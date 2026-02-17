# Unloading Data from Snowflake to S3

## What Is This About?

Sometimes you need to **export data out of Snowflake** and send it to an S3 bucket — maybe another team needs it, maybe a downstream tool like AWS Athena or a Python notebook reads from S3. In Snowflake, this process is called **"unloading."**

Think of it like this: **Loading** = bringing data *into* Snowflake. **Unloading** = sending data *out of* Snowflake to an external location like S3.

> **Real-World Scenario:** You work at "SkyCart," an e-commerce company. Every morning by 6:00 AM, the Marketing team expects a fresh export of yesterday's orders sitting in an S3 bucket. They use tools like Athena and Glue to read from it. Your job is to make sure the export is correct, repeatable, and verifiable.

---

## Table of Contents

1. [Three Things You Must Understand First](#1-three-things-you-must-understand-first)
2. [One-Time Setup — Connecting Snowflake to S3](#2-one-time-setup--connecting-snowflake-to-s3)
3. [The Unload — Step by Step](#3-the-unload--step-by-step)
4. [How to Verify Your Export Is Correct](#4-how-to-verify-your-export-is-correct)
5. [Choosing File Formats, Encryption & Performance](#5-choosing-file-formats-encryption--performance)
6. [Common Mistakes and How to Avoid Them](#6-common-mistakes-and-how-to-avoid-them)
7. [Automating This as a Daily Job](#7-automating-this-as-a-daily-job)
8. [Complete Copy-Paste Example](#8-complete-copy-paste-example)
9. [Quick Verification Checklist](#9-quick-verification-checklist)
10. [Real-World Tips](#10-real-world-tips)
11. [Test Your Understanding](#11-test-your-understanding)
12. [References](#12-references)

---

## 1. Three Things You Must Understand First

Before writing any SQL, understand these three ideas — everything else builds on them.

### Idea 1: Unloading = `COPY INTO <location>`

In Snowflake, you export data using the `COPY INTO` command — but instead of pointing it at a table (like when loading), you point it at an **S3 path** or a **named stage** that represents an S3 location.

Think of it as: *"Hey Snowflake, run this query and write the results as files into this S3 folder."*

### Idea 2: Snapshots Keep Your Data Consistent

Here's a subtle problem: if you count your rows first, then run the unload a few seconds later, the data might have changed between those two moments (someone could have inserted or deleted rows). Now your count won't match the export.

Snowflake solves this with **Time Travel**. You can say: *"Freeze the data as it looks right now"* by capturing a timestamp, and then tell both your count query and your export query to read from **that exact frozen moment**. This way, they always see the same data.

### Idea 3: Always Verify Your Export

Never assume the export worked perfectly. You should always prove three things:

- **Row count** — Does the number of rows in S3 match what Snowflake exported?
- **Files** — Are the expected folders and files actually in S3?
- **Data shape** — Do the columns, types, and values look correct?

> See: [COPY INTO \<location\> — Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/copy-into-location)

---

## 2. One-Time Setup — Connecting Snowflake to S3

Before you can export anything, Snowflake needs **permission** to write files into your S3 bucket. This is a one-time configuration.

### Step 1: Create a Storage Integration

A **Storage Integration** is Snowflake's way of securely connecting to your AWS account. Instead of storing AWS keys directly (which is risky), Snowflake uses an **IAM Role** — it "assumes" a role in your AWS account that has permission to write to the bucket.

```sql
USE ROLE ACCOUNTADMIN;

-- Tell Snowflake which IAM role to use and which S3 path it's allowed to write to
CREATE OR REPLACE STORAGE INTEGRATION SKY_OUT_INT
  TYPE                      = EXTERNAL_STAGE
  STORAGE_PROVIDER          = S3
  ENABLED                   = TRUE
  STORAGE_AWS_ROLE_ARN      = 'arn:aws:iam::123456789012:role/skycart-snowflake-writer'
  STORAGE_ALLOWED_LOCATIONS = ('s3://skycart-analytics/exports/');

-- This gives you two values you'll need for the AWS side
DESCRIBE INTEGRATION SKY_OUT_INT;
```

**What to do on the AWS side:** The `DESCRIBE` command returns a **Snowflake IAM User ARN** and an **External ID**. You take these two values and update your IAM role's trust policy in AWS so it trusts Snowflake. You also attach an S3 policy that allows `s3:PutObject` and `s3:ListBucket` on your target prefix.

> See: [CREATE STORAGE INTEGRATION — Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/create-storage-integration)

---

### Step 2: Create a Named External Stage

A **stage** is like a shortcut or bookmark — instead of typing the full S3 URL and integration name every time, you give it a name and reuse it.

```sql
USE ROLE SYSADMIN;
USE DATABASE PROD;
USE SCHEMA SHARED;

-- Now "@SKY_S3_STAGE" points to s3://skycart-analytics/exports/
CREATE OR REPLACE STAGE SKY_S3_STAGE
  URL                 = 's3://skycart-analytics/exports/'
  STORAGE_INTEGRATION = SKY_OUT_INT;
```

From now on, you can just reference `@SKY_S3_STAGE` instead of the full S3 URL.

> See: [CREATE STAGE — Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/create-stage)

---

### Step 3: Create Reusable File Formats

A **file format** defines *how* the exported files should look — what type (CSV, Parquet, etc.), what delimiter to use, how to handle NULLs, etc. You define it once and reuse it.

**Parquet format** — best for analytical tools (Athena, Spark, etc.) because it's compact and preserves column types:

```sql
CREATE OR REPLACE FILE FORMAT FF_PARQUET
  TYPE = PARQUET;
```

**CSV format** — best when someone needs a simple, human-readable file:

```sql
CREATE OR REPLACE FILE FORMAT FF_CSV
  TYPE                         = CSV
  FIELD_DELIMITER              = ','
  RECORD_DELIMITER             = '\n'
  SKIP_HEADER                  = 0
  NULL_IF                      = ('\\N', 'NULL')
  EMPTY_FIELD_AS_NULL          = TRUE
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  COMPRESSION                  = AUTO;
```

You can always override these settings directly in the `COPY INTO` command if you need a one-off change.

---

## 3. The Unload — Step by Step

**Our goal:** Export yesterday's completed orders from `PROD.SALES.ORDERS` into S3 as Parquet files, organized into folders by date.

### Step 3a: Save the Current Timestamp (Freeze the Data)

Before doing anything, we capture the current time. We'll use this timestamp in every query so that they all read the **exact same version** of the data.

```sql
USE ROLE ANALYST;
USE WAREHOUSE ETL_XL;
USE DATABASE PROD;
USE SCHEMA SALES;

-- "Freeze" the data at this exact moment
SET SNAP_TS = CURRENT_TIMESTAMP();
```

---

### Step 3b: (Optional) Preview Your Data First

Before exporting thousands of rows, it's smart to run a quick preview — just to make sure your query returns what you expect.

```sql
-- Just peek at the first 5 rows to make sure the query looks right
SELECT * FROM (
  SELECT order_id, customer_id, total_amount, order_date, updated_at
  FROM ORDERS
  WHERE status = 'COMPLETED'
    AND order_date = DATEADD(day, -1, CURRENT_DATE())
  QUALIFY ROW_NUMBER() OVER (ORDER BY order_id) <= 5
)
AT (TIMESTAMP => $SNAP_TS);
```

Notice the `AT (TIMESTAMP => $SNAP_TS)` — this tells Snowflake to read data from our frozen snapshot, not the live table.

---

### Step 3c: Count the Rows (So You Can Verify Later)

Now count how many rows *should* end up in S3. We'll compare this number against the actual export later.

```sql
-- Save the expected row count into a variable
SET ROWS_EXPECTED = (
  SELECT COUNT(*) FROM ORDERS
  AT (TIMESTAMP => $SNAP_TS)
  WHERE status = 'COMPLETED'
    AND order_date = DATEADD(day, -1, CURRENT_DATE())
);

-- Display it
SELECT $ROWS_EXPECTED AS rows_expected;
```

---

### Step 3d: Run the Actual Export (Parquet, Partitioned by Date)

This is the main event. We're telling Snowflake: *"Run this query, and write the results as Parquet files into S3, organized into folders by order_date."*

```sql
COPY INTO @PROD.SHARED.SKY_S3_STAGE/orders/parquet/
FROM (
  SELECT order_id, customer_id, total_amount, order_date, updated_at
  FROM ORDERS
  AT (TIMESTAMP => $SNAP_TS)
  WHERE status = 'COMPLETED'
    AND order_date = DATEADD(day, -1, CURRENT_DATE())
)
FILE_FORMAT      = (FORMAT_NAME = FF_PARQUET)
PARTITION BY     (TO_VARCHAR(order_date, 'YYYY-MM-DD'))
INCLUDE_QUERY_ID = TRUE
DETAILED_OUTPUT  = TRUE;
```

**What each option does in plain English:**

- **`PARTITION BY`** — Creates subfolders based on the date, like `.../partition_0=2025-08-29/`. This is great because downstream tools (like Athena) can skip irrelevant folders and only scan the dates they care about — saving time and money.

- **`INCLUDE_QUERY_ID`** — Adds the Snowflake query ID to each filename. This makes every file name unique and traceable — you can always link a file back to the exact query that created it.

- **`DETAILED_OUTPUT`** — Instead of just saying "done," Snowflake returns a row for each file it created, showing the file path, size, and number of rows. This is essential for verification.

> **Watch out:** You **cannot** use `PARTITION BY` together with `SINGLE=TRUE` (which forces one big file) or `OVERWRITE=TRUE`. If you need to overwrite old exports, use a date-stamped folder path instead, like `.../dt=2025-08-29/`.

---

### Step 3e: (Alternative) Export as CSV with Column Headers

If the downstream team needs a plain CSV file instead of Parquet:

```sql
COPY INTO 's3://skycart-analytics/exports/orders/csv/'
FROM (
  SELECT * FROM ORDERS
  AT (TIMESTAMP => $SNAP_TS)
  WHERE status = 'COMPLETED'
    AND order_date = DATEADD(day, -1, CURRENT_DATE())
)
STORAGE_INTEGRATION = SKY_OUT_INT
FILE_FORMAT         = (FORMAT_NAME = FF_CSV)
HEADER              = TRUE
MAX_FILE_SIZE       = 50000000
INCLUDE_QUERY_ID    = TRUE
DETAILED_OUTPUT     = TRUE;
```

- **`HEADER = TRUE`** — Adds column names as the first row in each CSV file.
- **`MAX_FILE_SIZE = 50000000`** — Targets ~50 MB per file. If the data is larger, Snowflake splits it into multiple files automatically.

> **Be careful with CSV:** Think about how NULLs and empty strings look in the file. A missing value and an empty string `""` can look the same in CSV. Set `NULL_IF` and `FIELD_OPTIONALLY_ENCLOSED_BY` carefully to avoid confusing your downstream users.

---

## 4. How to Verify Your Export Is Correct

Never just trust that the export worked. Here are four ways to verify, from quickest to most thorough.

### Check 1: Look at What the COPY Command Returned

When you use `DETAILED_OUTPUT = TRUE`, the `COPY` command itself returns a result showing every file it created and how many rows went into each one. Capture it immediately:

```sql
-- Save the COPY output into a temporary table
CREATE OR REPLACE TEMPORARY TABLE TMP_UNLOAD_AUDIT AS
SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

-- Add up the rows across all files
SELECT SUM(rows_unloaded) AS total_rows_exported FROM TMP_UNLOAD_AUDIT;
```

**Now compare:** Does the total match the count you saved earlier?

```sql
-- These two numbers should be identical
SELECT $ROWS_EXPECTED         AS rows_we_expected;
SELECT SUM(rows_unloaded)     AS rows_we_actually_exported FROM TMP_UNLOAD_AUDIT;
```

If they don't match, something went wrong — see [Common Mistakes](#6-common-mistakes-and-how-to-avoid-them).

---

### Check 2: List the Files in S3

See what actually landed in S3 — check the file names, sizes, and folder structure:

```sql
LIST @PROD.SHARED.SKY_S3_STAGE/orders/parquet/;
```

This shows every file under that path with its size and last-modified timestamp. You should see partition folders if you used `PARTITION BY`.

---

### Check 3: Read the Files Back and Recount (Most Reliable)

The best proof is to **read the S3 files back into Snowflake** (without loading them into a table) and count the rows. If this count matches your original count, you know for sure the files are complete.

```sql
-- Count rows directly from the Parquet files in S3
SELECT COUNT(*) AS rows_in_s3
FROM @PROD.SHARED.SKY_S3_STAGE/orders/parquet/
  (FILE_FORMAT => 'FF_PARQUET');
```

For CSV:

```sql
SELECT COUNT(*) AS rows_in_s3
FROM @PROD.SHARED.SKY_S3_STAGE/orders/csv/
  (FILE_FORMAT => 'FF_CSV');
```

This is powerful — you're querying files in S3 directly from Snowflake, without creating any table. It proves "what's actually in S3 matches what we intended to export."

> See: [Querying Data in Staged Files — Snowflake Docs](https://docs.snowflake.com/en/user-guide/querying-stage)

---

### Check 4: Spot-Check the Actual Data (Optional but Smart)

Do a quick sanity check on the values — make sure amounts look reasonable, no weird characters, etc.

```sql
-- Look at row counts and amount ranges per file
SELECT
  TO_VARCHAR(METADATA$FILENAME) AS file_name,
  COUNT(*)                      AS row_count,
  MIN($3)                       AS min_amount,
  MAX($3)                       AS max_amount
FROM @PROD.SHARED.SKY_S3_STAGE/orders/csv/ (FILE_FORMAT => 'FF_CSV')
GROUP BY 1
ORDER BY 1
LIMIT 20;
```

`METADATA$FILENAME` is a special Snowflake column that tells you which file each row came from — very useful for debugging.

---

## 5. Choosing File Formats, Encryption & Performance

### Which File Format Should You Use?

| Format | Best For | Trade-Off |
|--------|----------|-----------|
| **Parquet** | Analytics tools (Athena, Spark, Glue) — compact, typed columns, fast to scan | Not human-readable — you can't just open it in Notepad |
| **CSV** | Sharing with people or simple tools — everyone understands CSV | Larger files, and you have to be careful with NULLs, quotes, and special characters |
| **JSON** | When downstream expects JSON format | Verbose, larger files |

**Rule of thumb:** Use Parquet for machine-to-machine pipelines. Use CSV when a human needs to read it.

---

### Partitioning — Organizing Files into Folders

`PARTITION BY` creates a folder structure based on a column. For example, partitioning by `order_date` creates:

```
s3://skycart-analytics/exports/orders/parquet/
  partition_0=2025-08-28/
    data_file_001.parquet
  partition_0=2025-08-29/
    data_file_001.parquet
```

**Why this matters:** Downstream tools like Athena can skip entire folders they don't need. If someone only wants August 29th data, Athena reads *only* that folder instead of scanning every file. This saves both time and money.

> **Limitation:** You cannot combine `PARTITION BY` with `SINGLE=TRUE` or `OVERWRITE=TRUE`.

---

### Encryption — Keeping Your Exported Files Secure

If your S3 bucket already uses default encryption (SSE-S3), you're good — no extra config needed.

If your company requires a specific encryption key (KMS), add the encryption option:

```sql
COPY INTO @SKY_S3_STAGE/secure/orders/
FROM ( SELECT ... )
FILE_FORMAT = (FORMAT_NAME = FF_PARQUET)
ENCRYPTION  = (
  TYPE       = 'AWS_SSE_KMS',
  KMS_KEY_ID = 'arn:aws:kms:us-east-1:123456789012:key/abcd-...'
);
```

| Option | When to Use |
|--------|-------------|
| `AWS_SSE_S3` | Bucket's default encryption is enough |
| `AWS_SSE_KMS` | Compliance or security requires a specific encryption key |
| `NONE` | Encryption is handled at the bucket level or not needed |

---

### Performance Tips — Making Exports Faster

- **Don't use `ORDER BY`** unless you actually need sorted output. Sorting the entire result set is expensive and slows down the export significantly.
- **Aim for 50–250 MB per file** using `MAX_FILE_SIZE`. Too many tiny files slow down downstream reads; one giant file prevents parallel processing.
- **Use Parquet** for large exports — it compresses much better than CSV.
- **Use a bigger warehouse** for very large exports. An XL or 2XL warehouse will finish faster (but costs more per second).

---

### Cost — What You Pay For

| What | Details |
|------|---------|
| **Compute (warehouse time)** | You pay for the warehouse while it runs the export. Bigger warehouse = faster but more expensive per second. |
| **Data transfer (egress)** | If your Snowflake account is in `us-east-1` but your S3 bucket is in `eu-west-1`, you'll pay AWS data transfer fees. **Keep them in the same region** to avoid this. |
| **S3 storage** | Standard AWS S3 storage and request charges apply for the exported files. |

---

## 6. Common Mistakes and How to Avoid Them

### Mistake 1: Row Counts Don't Match

**Why it happens:** You counted the rows at one moment but exported data at a different moment — and the data changed in between.

**How to fix:** Always use `AT (TIMESTAMP => $SNAP_TS)` in **both** your count query and your export query. Also double-check that the `WHERE` clause is exactly the same in both.

For CSV exports, mismatched counts can also happen if the file format settings are wrong (e.g., a comma inside a text field gets treated as a delimiter). Check your `FIELD_OPTIONALLY_ENCLOSED_BY` and `RECORD_DELIMITER` settings.

---

### Mistake 2: "AccessDenied" Error or Nothing Appears in S3

**Why it happens:** The IAM role doesn't have the right permissions, or the trust policy between AWS and Snowflake isn't set up correctly.

**How to fix:** Run `DESCRIBE INTEGRATION SKY_OUT_INT` and verify the **IAM User ARN** and **External ID** match what's in your AWS trust policy. Also confirm the S3 policy allows `s3:PutObject` on the correct prefix.

---

### Mistake 3: Error When Using `PARTITION BY` with `OVERWRITE` or `SINGLE`

**Why it happens:** These options are not compatible by design. Snowflake doesn't allow overwriting when partitioning.

**How to fix:** Instead of overwriting, use a **date-stamped folder path** like `.../orders/dt=2025-08-29/`. Each day's export goes into its own folder, and you set up S3 lifecycle rules to clean up old ones.

---

### Mistake 4: Parquet Export Fails on Timestamp Columns

**Why it happens:** Certain Snowflake timestamp types (`TIMESTAMP_TZ`, `TIMESTAMP_LTZ`) don't convert cleanly to Parquet format.

**How to fix:** Cast your timestamp columns to `TIMESTAMP_NTZ` (no timezone) in your SELECT query before exporting:

```sql
SELECT updated_at::TIMESTAMP_NTZ AS updated_at ...
```

---

### Mistake 5: No File Appears in S3 (But No Error Either)

**Why it happens:** If your query returns **zero rows**, Snowflake simply doesn't create any file. It won't error out — it just silently produces nothing.

**How to fix:** If your downstream process expects a file to always exist, either: (a) create a small empty marker file separately, or (b) design the consumer to handle a missing folder gracefully.

---

## 7. Automating This as a Daily Job

Once you've tested the manual steps, wrap everything into an automated pipeline:

1. **Create a Stored Procedure** that does all the steps: capture snapshot, count rows, run the export, verify counts, and log the results into an audit table.

2. **Schedule it with a Snowflake Task** — for example, run at 5:45 AM so files are ready by 6:00 AM.

3. **Use date-stamped folders** like `.../orders/dt=2025-08-29/` so each day's export is isolated. No overwrites, no conflicts, and easy to track what happened on any given day.

---

## 8. Complete Copy-Paste Example

Here's the entire workflow in one block. You can copy this, adjust the table/stage names, and run it.

```sql
-- ============================================
-- STEP 0: Set your context
-- ============================================
USE ROLE SYSADMIN;
USE WAREHOUSE ETL_XL;
USE DATABASE PROD;
USE SCHEMA SALES;

-- ============================================
-- STEP 1: Freeze the data and count the rows
-- ============================================
SET SNAP_TS = CURRENT_TIMESTAMP();

SET ROWS_EXPECTED = (
  SELECT COUNT(*) FROM ORDERS
  AT (TIMESTAMP => $SNAP_TS)
  WHERE status = 'COMPLETED'
    AND order_date = DATEADD(day, -1, CURRENT_DATE())
);

-- ============================================
-- STEP 2: Export to S3 as Parquet, partitioned
-- ============================================
COPY INTO @PROD.SHARED.SKY_S3_STAGE/orders/parquet/
FROM (
  SELECT
    order_id,
    customer_id,
    total_amount::NUMBER(12,2)    AS total_amount,
    order_date,
    updated_at::TIMESTAMP_NTZ     AS updated_at
  FROM ORDERS AT (TIMESTAMP => $SNAP_TS)
  WHERE status = 'COMPLETED'
    AND order_date = DATEADD(day, -1, CURRENT_DATE())
)
FILE_FORMAT      = (FORMAT_NAME = FF_PARQUET)
PARTITION BY     (TO_VARCHAR(order_date, 'YYYY-MM-DD'))
INCLUDE_QUERY_ID = TRUE
DETAILED_OUTPUT  = TRUE;

-- ============================================
-- STEP 3: Capture the export report
-- ============================================
CREATE OR REPLACE TEMPORARY TABLE TMP_UNLOAD_AUDIT AS
SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

-- ============================================
-- STEP 4: Verify — do the numbers match?
-- ============================================
SELECT $ROWS_EXPECTED                    AS rows_we_expected;
SELECT SUM(rows_unloaded) AS rows_we_exported FROM TMP_UNLOAD_AUDIT;

-- ============================================
-- STEP 5: Read back from S3 as a final proof
-- ============================================
SELECT COUNT(*) AS rows_actually_in_s3
FROM @PROD.SHARED.SKY_S3_STAGE/orders/parquet/
  (FILE_FORMAT => 'FF_PARQUET');

-- ============================================
-- STEP 6: (Optional) List files to see structure
-- ============================================
LIST @PROD.SHARED.SKY_S3_STAGE/orders/parquet/;
```

> **Quick tweaks:** Add `ENCRYPTION = (TYPE='AWS_SSE_KMS', KMS_KEY_ID='...')` for KMS encryption, or swap `FF_PARQUET` with `FF_CSV` and add `HEADER = TRUE` for CSV exports.

---

## 9. Quick Verification Checklist

Use this for every export you run:

- [ ] Used the **same snapshot** (`AT TIMESTAMP =>`) in both the count and the export
- [ ] Captured the **COPY result** and the sum of `rows_unloaded` matches the expected count
- [ ] **Read-back count** from S3 (via the stage) matches the expected count
- [ ] **Partition folders** exist as expected (e.g., `partition_0=2025-08-29/`)
- [ ] **File sizes** are reasonable (not thousands of tiny files, not one huge file)
- [ ] For **CSV**: checked that NULLs, quotes, and special characters look correct
- [ ] For **Parquet**: timestamp columns are cast to `TIMESTAMP_NTZ`
- [ ] **Encryption** is correct (if required by your company)

---

## 10. Real-World Tips

### Make Exports Repeatable (Idempotent)

Use `INCLUDE_QUERY_ID = TRUE` so filenames are unique, or write each run into a **dated folder** like `.../dt=2025-08-29/`. This way, re-running the export never accidentally overwrites or duplicates previous output.

### Handle Schema Changes Gracefully

If columns get added or renamed over time, **Parquet handles this better than CSV**. Parquet embeds column names and types inside the file, so downstream tools can adapt. CSV with headers is fragile — adding a column can break parsers that expect a fixed order.

### Think About Your Downstream Users

Choose partition columns based on what your consumers **filter by**. If Marketing always queries by date, partition by date. Avoid creating too many tiny files — tools like Athena are slower when they have to open hundreds of small files versus a few medium-sized ones.

### Keep an Audit Trail

After every export, insert a row into an audit table with the `query_id`, `rows_expected`, `rows_exported`, the S3 prefix, and a pass/fail status. This makes it easy to troubleshoot issues days or weeks later.

---

## 11. Test Your Understanding

Try answering these questions to solidify what you've learned:

1. What's the difference between exporting to a **named external stage** versus using a **direct S3 URL** with `STORAGE_INTEGRATION`? When would you use each?

2. Why do we capture a timestamp with `SET SNAP_TS = CURRENT_TIMESTAMP()` and use `AT (TIMESTAMP => $SNAP_TS)` everywhere? What could go wrong if we didn't?

3. What do `INCLUDE_QUERY_ID` and `DETAILED_OUTPUT` give you, and why are they useful for auditing?

4. Why can't you use `PARTITION BY` together with `SINGLE=TRUE` or `OVERWRITE=TRUE`? How do you work around it?

5. When would you choose **Parquet** over **CSV**? What CSV settings help prevent data corruption?

6. How can you count the rows in your S3 files *without* loading them into a Snowflake table? Write the SQL.

7. What AWS permissions does the storage integration need, and what are the **IAM User ARN** and **External ID** used for?

8. What encryption options are available for S3 exports? When do you need KMS?

9. If your query returns **zero rows**, what happens? How do you handle this in an automated pipeline?

---

## 12. References

| Topic | Link |
|-------|------|
| `COPY INTO <location>` — all export options | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/copy-into-location) |
| `CREATE STORAGE INTEGRATION` — connecting to S3 | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/create-storage-integration) |
| `CREATE STAGE` — named external stages | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/create-stage) |
| Querying data in staged files (read-back) | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/querying-stage) |
