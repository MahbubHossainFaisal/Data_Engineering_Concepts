# COPY Command — COPY_HISTORY and LOAD_HISTORY

## What Is This About?

Every time you run a `COPY INTO` command (or Snowpipe loads a file), Snowflake keeps a record of what happened — which files were loaded, how many rows succeeded, how many failed, and what went wrong. This history is your **forensic toolkit** for data pipelines.

Snowflake gives you two views to access this information:

- **LOAD_HISTORY** — A quick, lightweight summary. Think of it as a flight departure board: "Did my file load? When? How many rows?"
- **COPY_HISTORY** — A deep, detailed record. Think of it as a black box recorder: "How exactly did the load run? What command was used? What broke and where?"

Understanding these two views is essential for troubleshooting missing data, auditing pipelines, and building monitoring alerts.

---

## Table of Contents

1. [LOAD_HISTORY — The Quick Summary View](#1-load_history--the-quick-summary-view)
2. [COPY_HISTORY — The Detailed Investigation View](#2-copy_history--the-detailed-investigation-view)
3. [LOAD_HISTORY vs COPY_HISTORY — Side by Side](#3-load_history-vs-copy_history--side-by-side)
4. [Real-World Troubleshooting Scenarios](#4-real-world-troubleshooting-scenarios)
5. [Retention Limits and How to Keep Longer History](#5-retention-limits-and-how-to-keep-longer-history)
6. [Building Pipeline Alerts on Top of These Views](#6-building-pipeline-alerts-on-top-of-these-views)
7. [Common Questions & Answers](#7-common-questions--answers)

---

## 1. LOAD_HISTORY — The Quick Summary View

`LOAD_HISTORY` lives in the `INFORMATION_SCHEMA` and provides a simple, file-level summary of past COPY operations. One row = one file that was loaded.

### How to Query It

```sql
SELECT *
FROM INFORMATION_SCHEMA.LOAD_HISTORY
WHERE TABLE_NAME = 'SALES_TRANSACTIONS'
  AND LAST_LOAD_TIME > DATEADD(day, -7, CURRENT_TIMESTAMP());
```

This shows all files loaded into the `SALES_TRANSACTIONS` table in the last 7 days.

### Key Columns

| Column | What It Tells You |
|--------|-------------------|
| `FILE_NAME` | The name of the file that was loaded — use this to track missing or duplicate files |
| `LAST_LOAD_TIME` | When the file was loaded |
| `ROW_COUNT` | How many rows were successfully ingested from this file |
| `STATUS` | Whether the load succeeded or failed |
| `FIRST_ERROR_MESSAGE` | If something broke, the first error message |
| `FIRST_ERROR_LINE` | Which line in the file caused the first error |
| `TABLE_NAME` / `SCHEMA_NAME` | Confirms which table the data went into |

### Limitations

- **14-day retention** — history older than 14 days is automatically removed
- **10,000 row limit** — a single query can return at most 10,000 rows. If you load thousands of small files daily, you'll hit this limit quickly
- **Less detail** — it tells you *what* happened, but not *why* or *how*

Use `LOAD_HISTORY` when you need a fast answer to: "Was this file loaded? When? How many rows?"

---

## 2. COPY_HISTORY — The Detailed Investigation View

`COPY_HISTORY` is accessed through a **table function** (not a regular view). It's richer than `LOAD_HISTORY` — it includes the actual COPY statement that ran, error counts, pipe information for Snowpipe, and more.

### How to Query It

```sql
SELECT *
FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
  TABLE_NAME => 'SALES_TRANSACTIONS',
  START_TIME => DATEADD(day, -7, CURRENT_TIMESTAMP()),
  END_TIME   => CURRENT_TIMESTAMP()
));
```

Notice the difference: you pass the table name and a time range as parameters.

### Key Columns

| Column | What It Tells You |
|--------|-------------------|
| `FILE_NAME` | The file that was loaded |
| `LAST_LOAD_TIME` | When it was loaded |
| `ROW_COUNT` | Rows successfully loaded |
| `ERROR_COUNT` | Rows that **failed** — this is the column you want when investigating partial loads |
| `STATUS` | Success, error, or partially loaded |
| `FIRST_ERROR_MESSAGE` | The first error encountered |
| `FIRST_ERROR_LINE_NUMBER` | Which line in the file |
| `FIRST_ERROR_CHARACTER_POS` | Which character position — pinpoints the exact spot |
| `COPY_STATEMENT` | The actual `COPY INTO` SQL that ran — critical for debugging format mismatches |
| `PIPE_NAME` | If the load was done by Snowpipe, which pipe handled it |
| `TABLE_NAME` | Where the data landed |

### Why COPY_HISTORY Is More Useful for Debugging

The key advantages over LOAD_HISTORY:

- **ERROR_COUNT** — tells you how many rows failed (not just whether the load succeeded or not)
- **COPY_STATEMENT** — shows the exact SQL command, including file format settings. If someone used the wrong format, you'll see it here.
- **PIPE_NAME** — connects the load to a specific Snowpipe, essential for debugging automated pipelines
- **Character-level error position** — narrows the problem down to the exact spot in the file

Use `COPY_HISTORY` when you need to answer: "Why did this load fail? How many rows were lost? What command was used?"

---

## 3. LOAD_HISTORY vs COPY_HISTORY — Side by Side

| | **LOAD_HISTORY** | **COPY_HISTORY** |
|---|---|---|
| **How to access** | Regular view: `INFORMATION_SCHEMA.LOAD_HISTORY` | Table function: `TABLE(INFORMATION_SCHEMA.COPY_HISTORY(...))` |
| **Detail level** | Basic — file name, row count, status, first error | Rich — adds error count, COPY statement, pipe name, character position |
| **Shows error count** | No — only first error message | Yes — exact number of failed rows |
| **Shows COPY statement** | No | Yes — the full SQL that ran |
| **Shows Snowpipe info** | No | Yes — which pipe loaded the file |
| **Retention** | 14 days | 14 days |
| **Row limit** | 10,000 rows per query | No hard row limit |
| **Best for** | Quick check: "Was this file loaded?" | Deep investigation: "Why did this load partially fail?" |

**In practice, use both together:**
1. Start with `LOAD_HISTORY` for a quick overview — is the file listed? Did it succeed?
2. Drill into `COPY_HISTORY` when something looks wrong — get the error details, the COPY statement, and the exact failure point.

---

## 4. Real-World Troubleshooting Scenarios

### Scenario 1: "Yesterday's data is missing"

An analyst says the data for September 11th isn't in the `ORDERS` table.

**Step 1 — Check if the file was loaded at all:**

```sql
SELECT FILE_NAME, STATUS, LAST_LOAD_TIME
FROM INFORMATION_SCHEMA.LOAD_HISTORY
WHERE TABLE_NAME = 'ORDERS'
  AND LAST_LOAD_TIME > DATEADD(day, -3, CURRENT_TIMESTAMP());
```

If `orders_2025-09-11.csv` isn't in the results, the file was **never loaded**. The problem is upstream — the file wasn't staged, or the COPY command wasn't run for it.

If the file is listed but `STATUS = LOAD_FAILED`, the load was attempted but failed. Move to Step 2.

**Step 2 — Get the error details:**

```sql
SELECT FILE_NAME, ROW_COUNT, ERROR_COUNT, FIRST_ERROR_MESSAGE, COPY_STATEMENT
FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
  TABLE_NAME => 'ORDERS',
  START_TIME => DATEADD(day, -3, CURRENT_TIMESTAMP()),
  END_TIME   => CURRENT_TIMESTAMP()
));
```

Now you can see *why* it failed — maybe a wrong file format, an encoding issue, or malformed rows.

---

### Scenario 2: "Row count looks lower than expected"

The file was loaded, but the table has fewer rows than expected.

```sql
SELECT FILE_NAME, ROW_COUNT, ERROR_COUNT, FIRST_ERROR_MESSAGE
FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
  TABLE_NAME => 'ORDERS',
  START_TIME => DATEADD(day, -2, CURRENT_TIMESTAMP()),
  END_TIME   => CURRENT_TIMESTAMP()
));
```

You see: `orders_2025-09-11.csv` — 900 rows loaded, 100 rows errored. The `FIRST_ERROR_MESSAGE` says "Numeric value 'N/A' is not recognized." Now you know the source file has bad data in a numeric column, and the COPY command used `ON_ERROR = 'CONTINUE'` (which skipped the bad rows instead of aborting).

To see all the rejected rows, use `VALIDATE`:

```sql
SELECT * FROM TABLE(VALIDATE(ORDERS, JOB_ID => '<query_id>'));
```

---

## 5. Retention Limits and How to Keep Longer History

### The Limitation

Both `LOAD_HISTORY` and `COPY_HISTORY` retain data for only **14 days**. After that, the records are automatically deleted. Additionally, `LOAD_HISTORY` caps results at **10,000 rows** per query.

For many production systems — especially those with compliance, SLA monitoring, or auditing requirements — 14 days isn't enough.

### The Solution: Build Your Own Audit Table

Create a permanent table and populate it daily with a scheduled task:

```sql
-- Create a table to store long-term COPY history
CREATE TABLE IF NOT EXISTS audit.copy_history_archive (
  file_name          STRING,
  table_name         STRING,
  last_load_time     TIMESTAMP_LTZ,
  row_count          NUMBER,
  error_count        NUMBER,
  status             STRING,
  first_error_message STRING,
  copy_statement     STRING,
  pipe_name          STRING,
  archived_at        TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Run this daily (manually, via Snowflake Task, or Airflow)
INSERT INTO audit.copy_history_archive
  (file_name, table_name, last_load_time, row_count, error_count, status, first_error_message, copy_statement, pipe_name)
SELECT
  FILE_NAME, TABLE_NAME, LAST_LOAD_TIME, ROW_COUNT, ERROR_COUNT, STATUS, FIRST_ERROR_MESSAGE, COPY_STATEMENT, PIPE_NAME
FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
  TABLE_NAME => 'ORDERS',
  START_TIME => DATEADD(day, -1, CURRENT_TIMESTAMP()),
  END_TIME   => CURRENT_TIMESTAMP()
));
```

Schedule this with a **Snowflake Task** to run every day. Now you have months or years of load history that you can query anytime.

---

## 6. Building Pipeline Alerts on Top of These Views

Smart data engineering teams don't wait for analysts to report missing data — they build **proactive alerts**.

### Alert 1: Missing File Detection

"Did today's expected file arrive and load?"

```sql
-- Check if today's file was loaded
SELECT COUNT(*) AS files_loaded
FROM INFORMATION_SCHEMA.LOAD_HISTORY
WHERE TABLE_NAME = 'ORDERS'
  AND FILE_NAME LIKE '%' || TO_VARCHAR(CURRENT_DATE(), 'YYYYMMDD') || '%'
  AND LAST_LOAD_TIME > DATEADD(hour, -24, CURRENT_TIMESTAMP());
```

If the count is 0 by a certain cutoff time (e.g., 8 AM), fire a Slack or email alert.

### Alert 2: Row Count Mismatch

Compare the loaded row count against an expected threshold:

```sql
SELECT FILE_NAME, ROW_COUNT, ERROR_COUNT
FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
  TABLE_NAME => 'ORDERS',
  START_TIME => DATEADD(day, -1, CURRENT_TIMESTAMP()),
  END_TIME   => CURRENT_TIMESTAMP()
))
WHERE ERROR_COUNT > 0 OR ROW_COUNT < 1000;
```

Alert if any file has errors or loaded fewer rows than the expected minimum.

### Alert 3: Load Failure Detection

```sql
SELECT FILE_NAME, STATUS, FIRST_ERROR_MESSAGE
FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
  TABLE_NAME => 'ORDERS',
  START_TIME => DATEADD(hour, -6, CURRENT_TIMESTAMP()),
  END_TIME   => CURRENT_TIMESTAMP()
))
WHERE STATUS = 'LOAD_FAILED';
```

Any failed load in the last 6 hours triggers an immediate alert with the error message.

### Alert 4: Snowpipe Inactivity

If a Snowpipe hasn't loaded any files in the expected time window:

```sql
SELECT MAX(LAST_LOAD_TIME) AS last_activity
FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
  TABLE_NAME => 'ORDERS',
  START_TIME => DATEADD(hour, -24, CURRENT_TIMESTAMP()),
  END_TIME   => CURRENT_TIMESTAMP()
))
WHERE PIPE_NAME = 'MY_ORDERS_PIPE';
```

If `last_activity` is more than X hours ago, something may be wrong with the pipe or the upstream file delivery.

These alerts are typically implemented using **Snowflake Tasks** (scheduled SQL), or exported to external monitoring tools like Datadog, CloudWatch, or PagerDuty via Airflow or dbt.

---

## 7. Common Questions & Answers

### What's the difference between LOAD_HISTORY and COPY_HISTORY?

`LOAD_HISTORY` is a lightweight, file-level summary — it tells you whether a file was loaded, when, and how many rows. `COPY_HISTORY` goes deeper — it includes the error count, the exact COPY statement that ran, which Snowpipe was involved, and the character position of the first error. Use `LOAD_HISTORY` for quick checks, `COPY_HISTORY` for investigations.

---

### Why is retention limited to 14 days?

Snowflake limits metadata retention to keep the system lightweight and performant. Storing years of load history for every account would bloat the metadata storage. The 10,000-row limit on `LOAD_HISTORY` is another safeguard against expensive metadata queries. If you need longer retention, build your own audit table and populate it daily.

---

### How do I troubleshoot a missing file?

Start with `LOAD_HISTORY` — search for the file name. If it's not listed, the file was never loaded (check the stage or the COPY command). If it's listed with a failure status, switch to `COPY_HISTORY` for the error details, including the error message, the line number, and the COPY statement that was used.

---

### Which view should I use for partial loads?

**COPY_HISTORY.** It has the `ERROR_COUNT` column that tells you exactly how many rows failed, plus the error message and character position. `LOAD_HISTORY` only tells you the first error — it doesn't quantify how many rows were affected.

---

### How do I keep history longer than 14 days?

Create a permanent audit table and schedule a daily job (Snowflake Task or Airflow) to insert the latest `COPY_HISTORY` results into it. This gives you a persistent archive you can query months or years later for compliance, debugging, or SLA reporting.

---

### Does COPY_HISTORY track Snowpipe loads?

Yes. The `PIPE_NAME` column shows which Snowpipe loaded the file. This is critical for debugging automated pipelines — you can see if a pipe stopped loading, which files it processed, and whether it encountered errors.
