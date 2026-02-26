# 🚀 Snowpipe: Real-Time Data Ingestion Automation

## 🌟 The Core Idea: Files → Snowflake Automatically

Imagine your company receives **customer transaction files** on S3 every minute. You need those files loaded into Snowflake **instantly** — not manually, not via scheduled tasks, but **automatically the moment they land**.

**The old way (❌ Manual):**
1. File lands in S3 at 2:15 PM
2. You run COPY INTO manually at 2:45 PM
3. Data is now 30 minutes stale

**The new way (✅ Snowpipe):**
1. File lands in S3 at 2:15 PM
2. Snowpipe detects it automatically
3. Data is in Snowflake within seconds

Welcome to **Snowpipe** — the native, event-driven ingestion engine.

---

## 🎯 What Is Snowpipe?

> **Snowpipe** is Snowflake's **serverless, event-driven data ingestion service** that automatically detects files in S3 (or Azure/GCS) and loads them into Snowflake tables using pre-defined COPY commands.

**Key distinction from COPY:**
- COPY = Manual/scheduled bulk loading
- Snowpipe = Automatic/event-driven streaming ingestion

---

## 💡 Purpose & Problems Solved

### Without Snowpipe ❌
- Manual COPY INTO commands (tedious, error-prone)
- External schedulers needed even for small loads
- Delays between file arrival and data availability
- Complex error handling and retries
- No built-in notification of failures

### With Snowpipe ✅
- Fully automated, event-driven loading
- No external orchestration required
- Near real-time data availability
- Built-in error handling and retries
- Native Snowflake monitoring
- Serverless (you don't manage compute)

**Real impact:** A retailer receiving 1000s of transaction files daily now processes them automatically in seconds, instead of waiting for scheduled batch jobs.

---

## 🔄 How Snowpipe Works: The Complete Workflow

### The Architecture (3 Components)

```
S3 Bucket
    │
    │ (File uploaded)
    ▼
S3 Event Notification
    │ (SNS/SQS message)
    ▼
Snowflake Snowpipe
    │ (Detects notification)
    ▼
Executes COPY Command
    │
    ▼
Snowflake Table (Data Loaded)
```

### Step-by-Step Example: Real Scenario

Let's say **RetailX Inc.** wants to load order files from S3 into Snowflake automatically.

#### Step 1: Create File Format
```sql
CREATE FILE FORMAT order_csv_format
  TYPE = CSV
  FIELD_DELIMITER = ','
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  SKIP_HEADER = 1
  NULL_IF = ('NULL', '');
```

#### Step 2: Create Target Table
```sql
CREATE TABLE ORDERS_STAGING (
  order_id STRING,
  customer_id STRING,
  order_date DATE,
  amount NUMBER(10,2)
);
```

#### Step 3: Create External Stage (Points to S3)
```sql
CREATE STAGE orders_stage
  URL = 's3://retailx-bucket/orders/'
  STORAGE_INTEGRATION = aws_integration; -- (assumes AWS integration exists)
```

#### Step 4: Create the COPY Command (as SQL)
```sql
-- This is the blueprint Snowpipe will use
COPY INTO ORDERS_STAGING
FROM @orders_stage
FILE_FORMAT = order_csv_format
ON_ERROR = 'CONTINUE';
```

#### Step 5: Create the Snowpipe Object
```sql
CREATE OR REPLACE PIPE orders_pipe
  AUTO_INGEST = TRUE
  AS
  COPY INTO ORDERS_STAGING
  FROM @orders_stage
  FILE_FORMAT = order_csv_format
  ON_ERROR = 'CONTINUE';
```

→ Now Snowpipe is **active** and listening for S3 events!

#### Step 6: Set Up S3 Notifications
In your **AWS Console, S3 bucket settings:**
1. Enable SNS/SQS notifications for object creation
2. Point to the **SQS queue Snowpipe created**
3. Filter to only `.csv` files (optional)

### What Happens When a File Lands

```
1. orders_2025_02_27_001.csv uploaded to s3://retailx-bucket/orders/
2. S3 detects upload event
3. S3 sends message to Snowflake's SQS queue
4. Snowpipe polls the queue
5. Snowpipe reads: "Hey, new file: orders_2025_02_27_001.csv"
6. Snowpipe executes the pre-defined COPY command
7. File is parsed and loaded into ORDERS_STAGING
8. Done!
```

**Time taken:** Usually < 10 seconds (near real-time)

---

## 🔔 Notification Channels: The Trigger System

Snowpipe uses **cloud notifications** (SNS/SQS) to detect new files. Think of it as a **doorbell system**:

- **S3 bucket** = Your mailbox
- **New file upload** = Something arrives in mailbox
- **S3 event** = Doorbell rings
- **SNS/SQS queue** = Snowflake listens at the door
- **Snowpipe** = The worker who receives the package

### AWS SNS vs SQS (How Snowflake Recommends It)

**Why SNS→SQS?** Why not just SNS?

```
S3 Event
    │
    ▼ (notifies)
SNS Topic
    │
    ▼ (publishes to)
SQS Queue (Snowflake subscribes here)
    │
    ▼ (Snowflake polls)
Snowpipe ingests data
```

**Benefits of this flow:**
- SQS provides **queuing** (handles burst loads)
- SNS provides **reliable fan-out** (can notify multiple services)
- Snowpipe **polls** the queue (controlled, not pushed at)
- No data loss if Snowflake temporarily unavailable

---

## ⚙️ Key Snowpipe Characteristics

### Snowflake Manages the Warehouse

Here's something unique: **Snowflake manages the warehouse internally for Snowpipe**. You don't specify a warehouse in the pipe definition.

```sql
CREATE PIPE orders_pipe
  AUTO_INGEST = TRUE
  AS
  COPY INTO ORDERS_STAGING ...
  -- No WAREHOUSE specified!
```

Why? Because Snowflake:
- Allocates compute dynamically
- Charges separately for pipe execution (you see it in PIPE_USAGE view)
- Scales based on volume
- You don't manage warehouse resize/suspension

**Cost implication:** Snowpipe charges per 1000 files processed, not by warehouse seconds.

---

## 🔍 Monitoring & Troubleshooting Snowpipe

### Useful Queries for Day-to-Day Tasks

#### 1. Check Pipe Status
```sql
SHOW PIPES;

-- More detailed:
DESC PIPE orders_pipe;
```

**Output shows:**
- `notification_channel` — SQS queue ARN
- `created_on` — When pipe was created
- `invalid` — Whether pipe is broken

#### 2. View Ingestion History
```sql
SELECT *
FROM TABLE(SNOWFLAKE.INFORMATION_SCHEMA.PIPE_USAGE_HISTORY(
  PIPE_NAME => 'orders_pipe',
  RESULT_LIMIT => 100
))
ORDER BY EXECUTION_TIME DESC;
```

**Shows:**
- How many files processed
- How many bytes loaded
- Execution success/failure
- Timestamp details

#### 3. Check Copy History (Find Errors)
```sql
SELECT *
FROM SNOWFLAKE.ACCOUNT_USAGE.COPY_HISTORY
WHERE PIPE_NAME = 'orders_pipe'
  AND LOAD_TIME > CURRENT_DATE - 7
ORDER BY LOAD_TIME DESC;
```

**Gives you:**
- File name
- Status (SUCCESS, FAILED, LOADED, PARTIALLY_LOADED)
- File size
- Row count
- Error message (if any)

#### 4. Find Recently Failed Loads
```sql
SELECT 
  file_name,
  stage_location,
  error_code,
  error_message,
  load_time
FROM SNOWFLAKE.ACCOUNT_USAGE.COPY_HISTORY
WHERE pipe_name = 'orders_pipe'
  AND status = 'FAILED'
ORDER BY load_time DESC
LIMIT 10;
```

**This answers:** "Why didn't file X load?"

### Handling Snowpipe Errors (No Notifications!)

Here's a critical gotcha: **Snowpipe doesn't throw errors like normal SQL does**. If your COPY command fails, Snowpipe silently retries 3 times and gives up.

**Your monitoring strategy:**
1. **Daily check** of COPY_HISTORY
2. **Alert on failures** — set up a task to check for failed loads
3. **Create alerting task:**

```sql
CREATE OR REPLACE TASK CHECK_SNOWPIPE_FAILURES
  WAREHOUSE = MONITOR_WH
  SCHEDULE = '1 HOUR'
  AS
  SELECT *
  FROM SNOWFLAKE.ACCOUNT_USAGE.COPY_HISTORY
  WHERE pipe_name = 'orders_pipe'
    AND status IN ('FAILED', 'PARTIALLY_LOADED')
    AND load_time > CURRENT_TIMESTAMP - INTERVAL '1 HOUR';
```

---

## ⚠️ Critical Snowpipe Design Rules

### Rule 1: Can't Alter COPY Inside Pipe

**❌ This DOESN'T work:**
```sql
ALTER PIPE orders_pipe 
  SET COPY_STATEMENT = 'COPY INTO NEW_TABLE ...';
```

Snowpipe doesn't support altering the underlying COPY command.

**✅ What you MUST do:**
```sql
-- Step 1: Drop the pipe
DROP PIPE orders_pipe;

-- Step 2: Create new pipe with updated COPY
CREATE PIPE orders_pipe
  AUTO_INGEST = TRUE
  AS
  COPY INTO NEW_TABLE
  FROM @orders_stage
  FILE_FORMAT = order_csv_format;

-- Step 3: Refresh metadata (see next rule)
ALTER PIPE orders_pipe REFRESH;
```

### Rule 2: Refresh Pipe Metadata After Recreate

When you recreate a pipe, Snowflake loses track of which files were already loaded.

**Problem:** Files get reloaded!

**Solution: Use REFRESH**
```sql
ALTER PIPE orders_pipe REFRESH;
```

This tells Snowpipe to:
- Scan the S3 folder
- Compare with loaded file list
- Only load files not yet processed

**Pro tip:** Without REFRESH, you risk duplicate data in your table.

---

## 📊 Snowpipe Best Practices

### Best Practice 1: One Pipe Per S3 Bucket (Usually)

**Why?** 
- Notification channels are bucket-level
- Cleaner mapping: bucket → pipe → table
- Easier troubleshooting

**Example structure:**
```
s3://retailx-orders/
  └─ orders_pipe (COPY INTO orders_table)

s3://retailx-customers/
  └─ customers_pipe (COPY INTO customers_table)
```

Even if each bucket produces different data, **one pipe per bucket** is clearest.

**Exception:** Multiple pipes from **same bucket** only if:
- Different folder prefixes with different data
- Each folder needs its own transformation
- Technical requirement for separate tables

### Best Practice 2: Idempotent COPY Commands

Your COPY command **may run multiple times** on the same file (retries, manual run, etc.).

**Unsafe:**
```sql
COPY INTO orders_table FROM @orders_stage;
-- Running twice = duplicate rows!
```

**Safe (Idempotent):**
```sql
COPY INTO orders_table
FROM @orders_stage
ON_ERROR = 'CONTINUE'
FORCE = FALSE;
```

---

## 🔄 File Tracking: Name vs Hash (Critical Concept!)

### The Question: How Does Snowpipe Know What to Load?

You might think Snowpipe tracks files by **name**. It doesn't.

**Snowpipe tracks by FILE HASH + NAME combination.**

### Scenario 1: Truncate Table, Reupload Same File

```
Timeline:
1. orders_001.csv uploaded → loaded into table
2. Truncate table (DELETE all rows)
3. Upload same orders_001.csv again
4. Question: Does Snowpipe reload it?
```

**Answer: NO.** Why?

Because Snowpipe remembers:
- File name: `orders_001.csv`
- File hash: `x3f7a9b2c` (MD5 of file contents)
- Status: ✅ Already loaded

When you reupload, if file **content is identical**:
- Same hash `x3f7a9b2c`
- Snowpipe says: "I've seen this before!"
- File is **skipped**

**Result:** Table stays empty (file not reloaded).

### Scenario 2: COPY BY Command (Uses Hash)

When you manually run:
```sql
COPY INTO orders_table
FROM @orders_stage/orders_001.csv
FILE_FORMAT = csv_format;
```

This uses **file content hash** to avoid duplicates.

### How to Force Reload

If you want to reload a file:

1. **Modify the file slightly** (append timestamp, change hash)
2. **Upload with new name/hash**
3. **Use FORCE parameter:**
```sql
COPY INTO orders_table
FROM @orders_stage/orders_001.csv
FORCE = TRUE;
```

---

## 🎬 Step-by-Step Snowpipe Demo: Complete E2E Setup

#### Phase 1: Snowflake Setup

```sql
-- Create file format
CREATE FILE FORMAT order_csv
  TYPE = CSV
  FIELD_DELIMITER = ','
  SKIP_HEADER = 1
  NULL_IF = ('NULL', '');

-- Create target table
CREATE TABLE ORDERS_RAW (
  order_id STRING,
  customer_id STRING,
  order_amount DECIMAL(10,2),
  order_date DATE
);

-- Create external stage pointing to S3
CREATE STAGE orders_stage
  URL = 's3://retailx-data-bucket/orders/'
  STORAGE_INTEGRATION = snowflake_aws_integration;

-- Create Snowpipe
CREATE PIPE orders_ingestion
  AUTO_INGEST = TRUE
  AS
  COPY INTO ORDERS_RAW
  FROM @orders_stage
  FILE_FORMAT = order_csv
  ON_ERROR = 'CONTINUE';
```

#### Phase 2: AWS S3 Setup

1. Enable S3 event notifications
2. Set up SNS→SQS forwarding
3. Grant Snowflake permission to receive messages

#### Phase 3: Test Ingestion

```bash
aws s3 cp orders_2025_02_27.csv s3://retailx-data-bucket/orders/
```

**Verify:**
```sql
SELECT COUNT(*) FROM ORDERS_RAW;
```

---

## 🏆 Key Takeaway

**Snowpipe = Automatic, Event-Driven Data Ingestion**

✅ **Use Snowpipe for:**
- Real-time file ingestion (< 1 minute latency)
- High-frequency uploads (100s of files daily)
- Minimal infrastructure management

❌ **Don't use Snowpipe for:**
- One-time bulk loads (use COPY INTO)
- Complex transformation during load

**Remember:**
- Track files by **hash + name**
- Refresh metadata after recreating pipes
- Monitor via COPY_HISTORY
- One pipe per bucket (usually)
- Snowflake manages warehouse (serverless)

---
