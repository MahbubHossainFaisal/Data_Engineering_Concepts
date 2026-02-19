# Snowflake External Table — Automatic Refresh

## What Is This About?

An **external table** in Snowflake lets you query files that sit in S3 *without* loading them into a Snowflake table. Snowflake reads the files directly from S3 every time you run a query.

But there's a catch: Snowflake needs to know **which files exist** in S3. It keeps an internal list of files (called "metadata"). When new files land in S3 or old ones get deleted, that metadata needs to be **refreshed** — otherwise Snowflake won't know about the changes.

You *could* refresh manually every time, but that's tedious and error-prone. The better approach is to set up **automatic refresh** — so that every time a file is added or removed in S3, Snowflake automatically updates its metadata.

There are **two ways** to set this up on AWS:

- **Option A — SQS (Simple Queue Service):** Snowflake creates an SQS queue. You tell S3 to send file-change notifications to that queue. Snowflake listens and refreshes automatically. This is the simpler and most common approach.

- **Option B — SNS (Simple Notification Service):** You put an SNS topic between S3 and Snowflake. S3 sends notifications to SNS, and SNS forwards them to Snowflake's SQS queue (plus any other subscribers you want, like Lambda functions). Use this when you already have SNS set up or need multiple systems to react to the same S3 events.

---

## Table of Contents

1. [Prerequisites — What You Need Before Starting](#1-prerequisites--what-you-need-before-starting)
2. [Option A — The SQS Approach (Recommended)](#2-option-a--the-sqs-approach-recommended)
3. [Option B — The SNS Approach (When You Need a Broadcaster)](#3-option-b--the-sns-approach-when-you-need-a-broadcaster)
4. [How to Verify It's Working](#4-how-to-verify-its-working)
5. [Troubleshooting — When Auto-Refresh Isn't Working](#5-troubleshooting--when-auto-refresh-isnt-working)
6. [Important Rules and Gotchas](#6-important-rules-and-gotchas)
7. [Quick Cheat Sheet](#7-quick-cheat-sheet)
8. [Final Pre-Save Checklist](#8-final-pre-save-checklist)
9. [References](#9-references)

---

## 1. Prerequisites — What You Need Before Starting

Before setting up auto-refresh, make sure you have:

- A **Snowflake account on AWS** (these features are AWS-specific)
- **Admin access to the target AWS account** (you'll need to create event notifications and possibly edit policies)
- A **storage integration** already configured between Snowflake and your S3 bucket
- A **stage** in Snowflake pointing to your S3 location

**Tip:** When setting up S3 event notifications, make the prefix/suffix filter as specific as possible. This avoids unnecessary notifications (which cost money and add noise). Also, AWS doesn't allow two event notifications with overlapping prefixes going to the same queue type — plan accordingly.

---

## 2. Option A — The SQS Approach (Recommended)

This is the simplest setup. Here's how the pieces connect:

```
New file lands in S3
        ↓
S3 sends a notification to Snowflake's SQS queue
        ↓
Snowflake picks up the message and refreshes the external table metadata
        ↓
Your next query sees the new file automatically
```

### Step 1: Create a Stage and External Table

First, create a stage that points to your S3 location:

```sql
USE SCHEMA mydb.public;

CREATE STAGE mystage
  URL = 's3://mybucket/path'
  STORAGE_INTEGRATION = my_storage_int;
```

Then create the external table. By default, `AUTO_REFRESH = TRUE` is already on — you don't need to specify it.

```sql
CREATE OR REPLACE EXTERNAL TABLE ext_table
  WITH LOCATION = @mystage/somepath/
  FILE_FORMAT = (TYPE = PARQUET);
```

If you have partition columns, define them here. But note: if you use `PARTITION_TYPE = USER_SPECIFIED` (manual partitions), auto-refresh is **not supported** — you'd have to manage partitions yourself.

---

### Step 2: Find the SQS Queue ARN That Snowflake Created

Snowflake automatically creates an SQS queue for your account/region. You need its ARN to configure S3 notifications.

```sql
SHOW EXTERNAL TABLES;
```

In the results, look for the **`notification_channel`** column. Copy that value — it's an SQS ARN that looks something like:

```
arn:aws:sqs:us-east-1:123456789012:sf-snowpipe-XXXXXXXX
```

This is the queue where Snowflake is listening for S3 events.

---

### Step 3: Tell S3 to Send Notifications to That Queue

Now go to the **AWS Console**:

1. Navigate to **S3** > your bucket > **Properties** tab > scroll to **Event notifications**
2. Click **Create event notification**
3. Fill in the details:

| Field | What to Enter |
|-------|---------------|
| **Name** | Something descriptive, like `AutoRefresh-Snowflake` |
| **Events** | Select **All object create events** and **All object removal events** (or choose specific ones like `s3:ObjectCreated:Put`) |
| **Prefix filter** (optional) | The subfolder path your external table reads from, e.g., `path/somepath/` — this avoids notifications for unrelated files |
| **Suffix filter** (optional) | e.g., `.parquet` if you only care about Parquet files |
| **Destination** | Choose **SQS queue** |
| **SQS queue ARN** | Paste the `notification_channel` ARN you copied from Snowflake |

4. Save the notification.

---

### Step 4: Seed the Metadata Once (Manual Refresh)

The S3 event notification only fires for *new* events going forward. It doesn't retroactively tell Snowflake about files that already exist. So you need to do **one manual refresh** to pick up existing files:

```sql
ALTER EXTERNAL TABLE ext_table REFRESH;
```

After this, everything is automatic. New files in S3 trigger an SQS message, and Snowflake refreshes the metadata on its own.

---

## 3. Option B — The SNS Approach (When You Need a Broadcaster)

Use this when your S3 events need to go to **multiple destinations** — for example, Snowflake *and* a Lambda function *and* another team's SQS queue. SNS acts as a middleman that broadcasts events to all subscribers.

The flow looks like this:

```
New file lands in S3
        ↓
S3 sends a notification to an SNS topic
        ↓
SNS broadcasts to all subscribers:
    → Snowflake's SQS queue (auto-refresh)
    → Your Lambda function
    → Another team's SQS queue
    → Email alerts, etc.
```

### Step 1: Create (or Identify) Your SNS Topic

In the **AWS Console**:

1. Go to **SNS** > **Topics** > **Create topic**
2. Choose **Standard** (not FIFO — Snowflake doesn't support FIFO topics)
3. Give it a name and create it
4. Copy the **Topic ARN** (e.g., `arn:aws:sns:us-east-1:111122223333:mytopic`)

If you already have an SNS topic that receives S3 events, skip this step and use that topic's ARN.

---

### Step 2: Generate the Permission Policy from Snowflake

Snowflake needs permission to subscribe its SQS queue to your SNS topic. It provides a helper function that generates the exact policy snippet you need:

```sql
SELECT SYSTEM$GET_AWS_SNS_IAM_POLICY('arn:aws:sns:us-east-1:111122223333:mytopic');
```

This returns a JSON policy fragment. Copy it — you'll paste it into the SNS topic's access policy in the next step.

---

### Step 3: Add the Policy to Your SNS Topic

Back in the **AWS Console**:

1. Go to your SNS topic > **Edit**
2. Find the **Access policy** section
3. Merge the JSON that Snowflake gave you into the existing policy
4. Save

This grants Snowflake's SQS queue permission to subscribe to the topic and receive messages.

---

### Step 4: Create the External Table with the SNS ARN

When you create the external table, include the `AWS_SNS_TOPIC` parameter. This tells Snowflake to subscribe its SQS queue to your SNS topic:

```sql
CREATE OR REPLACE EXTERNAL TABLE ext_table
  WITH LOCATION = @mystage/path1/
  FILE_FORMAT = (TYPE = JSON)
  AWS_SNS_TOPIC = 'arn:aws:sns:us-east-1:111122223333:mytopic';
```

Behind the scenes, Snowflake creates the SQS subscription to your SNS topic automatically.

---

### Step 5: Make Sure S3 Events Go to the SNS Topic

If S3 isn't already configured to notify this SNS topic, set it up:

1. Go to your S3 bucket > **Properties** > **Event notifications**
2. Create an event notification, but this time set the **Destination** to your **SNS topic** instead of SQS
3. Select the events you care about (`ObjectCreated`, `ObjectRemoved`, etc.)
4. Save

---

### Step 6: Seed the Metadata Once

Same as the SQS approach — run one manual refresh to pick up existing files:

```sql
ALTER EXTERNAL TABLE ext_table REFRESH;
```

From now on, the chain `S3 → SNS → Snowflake SQS → auto-refresh` handles everything.

---

## 4. How to Verify It's Working

After setting up auto-refresh, test it:

**1. Check the external table details:**

```sql
SHOW EXTERNAL TABLES;
```

Look at two columns:
- `notification_channel` — the SQS ARN Snowflake is listening on
- `last_refreshed_on` — the timestamp of the last refresh

**2. Upload a test file to S3 and wait a moment:**

```bash
aws s3 cp test_file.parquet s3://mybucket/path/somepath/
```

Wait 30-60 seconds, then check:

```sql
SHOW EXTERNAL TABLES;
```

The `last_refreshed_on` should have updated to a recent timestamp.

**3. Check the file registration history:**

```sql
SELECT *
FROM TABLE(INFORMATION_SCHEMA.EXTERNAL_TABLE_FILE_REGISTRATION_HISTORY(
  TABLE_NAME => 'EXT_TABLE'
));
```

This shows every file that was registered or unregistered, when it happened, and whether it was from a manual refresh or an automatic one.

**4. (Optional) Check the SQS queue in AWS Console:**

Go to **SQS** in the AWS Console. Find the queue matching the `notification_channel` ARN. Under **Monitoring**, you should see messages being received.

> **Tip:** If you're querying the external table and don't see new data, Snowflake might be returning cached results. Disable the result cache temporarily:
> ```sql
> ALTER SESSION SET USE_CACHED_RESULT = FALSE;
> ```
> Then re-run your query.

---

## 5. Troubleshooting — When Auto-Refresh Isn't Working

If new files appear in S3 but the external table doesn't update, walk through these checks:

### Is AUTO_REFRESH actually enabled?

If someone changed ownership of the external table, `AUTO_REFRESH` can silently flip to `FALSE`. Fix it:

```sql
ALTER EXTERNAL TABLE ext_table SET AUTO_REFRESH = TRUE;
```

### Is the S3 event notification configured correctly?

In the S3 bucket properties, verify:
- The correct events are selected (`ObjectCreated`, `ObjectRemoved`)
- The prefix filter matches the path your external table reads from
- The destination points to the right SQS queue (or SNS topic)

### (SNS only) Did you add the Snowflake policy to the SNS topic?

Without this policy, Snowflake's SQS queue can't subscribe to the SNS topic, so messages never arrive. Re-run:

```sql
SELECT SYSTEM$GET_AWS_SNS_IAM_POLICY('arn:aws:sns:...');
```

And make sure the returned JSON is merged into the SNS topic's access policy.

### Did you do the initial manual refresh?

Auto-refresh only handles *new* events. If you never ran `ALTER EXTERNAL TABLE ... REFRESH`, Snowflake doesn't know about files that existed before the notification was set up.

### Are there overlapping S3 event notifications?

AWS does not allow two event notifications on the same bucket with the same prefix going to the same type of destination (e.g., two SQS targets for the same prefix). If there's a conflict, the notification creation will fail.

---

## 6. Important Rules and Gotchas

| Rule | Why It Matters |
|------|---------------|
| **Manual partitions disable auto-refresh** | If you use `PARTITION_TYPE = USER_SPECIFIED`, Snowflake won't auto-refresh. You must `ADD PARTITION` / `REMOVE PARTITION` manually. |
| **One SQS queue per region** | Snowflake uses a single SQS queue per region for your account. The same queue serves multiple external tables and Snowpipe objects. Don't try to create separate queues. |
| **No overlapping S3 notifications** | AWS forbids two event configs with the same prefix going to the same destination type. Plan your prefixes carefully. |
| **SNS must be Standard, not FIFO** | Snowflake doesn't support FIFO SNS topics. |
| **Same-region is best** | Create your SNS topic in the same region as your S3 bucket and Snowflake account. Cross-region setups add latency and may incur data transfer costs. |
| **Seed once, auto after** | Always run `ALTER EXTERNAL TABLE ... REFRESH` once after setup. After that, automation takes over. |

---

## 7. Quick Cheat Sheet

### SQS Path (Simpler)

```sql
-- 1. Create stage + external table
CREATE STAGE mystage
  URL = 's3://mybucket/path'
  STORAGE_INTEGRATION = my_storage_int;

CREATE EXTERNAL TABLE ext_table
  WITH LOCATION = @mystage/path
  FILE_FORMAT = (TYPE = PARQUET);

-- 2. Get the SQS ARN to configure in S3
SHOW EXTERNAL TABLES;
-- Copy the "notification_channel" value

-- 3. Seed metadata once
ALTER EXTERNAL TABLE ext_table REFRESH;
```

**Then in AWS:** S3 bucket > Properties > Event notifications > Create > Destination = SQS > Paste the `notification_channel` ARN.

---

### SNS Path (When Broadcasting to Multiple Subscribers)

```sql
-- 1. Get the policy snippet to add to your SNS topic
SELECT SYSTEM$GET_AWS_SNS_IAM_POLICY('arn:aws:sns:us-east-1:111122223333:mytopic');
-- Add the returned JSON to the SNS topic's access policy in AWS

-- 2. Create external table with the SNS topic
CREATE EXTERNAL TABLE ext_table
  WITH LOCATION = @mystage/path
  FILE_FORMAT = (TYPE = JSON)
  AWS_SNS_TOPIC = 'arn:aws:sns:us-east-1:111122223333:mytopic';

-- 3. Seed metadata once
ALTER EXTERNAL TABLE ext_table REFRESH;
```

**Then in AWS:** Make sure S3 event notifications point to the SNS topic (not directly to SQS).

---

## 8. Final Pre-Save Checklist

Before you leave the AWS Console, verify:

- [ ] S3 event notification selects the right events (`ObjectCreated` and/or `ObjectRemoved`)
- [ ] The SQS ARN in the S3 notification matches exactly what `SHOW EXTERNAL TABLES` returned (no typos, no extra spaces)
- [ ] *(SNS only)* You ran `SYSTEM$GET_AWS_SNS_IAM_POLICY` and merged the output into the SNS topic's access policy
- [ ] The prefix/suffix filters in the S3 event match the path your external table reads from
- [ ] You ran `ALTER EXTERNAL TABLE ... REFRESH` at least once to seed the initial metadata
- [ ] *(SNS only)* The SNS topic is **Standard**, not FIFO

---

## 9. References

| Topic | Link |
|-------|------|
| Auto-refresh for external tables on S3 | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/tables-external-s3) |
| `CREATE EXTERNAL TABLE` (all options) | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/create-external-table) |
| `SHOW EXTERNAL TABLES` (check notification_channel) | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/show-external-tables) |
| `SYSTEM$GET_AWS_SNS_IAM_POLICY` | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/functions/system_get_aws_sns_iam_policy) |
| Auto-refresh overview | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/tables-external-auto) |
| Creating notification integrations for SNS | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/notifications/creating-notification-integration-amazon-sns) |
| S3 event notifications (AWS) | [AWS Docs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/enable-event-notifications.html) |
| Automating Snowpipe for S3 (related pattern) | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/data-load-snowpipe-auto-s3) |
