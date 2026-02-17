# Loading Data from S3 into Snowflake

## What Is This About?

When your data lives in AWS S3 as CSV files and you need to bring it into a Snowflake table, you use the `COPY INTO` command. But real-world data is messy — some rows will have bad dates, text where numbers should be, or missing values. You need a strategy to **load the good data**, **catch the bad rows**, **fix them**, and **reload only those fixed rows**.

This guide walks you through the entire process, step by step, in plain English.

> **Real-World Scenario:** You work at "Retail-X." Every hour, new `orders_YYYYMMDD.csv` files land in `s3://retailx-raw/orders/`. Some rows have problems — maybe a date is formatted wrong, or someone typed "N/A" in a numeric column. Your job is to get the clean data into Snowflake, capture the bad rows, fix them, and reload them — without duplicating anything.

---

## Table of Contents

1. [The Big Picture — What's the Plan?](#1-the-big-picture--whats-the-plan)
2. [Setup — File Format, Stage & Table](#2-setup--file-format-stage--table)
3. [Step 1 — Check for Errors First (Without Loading Anything)](#3-step-1--check-for-errors-first-without-loading-anything)
4. [Step 2 — Load the Good Rows](#4-step-2--load-the-good-rows)
5. [Step 3 — Find Out What Went Wrong](#5-step-3--find-out-what-went-wrong)
6. [Step 4 — Fix and Reload Only the Bad Rows](#6-step-4--fix-and-reload-only-the-bad-rows)
7. [How to Monitor Your Loads](#7-how-to-monitor-your-loads)
8. [Frequently Asked Questions](#8-frequently-asked-questions)
9. [Best Practice Summary](#9-best-practice-summary)
10. [References](#10-references)

---

## 1. The Big Picture — What's the Plan?

Here's the workflow at a high level. Every step is explained in detail below.

| Step | What You Do | Why |
|------|-------------|-----|
| **1** | Create a file format, a stage, and a target table | These are the building blocks Snowflake needs to read your S3 files |
| **2** | Validate the files first (a "dry run") | Find every error *before* loading — so you know what you're dealing with |
| **3** | Load with `ON_ERROR = 'CONTINUE'` | This tells Snowflake: "Skip the bad rows, but load everything else" |
| **4** | Capture the error details | Get the list of what went wrong — which rows, which files, what error |
| **5** | Fix the bad rows and reload just those | Either fix the CSV files and re-upload them, or fix the data in SQL |

> See: [COPY INTO \<table\> — Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table)

---

## 2. Setup — File Format, Stage & Table

Before loading any data, you need three things:

### What Is a File Format?

A **file format** tells Snowflake *how to read* your files. For a CSV file, it needs to know: What's the delimiter? Is there a header row? How should it handle NULLs? Are fields wrapped in quotes?

```sql
CREATE OR REPLACE FILE FORMAT retailx_csv_fmt
  TYPE            = CSV
  FIELD_DELIMITER = ','
  SKIP_HEADER     = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  TRIM_SPACE      = TRUE
  NULL_IF         = ('', 'NULL', 'null')
  COMPRESSION     = 'AUTO';
```

**In plain English:** This says "the file is CSV, uses commas, has a header row to skip, fields might be wrapped in double quotes, trim extra spaces, and treat empty strings or the word NULL as actual NULL values."

---

### What Is a Stage?

A **stage** is a pointer to where your files live. Think of it as a bookmark to your S3 location. Instead of typing the full S3 URL every time, you create a stage once and reference it by name.

```sql
CREATE OR REPLACE STAGE retailx_orders_stage
  URL                 = 's3://retailx-raw/orders/'
  STORAGE_INTEGRATION = retailx_s3_int
  FILE_FORMAT         = retailx_csv_fmt;
```

**In plain English:** "Create a stage called `retailx_orders_stage` that points to my S3 bucket, uses my storage integration for authentication, and reads files using the CSV format I defined above."

> **Note:** The `retailx_s3_int` is a **Storage Integration** that handles authentication between Snowflake and AWS. If you haven't created one yet, see the setup guide from earlier lessons.

---

### The Target Table

This is the Snowflake table where the data will end up:

```sql
CREATE OR REPLACE TABLE retailx_orders (
  order_id    INTEGER,
  customer_id STRING,
  created_at  TIMESTAMP_NTZ,
  total_usd   NUMBER(10,2)
);
```

---

## 3. Step 1 — Check for Errors First (Without Loading Anything)

Before actually loading data, you can do a **dry run** to find all the problems upfront. Think of it like a spell-check before printing a document.

### How It Works

Add `VALIDATION_MODE = 'RETURN_ERRORS'` to your `COPY INTO` command. This makes Snowflake scan the files and report every row that *would* fail — without actually inserting anything into your table.

```sql
COPY INTO retailx_orders
  FROM @retailx_orders_stage
  FILE_FORMAT     = (FORMAT_NAME = 'retailx_csv_fmt')
  PATTERN         = '.*orders_20250828.*[.]csv'
  VALIDATION_MODE = 'RETURN_ERRORS';
```

**What you get back:** A result set listing every error — the error message, which file it's in, which line, which column, and the row number.

The `PATTERN` parameter is a regex filter — it tells Snowflake to only scan files whose names match `orders_20250828*.csv`. This is how you target specific files.

---

### Save the Errors to a Table

The validation results are temporary — they disappear after your session ends. To keep them, save them to a table right away:

```sql
CREATE OR REPLACE TABLE retailx_orders_validation_errors AS
SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
```

**What's happening here?** `LAST_QUERY_ID()` grabs the ID of the query you just ran (the validation). `RESULT_SCAN()` reads the result of that query. Together, they let you capture the validation output into a permanent table you can examine at your leisure.

> See: [RESULT_SCAN — Snowflake Docs](https://docs.snowflake.com/en/sql-reference/functions/result_scan)

### One Limitation to Know

`VALIDATION_MODE` does **not** work if your `COPY INTO` includes SQL transformations (like `COPY INTO table FROM (SELECT ...)`). If you need to transform data during the load, you'll need to use the "raw landing table" approach described in [Step 4](#6-step-4--fix-and-reload-only-the-bad-rows).

---

## 4. Step 2 — Load the Good Rows

Now it's time to actually load data. The key decision here is: **what should Snowflake do when it hits a bad row?**

```sql
COPY INTO retailx_orders
  FROM @retailx_orders_stage
  FILE_FORMAT = (FORMAT_NAME = 'retailx_csv_fmt')
  PATTERN     = '.*orders_20250828.*[.]csv'
  ON_ERROR    = 'CONTINUE';
```

### What Does `ON_ERROR` Do?

This setting controls Snowflake's behavior when it encounters a row that can't be loaded (wrong data type, missing required value, etc.):

| Setting | What Snowflake Does | When to Use |
|---------|---------------------|-------------|
| `ABORT_STATEMENT` *(default)* | Stops **everything** at the first bad row. No data gets loaded. | When your data must be 100% clean — you'd rather load nothing than load partial data |
| `SKIP_FILE` | Skips the **entire file** that has even one bad row. Other files still load. | When a single bad row means the whole file is suspect |
| **`CONTINUE`** | Skips **only the bad row** and keeps loading everything else | When you want to get as much good data in as possible, and you'll deal with the bad rows separately |

For our scenario, `CONTINUE` is the right choice — we want all the good orders in the table, and we'll handle the bad ones next.

### What Happens After the Load?

After this command runs, you'll have:

- All the **good rows** sitting in the `retailx_orders` table
- A report showing how many rows were loaded vs. how many had errors
- The ability to dig into the error details using `VALIDATE()` or `COPY_HISTORY`

> See: [COPY_HISTORY — Snowflake Docs](https://docs.snowflake.com/en/sql-reference/functions/copy_history)

---

## 5. Step 3 — Find Out What Went Wrong

Now that the good data is loaded, you need to figure out what went wrong with the bad rows. There are two approaches, and you might use both.

### Approach A: Get the Error Messages (Quick and Easy)

**Run this immediately after your COPY command** — it captures the error details for every row that failed:

```sql
CREATE OR REPLACE TABLE retailx_orders_load_errors AS
SELECT * FROM TABLE(VALIDATE('retailx_orders', JOB_ID => LAST_QUERY_ID()));
```

**What this does:** The `VALIDATE()` function goes back and looks at the errors from the COPY job you just ran. It returns one row per error, including the error message, the file name, line number, and column. Saving it to a table lets you review it anytime.

Think of it like getting an error report — it tells you *why* each row failed, but it doesn't give you the actual data from the row.

> See: [VALIDATE — Snowflake Docs](https://docs.snowflake.com/en/sql-reference/functions/validate)

---

### Approach B: Get the Actual Bad Rows (Better for Fixing)

The error messages tell you *why* rows failed, but you also want the **actual data** from those rows so you can fix it. To do this, you query the files directly in S3 and use `TRY_` functions to find rows that would fail.

**How `TRY_` functions work:** Normally, `CAST('abc' AS INTEGER)` would throw an error. But `TRY_CAST('abc' AS INTEGER)` returns `NULL` instead. So if `TRY_CAST` returns NULL, you know that value is bad.

```sql
CREATE OR REPLACE TABLE retailx_orders_bad_raw AS
SELECT
  t.$1::STRING               AS order_id_raw,
  t.$2::STRING               AS customer_id_raw,
  t.$3::STRING               AS created_at_raw,
  t.$4::STRING               AS total_usd_raw,
  METADATA$FILENAME           AS source_file,
  METADATA$FILE_ROW_NUMBER    AS source_row_num
FROM @retailx_orders_stage (FILE_FORMAT => 'retailx_csv_fmt') t
WHERE TRY_CAST(t.$1 AS INTEGER) IS NULL                          -- order_id isn't a valid number
   OR TRY_TO_TIMESTAMP(t.$3, 'YYYY-MM-DD HH24:MI:SS') IS NULL   -- date is in a wrong format
   OR TRY_CAST(t.$4 AS NUMBER) IS NULL;                          -- total isn't a valid number
```

**What's happening in plain English:**

1. We're reading the raw CSV files directly from S3 (via the stage), treating every column as a plain string (`$1`, `$2`, `$3`, `$4` are positional columns).
2. For each row, we try to convert the values to their expected types using `TRY_CAST` / `TRY_TO_TIMESTAMP`.
3. If any conversion returns NULL, it means that value is bad — and we capture the whole row.
4. `METADATA$FILENAME` and `METADATA$FILE_ROW_NUMBER` tell us exactly which file and which line the bad row came from — invaluable for debugging.

> See: [Querying Staged Files — Snowflake Docs](https://docs.snowflake.com/en/user-guide/querying-stage)

---

### (Optional) Export the Bad Rows to a File

If you want to send the bad rows to someone else to fix (or fix them in Excel), you can export them to an internal stage:

```sql
-- Create an internal stage to hold error files
CREATE OR REPLACE STAGE retailx_error_stage;

-- Export the bad rows as a CSV
COPY INTO @retailx_error_stage/errors_
FROM ( SELECT * FROM retailx_orders_bad_raw )
FILE_FORMAT = (TYPE = CSV  FIELD_DELIMITER = ','  HEADER = TRUE);
```

You can then download these files using the `GET` command, fix the data, re-upload the corrected file, and load just that file.

> See: [COPY INTO \<location\> — Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/copy-into-location)

---

## 6. Step 4 — Fix and Reload Only the Bad Rows

Now you have the bad rows identified. How do you fix them and get them into the production table? Here are two approaches.

### Option 1: The "Raw Landing Table" Approach (Best for Production)

This is the most reliable method. The idea is simple:

**Instead of loading directly into the production table (which has strict types like INTEGER and TIMESTAMP), load everything into a "raw" table where every column is just a STRING.** This way, the COPY command *never* fails — even bad data loads successfully as text. Then you use SQL to sort the good from the bad.

**Step A — Load everything as raw strings:**

```sql
CREATE OR REPLACE TABLE raw_orders_rawcols (
  src_file        STRING,
  file_row_number NUMBER,
  col1 STRING,    -- will become order_id
  col2 STRING,    -- will become customer_id
  col3 STRING,    -- will become created_at
  col4 STRING,    -- will become total_usd
  ingested_at     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

COPY INTO raw_orders_rawcols
  FROM @retailx_orders_stage (FILE_FORMAT => 'retailx_csv_fmt')
  FILE_FORMAT = (FORMAT_NAME = 'retailx_csv_fmt')
  ON_ERROR    = 'CONTINUE';
```

Since every column is a STRING, almost nothing will fail. Now all your data — good and bad — is in Snowflake.

**Step B — Separate the good rows from the bad ones using SQL:**

```sql
-- Move clean rows to the production table
INSERT INTO retailx_orders
SELECT
  TRY_CAST(col1 AS INTEGER),
  col2,
  TRY_TO_TIMESTAMP(col3, 'YYYY-MM-DD HH24:MI:SS'),
  TRY_CAST(col4 AS NUMBER(10,2))
FROM raw_orders_rawcols
WHERE TRY_CAST(col1 AS INTEGER) IS NOT NULL
  AND TRY_TO_TIMESTAMP(col3, 'YYYY-MM-DD HH24:MI:SS') IS NOT NULL
  AND TRY_CAST(col4 AS NUMBER) IS NOT NULL;
```

**What this does:** It tries to convert each column to its proper type. The `WHERE` clause keeps only rows where *all* conversions succeeded — those are your clean rows.

```sql
-- Capture the bad rows into an error table for manual review
CREATE OR REPLACE TABLE retailx_orders_error AS
SELECT * FROM raw_orders_rawcols
WHERE NOT (
      TRY_CAST(col1 AS INTEGER) IS NOT NULL
  AND TRY_TO_TIMESTAMP(col3, 'YYYY-MM-DD HH24:MI:SS') IS NOT NULL
  AND TRY_CAST(col4 AS NUMBER) IS NOT NULL
);
```

**What this does:** The opposite — it keeps rows where *at least one* conversion failed. These are the rows that need human attention.

**Why this approach is recommended:**
- No risk of duplicates — you control exactly what goes into the production table
- Easy to reprocess — just re-run the INSERT from the raw table
- You keep the original raw data for auditing
- Easy to automate with stored procedures

---

### Option 2: Fix the File and Re-Upload It (Quick & Simple)

For one-off fixes, this is faster:

1. Take the bad rows from `retailx_orders_bad_raw` (or download the error CSV from the internal stage).
2. Fix the data — maybe correct a date format or replace "N/A" with a proper number.
3. Save the corrected file with a **new name** (e.g., `orders_20250828_fixed.csv`) and upload it to S3.
4. Load just that one file:

```sql
COPY INTO retailx_orders
  FROM @retailx_orders_stage
  FILES = ('orders_20250828_fixed.csv');
```

> **Important — don't re-upload with the same filename!** Snowflake remembers which files it has already loaded. If you re-upload the same file name with the same content, Snowflake will skip it (it thinks it already loaded it). You must either:
> - Use a **different filename** (like adding `_fixed` to the name), or
> - Use `FORCE = TRUE` — but this reloads the **entire** file, including the good rows you already loaded, causing **duplicates**
>
> The safest approach is always to use a new filename.

---

## 7. How to Monitor Your Loads

### See Errors for a Specific Load Job

```sql
SELECT *
FROM TABLE(VALIDATE('retailx_orders', JOB_ID => '<paste_query_id_here>'));
```

This shows every error from that particular COPY job — which file, which row, what went wrong.

> See: [VALIDATE — Snowflake Docs](https://docs.snowflake.com/en/sql-reference/functions/validate)

---

### See Load History for the Last Few Days

```sql
SELECT *
FROM TABLE(COPY_HISTORY(
  DATEADD('day', -2, CURRENT_TIMESTAMP()),
  CURRENT_TIMESTAMP()
))
WHERE table_name = 'RETAILX_ORDERS'
ORDER BY last_load_time DESC;
```

This shows you which files were loaded, when, how many rows succeeded, and how many errors occurred — for the last 2 days (you can adjust the range).

> See: [COPY_HISTORY — Snowflake Docs](https://docs.snowflake.com/en/sql-reference/functions/copy_history)

---

## 8. Frequently Asked Questions

### When I use `ON_ERROR = 'CONTINUE'`, does Snowflake save the text of the skipped rows?

**Not exactly.** It saves **error metadata** — the error message, file name, line number, and column. You can retrieve this using `VALIDATE()`. But if you want the **actual data values** from the failed rows, you need to query the stage directly with `TRY_` functions (as shown in [Approach B](#approach-b-get-the-actual-bad-rows-better-for-fixing)).

---

### Can I automate this whole process?

**Yes!** You can wrap all of these steps into a **Stored Procedure** and schedule it with a **Snowflake Task**. The procedure would:

1. Run the `COPY INTO` with `ON_ERROR = 'CONTINUE'`
2. Capture errors using `VALIDATE()`
3. Save error details to an error table
4. Run a cleansing procedure to fix common issues
5. Reload the fixed rows

You can also use **Snowpipe** for continuous, automatic loading as new files arrive in S3.

> See: [Troubleshooting Bulk Data Loads — Snowflake Docs](https://docs.snowflake.com/en/user-guide/data-load-bulk-ts)

---

### Should I use `FORCE = TRUE` to reload a file I've already loaded?

**Be very careful with this.** `FORCE = TRUE` tells Snowflake to reload the file even if it already loaded it before. The problem is that it reloads **every row** in the file — including the good rows you already have. This creates **duplicate data**.

**Better approach:** Give the corrected file a new name (like `_fixed.csv`) or use the raw-landing-table method where you INSERT only the rows you need.

---

## 9. Best Practice Summary

| Practice | Why It Matters |
|----------|---------------|
| **Always validate first** | Running `VALIDATION_MODE = 'RETURN_ERRORS'` costs very little and tells you about every problem upfront — no surprises during the actual load |
| **Use a raw landing table** | Loading everything as strings into a raw table means the COPY command never fails. Then you use SQL to clean and transform — you're in full control |
| **For quick fixes, work ad-hoc** | Query the stage with `TRY_` functions to find bad rows, fix the file, rename it, and reload just that file |
| **Always keep an error log** | Use `VALIDATE()` or `RESULT_SCAN()` to capture error details into a permanent table. You'll thank yourself when debugging issues a week later |

---

## 10. References

| Topic | Link |
|-------|------|
| `COPY INTO <table>` — loading data (all options) | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table) |
| `VALIDATE()` — retrieve errors from a load job | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/functions/validate) |
| `RESULT_SCAN()` — capture results from any query | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/functions/result_scan) |
| `COPY_HISTORY` — audit load history | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/functions/copy_history) |
| Querying staged files (`METADATA$FILENAME`, etc.) | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/querying-stage) |
| `COPY INTO <location>` — exporting data | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/copy-into-location) |
| Troubleshooting bulk data loads | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/data-load-bulk-ts) |
| Snowflake metadata tips | [The Information Lab](https://www.theinformationlab.nl/2022/08/26/snowflake-skills-3-metadata/) |
