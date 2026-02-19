# AWS CLI for Snowflake Engineers

## What Is This About?

**AWS CLI** (Command Line Interface) is a tool that lets you interact with AWS services — like S3, IAM, EC2 — directly from your terminal, instead of clicking around the AWS web console.

As a Snowflake engineer, you'll use it constantly because **Snowflake and S3 are tightly connected**. You load data from S3 into Snowflake, unload data from Snowflake back to S3, and when something goes wrong, the CLI is how you investigate.

Think of AWS CLI as your **stethoscope** — when a Snowflake pipeline fails, the CLI helps you diagnose what happened on the S3 side.

> **Example:** Your `COPY INTO` command fails with "File not found." Instead of guessing, you run one CLI command to check if the file actually exists in the bucket. Problem found in seconds.

---

## Table of Contents

**Part 1 — AWS CLI Fundamentals**

1. [Installing and Configuring AWS CLI](#1-installing-and-configuring-aws-cli)
2. [Listing Files in S3](#2-listing-files-in-s3)
3. [Downloading Files from S3](#3-downloading-files-from-s3)
4. [Uploading Files to S3](#4-uploading-files-to-s3)
5. [Other Useful Commands](#5-other-useful-commands)

**Part 2 — When and Why to Use the CLI**

6. [CLI vs Web Console — When Does CLI Win?](#6-cli-vs-web-console--when-does-cli-win)

**Part 3 — AWS CLI Command Reference**

7. [All the Commands You Should Know](#7-all-the-commands-you-should-know)

**Part 4 — Loading & Unloading Patterns in Snowflake**

8. [Loading Through a Stage](#8-loading-through-a-stage)
9. [Loading Directly from S3](#9-loading-directly-from-s3)
10. [Unloading from Snowflake to S3](#10-unloading-from-snowflake-to-s3)
11. [Handling ZIP Files](#11-handling-zip-files)
12. [Comparison of All Loading Approaches](#12-comparison-of-all-loading-approaches)

**Part 5 — Practical Scenarios**

13. [Debugging a Failed Pipeline — A Real-World Walkthrough](#13-debugging-a-failed-pipeline--a-real-world-walkthrough)
14. [Self-Check Questions & Answers](#14-self-check-questions--answers)

---

# Part 1 — AWS CLI Fundamentals

## 1. Installing and Configuring AWS CLI

### Step 1: Install It

| OS | How to Install |
|----|---------------|
| **Windows** | Download the MSI installer from the AWS website |
| **Mac** | `brew install awscli` |
| **Linux** | `sudo apt-get install awscli` |

Verify it's working:

```bash
aws --version
```

You should see something like `aws-cli/2.x.x Python/3.x.x ...`

---

### Step 2: Get Your AWS Credentials

AWS CLI needs to know **who you are**. For that, you need two values:

- **Access Key ID** — think of this as your username
- **Secret Access Key** — think of this as your password

**How to get them:**

1. Log into the AWS web console.
2. Go to **IAM** (Identity & Access Management).
3. Navigate to **Users** and select your account.
4. Under **Security Credentials**, click **Create Access Key**.
5. AWS gives you two values — copy them and keep them safe.

> **Security warning:** Your Secret Access Key is like a bank PIN. If someone gets it, they can access your AWS account. Never commit it to Git, never share it in Slack, and never hardcode it in scripts. Many companies prefer **IAM Roles** with temporary credentials instead of static keys.

---

### Step 3: Configure the CLI

Run this command and fill in your details:

```bash
aws configure
```

It will ask for four things:

```
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-east-1
Default output format [None]: json
```

**About Region:** This must match the region where your S3 bucket lives. If your bucket is in `us-east-1` but you type `ap-south-1`, you'll get confusing "bucket not found" errors. When in doubt, ask your team or check with:

```bash
aws s3api get-bucket-location --bucket your-bucket-name
```

**About Output Format:** This controls how results look in your terminal.

| Format | What It Looks Like |
|--------|--------------------|
| `json` | Raw JSON (good for scripts) |
| `table` | Neatly formatted table (good for humans) |
| `text` | Plain text (good for piping to other commands) |

After this, your CLI is ready to use.

---

## 2. Listing Files in S3

This is probably the command you'll use most often. It shows you what files exist in an S3 bucket or folder.

```bash
aws s3 ls s3://company-data/raw/2025/
```

**Example output:**

```
2025-08-01 12:45:32     145123 sales_data_2025-08-01.csv
2025-08-02 14:22:10     167890 sales_data_2025-08-02.csv
```

**How to read the output:**

| Column | Meaning |
|--------|---------|
| `2025-08-01` | Date the file was uploaded |
| `12:45:32` | Time it was uploaded |
| `145123` | File size in bytes (~145 KB) |
| `sales_data_2025-08-01.csv` | File name |

**Why this matters for Snowflake:** Before running a `COPY INTO`, you can verify the file actually exists and isn't empty (size = 0). Many pipeline failures boil down to "the file wasn't there" or "the file was empty."

---

## 3. Downloading Files from S3

Sometimes you need to pull a file down to your machine to inspect it — maybe open it in Notepad or Excel to check the format.

**Download a single file:**

```bash
aws s3 cp s3://company-data/raw/2025/sales_data_2025-08-01.csv ./local_folder/
```

**Download an entire folder:**

```bash
aws s3 cp s3://company-data/raw/2025/ ./local_folder/ --recursive
```

The `--recursive` flag is important — without it, only a single file copies. With it, everything in that folder (including subfolders) comes down.

> **Real-world use:** You download a file, open it, and realize the delimiter is `|` instead of `,`. That's why your Snowflake `COPY INTO` was failing — the file format didn't match.

---

## 4. Uploading Files to S3

When you've fixed a file or created test data locally, push it to S3 so Snowflake can read it.

**Upload a single file:**

```bash
aws s3 cp ./local_folder/my_test_file.csv s3://company-data/raw/2025/
```

**Upload an entire folder:**

```bash
aws s3 cp ./local_folder/ s3://company-data/raw/2025/ --recursive
```

---

## 5. Other Useful Commands

### Sync — Smart Copy That Only Transfers Changes

Unlike `cp` which copies everything every time, `sync` compares the source and destination and **only transfers new or changed files**. Much faster when you have thousands of files.

```bash
aws s3 sync ./local_folder/ s3://company-data/raw/2025/
```

Think of `cp` as "copy everything no matter what" and `sync` as "make both sides match, only moving what's different."

---

### Delete a File from S3

```bash
aws s3 rm s3://company-data/raw/2025/sales_data_2025-08-01.csv
```

---

### Check Which Region a Bucket Is In

Useful when Snowflake gives you a region mismatch error:

```bash
aws s3api get-bucket-location --bucket company-data
```

---

### Check Who You're Logged In As

When you're getting "Access Denied" and you're not sure which account/role the CLI is using:

```bash
aws sts get-caller-identity
```

---

### Inspect a File's Metadata (Size, Last Modified, Encryption)

```bash
aws s3api head-object --bucket company-data --key raw/2025/sales_data.csv
```

This shows the file size, when it was last modified, and what encryption it uses — without downloading the file.

---

# Part 2 — When and Why to Use the CLI

## 6. CLI vs Web Console — When Does CLI Win?

Both the CLI and the AWS web console let you do the same things. But in practice, the CLI is often the better choice. Here's when and why.

### For Automation and Scheduling

If you need to upload files to S3 every day at 5 AM, you can't have a person clicking buttons in the web console. A CLI command can be scheduled with cron, Airflow, or any scheduler.

```bash
aws s3 sync ./daily_csv/ s3://company-data/raw/2025/
```

---

### On Servers Without a Browser

Your ETL server is a Linux EC2 instance with no GUI. The web console isn't an option. The CLI is your only way to interact with S3.

---

### For Bulk Operations

Moving, deleting, or uploading hundreds of files through the web console is painfully slow. The CLI handles it in seconds.

```bash
aws s3 rm s3://company-data/raw/2025/ --recursive
aws s3 cp ./new_files/ s3://company-data/raw/2025/ --recursive
```

---

### For Debugging Permissions

When Snowflake says "access denied," the CLI lets you inspect the exact policies and simulate whether a role has the right permissions.

```bash
aws s3api get-bucket-policy --bucket company-data
```

---

### For Temporary Credentials

Many companies don't allow permanent access keys. Instead, they use **STS (Security Token Service)** to issue temporary credentials that expire. The CLI supports this natively.

```bash
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/SnowflakeRole \
  --role-session-name SnowflakeSession
```

---

### For Embedding in Scripts and Pipelines

CLI commands can be called from Python, Airflow DAGs, shell scripts — anywhere you need programmatic access to AWS.

---

### Summary — When to Use CLI vs Console

| Situation | Use CLI? | Why |
|-----------|----------|-----|
| One-off exploration / learning | Console is fine | Visual, easy to navigate |
| Automating repetitive tasks | **CLI** | Scriptable, schedulable |
| Working on a remote server | **CLI** | No browser available |
| Uploading/downloading many files | **CLI** | Much faster for bulk operations |
| Debugging "Access Denied" errors | **CLI** | Can inspect policies and simulate access |
| Using temporary credentials | **CLI** | STS only works programmatically |
| Inspecting file metadata | **CLI** | One command vs multiple console clicks |
| 3 AM production emergency | **CLI** | Fast, no VPN/browser hassle |

---

# Part 3 — AWS CLI Command Reference

## 7. All the Commands You Should Know

Here's a grouped reference of the most important commands for a Snowflake/data engineer.

### General Utility

| Command | What It Does |
|---------|-------------|
| `aws configure` | Set up your access key, secret key, region, and output format |
| `aws configure list` | See which credentials and region your CLI is currently using |
| `aws sts get-caller-identity` | Shows who you're logged in as (account ID, user/role) — great for debugging credential issues |

### S3 — Your Most-Used Commands

| Command | What It Does |
|---------|-------------|
| `aws s3 ls s3://bucket/path/` | List files in a bucket or folder |
| `aws s3 cp source destination` | Copy files between local and S3 (or S3 to S3) |
| `aws s3 mv source destination` | Move/rename files in S3 (removes from source) |
| `aws s3 rm s3://bucket/path/file` | Delete a file from S3 |
| `aws s3 sync source destination` | Sync two locations — only transfers new/changed files |
| `aws s3 presign s3://bucket/path/file` | Generate a temporary URL for sharing a private file |
| `aws s3api get-bucket-location --bucket name` | Check which AWS region the bucket is in |
| `aws s3api head-object --bucket name --key path` | Get file metadata (size, date, encryption) without downloading |

### IAM — Security and Access

| Command | What It Does |
|---------|-------------|
| `aws iam list-users` | List all IAM users in the account |
| `aws iam list-roles` | List all IAM roles |
| `aws iam get-user` | See details about your own IAM user |
| `aws iam attach-user-policy` | Attach a permission policy to a user (like S3 read-only) |
| `aws iam create-access-key` | Generate new access/secret key pair for a user |

### STS — Temporary Credentials

| Command | What It Does |
|---------|-------------|
| `aws sts assume-role` | Assume an IAM role and get temporary credentials |
| `aws sts get-session-token` | Get a temporary session token (for MFA-enabled accounts) |

### CloudWatch — Logs and Monitoring

| Command | What It Does |
|---------|-------------|
| `aws cloudwatch list-metrics` | List available monitoring metrics |
| `aws cloudwatch get-metric-data` | Retrieve metric data (e.g., S3 request counts) |
| `aws logs tail` | Watch log output in real-time |

### KMS and Secrets Manager

| Command | What It Does |
|---------|-------------|
| `aws kms list-keys` | List encryption keys — important when S3 uses SSE-KMS with Snowflake |
| `aws secretsmanager get-secret-value` | Retrieve stored secrets (some Snowflake connectors store passwords here) |

### Why These Matter for Snowflake Engineers

- **S3 commands** — you'll use these daily for loading/unloading data
- **IAM commands** — you'll configure Snowflake external stages using IAM Roles/Users
- **STS commands** — many companies enforce temporary tokens for Snowflake pipelines
- **CloudWatch** — for debugging why data didn't reach Snowflake (e.g., upstream ETL logs)
- **KMS & Secrets Manager** — for encrypted S3 buckets and secure credential management

---

# Part 4 — Loading & Unloading Patterns in Snowflake

Now that you understand the CLI, let's connect it to how data actually flows between S3 and Snowflake.

## 8. Loading Through a Stage

A **stage** in Snowflake is like a **loading dock** — a designated area where files sit before being loaded into a table. Stages can be **internal** (managed by Snowflake) or **external** (pointing to S3).

### How It Works

**Step 1 — Create a stage:**

For an internal stage (Snowflake manages the storage):

```sql
CREATE OR REPLACE STAGE my_stage;
```

For an external stage (points to S3):

```sql
CREATE OR REPLACE STAGE my_s3_stage
  URL = 's3://company-data/raw/2025/'
  STORAGE_INTEGRATION = my_s3_integration;
```

**Step 2 — Upload files to the stage** (only needed for internal stages):

```sql
PUT file://C:\local\sales_data_2025.csv @my_stage;
```

For external stages, the files are already in S3 — no upload needed.

**Step 3 — Load from the stage into a table:**

```sql
COPY INTO sales_table
FROM @my_stage
FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"');
```

**When to use this approach:**

- When you want to **inspect the files** before loading (list them, preview them)
- When you need detailed **error handling** (`ON_ERROR = CONTINUE / SKIP_FILE / ABORT_STATEMENT`)
- When you're loading **multiple files** and want control over the process

**Trade-off:** It's an extra step, and internal stages use a bit of Snowflake storage.

---

## 9. Loading Directly from S3

You can skip the named stage and tell Snowflake to read straight from an S3 path:

```sql
COPY INTO sales_table
FROM 's3://company-data/raw/2025/'
STORAGE_INTEGRATION = my_s3_integration
FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"')
ON_ERROR = 'CONTINUE';
```

**When to use this approach:**

- When your data is large and you want the **fastest possible load**
- When you don't need to inspect files beforehand
- When you want to avoid the extra storage cost of internal staging

**Trade-off:** Harder to pre-check file contents. If something is wrong with the files, you'll find out during the load.

---

## 10. Unloading from Snowflake to S3

This is the reverse — exporting data **from Snowflake to S3** as files. Covered in detail in the [Files Unloading to S3](./25_Files_Unloading_to_S3.md) guide.

```sql
COPY INTO 's3://company-data/unload/2025/'
FROM sales_table
STORAGE_INTEGRATION = my_s3_integration
FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' COMPRESSION = GZIP)
MAX_FILE_SIZE = 50000000;
```

- **`COMPRESSION = GZIP`** — Compresses the output files to save space and transfer time
- **`MAX_FILE_SIZE = 50000000`** — Targets ~50 MB per file. If the data is larger, Snowflake splits it into multiple files automatically.

**When to use:** Whenever another system needs to read your Snowflake data from S3 — downstream ETL jobs, BI tools, data sharing, etc.

**Watch out:** Very large exports can create many small files. Set `MAX_FILE_SIZE` to produce fewer, bigger files for better performance downstream.

---

## 11. Handling ZIP Files

This is a common source of confusion, so let's be very clear about what Snowflake can and cannot do.

### What Snowflake Supports

| Compression Format | Can Snowflake Load It? | Requirement |
|--------------------|----------------------|-------------|
| **GZIP** (.gz) | Yes | Must contain a single file |
| **BZIP2** (.bz2) | Yes | Must contain a single file |
| **ZIP** (.zip) with **one file** inside | Yes | The ZIP must contain exactly one file |
| **ZIP** (.zip) with **multiple files** inside | **No** | Snowflake will throw an error |

### Loading a Single-File ZIP

If the ZIP contains exactly one CSV file:

```sql
COPY INTO sales_table
FROM @my_s3_stage
FILE_FORMAT = (TYPE = 'CSV' COMPRESSION = 'AUTO');
```

Snowflake detects the compression automatically with `AUTO` and handles it.

### What Happens with Multi-File ZIPs?

Snowflake will give you an error like:

```
Error: ZIP archive contains multiple files.
```

### How to Solve the Multi-File ZIP Problem

You need to unzip the archive first, then upload the individual files.

**Using AWS CLI:**

```bash
# Download the ZIP
aws s3 cp s3://company-data/raw/2025/my_data.zip ./temp/

# Unzip it locally
unzip ./temp/my_data.zip -d ./temp/unzipped/

# Upload the individual CSV files back to S3
aws s3 cp ./temp/unzipped/ s3://company-data/raw/2025/ --recursive
```

Now each CSV file is separate in S3, and Snowflake can load them normally.

> **This is a great example of why you need AWS CLI.** Snowflake can't unzip multi-file archives, so the CLI bridges the gap — you pull the file down, unzip it, push the pieces back, and then Snowflake loads them.

---

## 12. Comparison of All Loading Approaches

| Approach | Command Pattern | Best For | Trade-Off |
|----------|----------------|----------|-----------|
| **Through a Stage** | `COPY INTO table FROM @stage` | When you want to inspect files and control error handling | Extra step; internal stages have storage cost |
| **Direct from S3** | `COPY INTO table FROM 's3://...'` | Large datasets where speed matters | Harder to pre-check file contents |
| **Unload to S3** | `COPY INTO 's3://...' FROM table` | Exporting data for other tools to consume | Large exports may create many small files |

**Rule of thumb:**

- Use **stages** when you want control, inspection, and error handling
- Use **direct copy** when the files are large and you want speed
- Use **unloading** when another system needs your Snowflake data in S3

---

# Part 5 — Practical Scenarios

## 13. Debugging a Failed Pipeline — A Real-World Walkthrough

It's 3 AM. You get an alert: *"Today's sales data is missing in Snowflake."*

Here's how you'd diagnose and fix it using the CLI.

**Step 1 — Check if the file even exists in S3:**

```bash
aws s3 ls s3://company-data/raw/2025/
```

If today's file isn't listed, the upstream team didn't upload it. Contact them.

**Step 2 — Check if the file is empty:**

If the file is listed but has `0` bytes, it's there but empty. That's why Snowflake couldn't load anything.

**Step 3 — Download and inspect the file:**

```bash
aws s3 cp s3://company-data/raw/2025/sales_data_2025-08-01.csv .
```

Open the file. Maybe the delimiter is `|` instead of `,`, or the header row is missing.

**Step 4 — Check if it's a region or permissions issue:**

```bash
aws s3api get-bucket-location --bucket company-data
aws sts get-caller-identity
```

Make sure the bucket region matches your Snowflake stage definition, and you're using the right credentials.

**Step 5 — Fix and reload:**

If you got the corrected file from the upstream team:

```bash
aws s3 cp ./sales_data_today.csv s3://company-data/raw/2025/
```

Then in Snowflake:

```sql
COPY INTO sales_table
FROM @my_s3_stage
FILE_FORMAT = (TYPE = 'CSV');
```

Pipeline fixed. Back to sleep.

---

## 14. Self-Check Questions & Answers

### Q1: How do you configure AWS CLI for the first time?

Run `aws configure` and provide your Access Key ID, Secret Access Key, default region, and output format. You get the keys from the AWS Console under IAM > Users > Security Credentials.

---

### Q2: What is the difference between `aws s3 cp` and `aws s3 sync`?

**`cp`** copies files unconditionally — it always transfers everything, even if the destination already has the same file. **`sync`** is smarter — it compares source and destination, and only transfers files that are new or changed. Use `sync` for incremental updates; use `cp` for one-off transfers.

---

### Q3: Why is the region important when configuring AWS CLI?

S3 buckets are **region-specific**. If your CLI is configured for `us-east-1` but your bucket is in `eu-west-1`, you'll get redirect errors. The CLI region must match the bucket's region. This also affects Snowflake — your external stage definition needs the correct region.

---

### Q4: How can you check if a file exists in S3 before running a Snowflake load?

```bash
aws s3 ls s3://company-data/raw/2025/sales_data_2025-08-01.csv
```

If the file exists, you'll see its details (date, size, name). If it doesn't exist, there's no output.

---

### Q5: What's the difference between using `--recursive` and not using it?

Without `--recursive`, the `cp` command only copies a single specified file. With `--recursive`, it copies **everything** in the folder, including all subfolders. You need `--recursive` whenever you're working with a directory rather than a single file.

---

### Q6: How would you debug a Snowflake load failure using AWS CLI?

1. **Check if the file exists:** `aws s3 ls s3://bucket/path/`
2. **Check file size:** Look at the bytes column in the `ls` output — 0 means empty
3. **Download and inspect:** `aws s3 cp s3://bucket/path/file.csv .` — open it to check delimiters, headers, encoding
4. **Check the bucket region:** `aws s3api get-bucket-location --bucket name` — mismatched regions cause failures
5. **Check your identity:** `aws sts get-caller-identity` — make sure you're using the right credentials
