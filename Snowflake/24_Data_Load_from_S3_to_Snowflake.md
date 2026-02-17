# Data Load from S3 to Snowflake

> **Scenario (Retail-X):** Hourly `orders_YYYYMMDD.csv` files land in `s3://retailx-raw/orders/`. Some rows occasionally contain bad dates or non-numeric totals. The goal is to load everything that's good, capture the bad rows in a place you can fix, then re-load only the fixed rows — safely and repeatably.

---

## Table of Contents

1. [TL;DR — One-Line Plan](#1-tldr--one-line-plan)
2. [Setup — File Format, Stage & Table](#2-setup--file-format-stage--table)
3. [Step 1 — Validate Files (Dry Run)](#3-step-1--validate-files-dry-run)
4. [Step 2 — Load the Good Rows](#4-step-2--load-the-good-rows)
5. [Step 3 — Collect Error Details After Load](#5-step-3--collect-error-details-after-load)
   - [5.1 — Error Metadata (Fast, Built-in)](#51--error-metadata-fast-built-in)
   - [5.2 — Capture Actual Raw Rows That Failed](#52--capture-actual-raw-rows-that-failed)
   - [5.3 — Export Bad Rows to a File](#53--export-bad-rows-to-a-file-optional)
6. [Step 4 — Fix & Re-Load Only the Bad Rows](#6-step-4--fix--re-load-only-the-bad-rows)
   - [Option 1 — Raw-Landing + Transform Workflow (Recommended)](#option-1--raw-landing--transform-workflow-recommended-for-production)
   - [Option 2 — Lightweight Ad-Hoc Fix](#option-2--lightweight-ad-hoc-fix--re-stage)
7. [Audit & Monitoring](#7-audit--monitoring)
8. [FAQ — Quick Answers](#8-faq--quick-answers)
9. [Recommended Production Pattern (Summary)](#9-recommended-production-pattern-summary)
10. [References](#10-references)

---

## 1. TL;DR — One-Line Plan

| Step | Action |
|------|--------|
| **1** | Create file format + stage |
| **2** | Validate files first (`VALIDATION_MODE='RETURN_ERRORS'`) to see problems |
| **3** | Load with `ON_ERROR='CONTINUE'` to let good rows in |
| **4** | Capture error metadata with `VALIDATE(...)` or `RESULT_SCAN(LAST_QUERY_ID())` |
| **5** | Extract actual bad rows (using `TRY_` functions), write to an internal stage or error table, fix them, then re-load only those fixed rows |

> Detailed examples for each step follow below.
> See: [COPY INTO \<table\> — Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table)

---

## 2. Setup — File Format, Stage & Table

Copy/paste and edit names as needed.

### 2a. File Format for CSV

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

### 2b. External Stage

> Assumes you already created the storage integration `retailx_s3_int`.

```sql
CREATE OR REPLACE STAGE retailx_orders_stage
  URL                 = 's3://retailx-raw/orders/'
  STORAGE_INTEGRATION = retailx_s3_int
  FILE_FORMAT         = retailx_csv_fmt;
```

### 2c. Target (Production) Table

```sql
CREATE OR REPLACE TABLE retailx_orders (
  order_id    INTEGER,
  customer_id STRING,
  created_at  TIMESTAMP_NTZ,
  total_usd   NUMBER(10,2)
);
```

> **Note:** If you don't have `retailx_s3_int` yet, create it as a **Storage Integration** — covered in earlier lessons.
> See: [COPY INTO \<table\> — Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table)

---

## 3. Step 1 — Validate Files (Dry Run)

**Why validate first?** `VALIDATION_MODE` scans files and returns row-level error details — you learn what to fix *before* touching production tables. Use this when you want to inspect problems upfront.

```sql
COPY INTO retailx_orders
  FROM @retailx_orders_stage
  FILE_FORMAT     = (FORMAT_NAME = 'retailx_csv_fmt')
  PATTERN         = '.*orders_20250828.*[.]csv'
  VALIDATION_MODE = 'RETURN_ERRORS';
```

This returns a result-set listing each error (error message, file, line, column, row number).

### Save Validation Output to an Error Table

```sql
CREATE OR REPLACE TABLE retailx_orders_validation_errors AS
SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
```

`RESULT_SCAN(LAST_QUERY_ID())` reads the result set returned by the previous `COPY ... VALIDATION_MODE` command. Use that table to inspect full error details (error text, file, row, column).

> See: [RESULT_SCAN — Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/functions/result_scan)

### Important Caveat

`VALIDATION_MODE` does **not** support `COPY` statements that perform SQL transformations during the load (e.g., `COPY INTO table (SELECT ...)`). If you must transform during load, use a raw landing table or ad-hoc queries — covered in the following sections.

> See: [COPY INTO \<table\> — Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table)

---

## 4. Step 2 — Load the Good Rows

```sql
COPY INTO retailx_orders
  FROM @retailx_orders_stage
  FILE_FORMAT = (FORMAT_NAME = 'retailx_csv_fmt')
  PATTERN     = '.*orders_20250828.*[.]csv'
  ON_ERROR    = 'CONTINUE';
```

### What Does `ON_ERROR = 'CONTINUE'` Do?

| ON_ERROR Value | Behavior |
|----------------|----------|
| `ABORT_STATEMENT` *(default)* | Stops the **entire** command at the first error |
| `SKIP_FILE` | Skips the **entire file** on the first error |
| **`CONTINUE`** | **Skips only the bad row**, continues loading remaining rows across all files |

Use `CONTINUE` when you want to ingest all good rows while still discovering bad ones.

> See: [COPY INTO \<table\> — ON_ERROR](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table)

### After This Run You Will Have

- Good rows inserted into `retailx_orders`.
- The load result (query) reports counts of rows loaded vs. errors.
- Metadata about the load available via `TABLE(VALIDATE(...))`, `COPY_HISTORY`, `LOAD_HISTORY`, or `LAST_QUERY_ID()`.

> See: [COPY_HISTORY — Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/functions/copy_history)

---

## 5. Step 3 — Collect Error Details After Load

Two approaches depending on whether you want *metadata about errors* or the *actual raw rows that failed*.

### 5.1 — Error Metadata (Fast, Built-in)

If you executed the `COPY` with `ON_ERROR='CONTINUE'`, capture all errors for that load run **immediately after** your COPY command:

```sql
CREATE OR REPLACE TABLE retailx_orders_load_errors AS
SELECT * FROM TABLE(VALIDATE('retailx_orders', JOB_ID => LAST_QUERY_ID()));
```

`VALIDATE(table, JOB_ID => ...)` returns the errors encountered during the COPY job — one row per error with details (error message, file, line, column, etc.). Save it to a table for triage.

> See: [VALIDATE — Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/functions/validate)

---

### 5.2 — Capture Actual Raw Rows That Failed

> **Recommended** if you want to fix and re-load only those rows.

`VALIDATE` / `RETURN_ERRORS` give you **error metadata**, but don't always return the exact raw CSV text in a convenient column. To get the raw problem rows, query the stage with `TRY_` functions to detect rows that would fail when cast to the target types.

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
WHERE TRY_CAST(t.$1 AS INTEGER) IS NULL                          -- order_id not int
   OR TRY_TO_TIMESTAMP(t.$3, 'YYYY-MM-DD HH24:MI:SS') IS NULL   -- bad date
   OR TRY_CAST(t.$4 AS NUMBER) IS NULL;                          -- bad number
```

**Key notes:**
- When querying a stage directly, positional columns are `$1, $2, ...`.
- `METADATA$FILENAME` and `METADATA$FILE_ROW_NUMBER` tell you exactly which file/row the problem came from.

> See: [Querying Data in Staged Files — Snowflake Documentation](https://docs.snowflake.com/en/user-guide/querying-stage)

---

### 5.3 — Export Bad Rows to a File (Optional)

If you prefer to fix rows offline or hand them to a data-fixer team, write them to an internal stage:

```sql
-- Create a named internal stage for error files
CREATE OR REPLACE STAGE retailx_error_stage;

-- Unload the bad rows to files in that internal stage
COPY INTO @retailx_error_stage/errors_
FROM ( SELECT * FROM retailx_orders_bad_raw )
FILE_FORMAT = (TYPE = CSV  FIELD_DELIMITER = ','  HEADER = TRUE);
```

Now you can `GET` these files from the internal stage, hand-fix them, re-stage them (to S3 or to the internal stage), and load them separately.

> See: [COPY INTO \<location\> — Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/sql/copy-into-location)

---

## 6. Step 4 — Fix & Re-Load Only the Bad Rows

Pick one of these two approaches based on scale and automation needs.

### Option 1 — Raw-Landing + Transform Workflow (Recommended for Production)

This is the most robust pattern: no duplicate risk, easy reprocessing, easier to automate, and you keep raw immutable data for replay.

**Step A — Load everything into a raw table with a loose schema** (all `VARCHAR`) so the COPY never fails due to type mismatch:

```sql
CREATE OR REPLACE TABLE raw_orders_rawcols (
  src_file        STRING,
  file_row_number NUMBER,
  col1 STRING,
  col2 STRING,
  col3 STRING,
  col4 STRING,
  ingested_at     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

COPY INTO raw_orders_rawcols
  FROM @retailx_orders_stage (FILE_FORMAT => 'retailx_csv_fmt')
  FILE_FORMAT = (FORMAT_NAME = 'retailx_csv_fmt')
  ON_ERROR    = 'CONTINUE';
```

**Step B — Use SQL with `TRY_` functions** to validate/clean rows. Insert clean rows into the production table and write unfixable rows into an error table for manual remediation:

```sql
-- Insert clean rows
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

-- Capture unfixable rows
CREATE OR REPLACE TABLE retailx_orders_error AS
SELECT * FROM raw_orders_rawcols
WHERE NOT (
      TRY_CAST(col1 AS INTEGER) IS NOT NULL
  AND TRY_TO_TIMESTAMP(col3, 'YYYY-MM-DD HH24:MI:SS') IS NOT NULL
  AND TRY_CAST(col4 AS NUMBER) IS NOT NULL
);
```

---

### Option 2 — Lightweight Ad-Hoc Fix & Re-Stage

1. Use the `retailx_orders_bad_raw` table from [Step 5.2](#52--capture-actual-raw-rows-that-failed) or the exported CSV on `@retailx_error_stage`.
2. Fix the CSV rows (manually or with a script).
3. Re-stage the corrected file with a **new filename** (so the checksum changes), e.g., `orders_20250828_fixed.csv` in S3 or an internal stage.
4. Load only that file:

```sql
COPY INTO retailx_orders
  FROM @retailx_orders_stage
  FILES = ('orders_20250828_fixed.csv');
```

> **Warning:** Do **not** re-run `COPY` on the original file without changing the filename or without using `FORCE=TRUE`. `FORCE=TRUE` will re-load the **entire** file and duplicate already-loaded good rows. Prefer creating a new corrected file or loading fixed rows directly from an error table via `INSERT`.
>
> See: [COPY INTO \<table\> — Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table)

---

## 7. Audit & Monitoring

### Row-Level Errors

```sql
SELECT *
FROM TABLE(VALIDATE('retailx_orders', JOB_ID => '<query_id>'));
```

Or use `TABLE(RESULT_SCAN(LAST_QUERY_ID()))` after a `VALIDATION_MODE` load.

> See: [VALIDATE — Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/functions/validate)

### File-Level Load History (Last 14 Days)

```sql
SELECT *
FROM TABLE(COPY_HISTORY(
  DATEADD('day', -2, CURRENT_TIMESTAMP()),
  CURRENT_TIMESTAMP()
))
WHERE table_name = 'RETAILX_ORDERS'
ORDER BY last_load_time DESC;
```

This shows which files were processed, rows loaded, and error counts.

> See: [COPY_HISTORY — Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/functions/copy_history)

---

## 8. FAQ — Quick Answers

### Does `ON_ERROR = 'CONTINUE'` record the skipped row text?

It records **error metadata** (line, column, error message) that you can get via `VALIDATE` or `VALIDATION_MODE`. If you want the exact original row fields, query the stage with positional `$1, $2, ...` and `TRY_` functions to capture the raw row into a table or stage.

> See: [VALIDATE — Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/functions/validate)

### Can I automate this whole fix-and-reload?

**Yes.** Wrap the steps in a **stored procedure** or **Snowflake Task**:

1. `VALIDATE` or `COPY` with `CONTINUE`
2. `VALIDATE(...)` → store errors
3. Generate error file or error table
4. Run cleansing stored proc / external job to fix errors
5. Stage corrected files and `COPY` them in

You can also use **Snowpipe** for continuous loads and monitor error outputs similarly.

> See: [Troubleshooting Bulk Data Loads — Snowflake Documentation](https://docs.snowflake.com/en/user-guide/data-load-bulk-ts)

### Should I ever use `FORCE=TRUE` to reload the same file after fixing it?

Only if you're sure you want to re-load **all** rows in that file (and deduplicate later). Prefer staging corrected rows as new files or using the raw-landing & SQL-cleanse approach to avoid duplicates.

> See: [COPY INTO \<table\> — Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table)

---

## 9. Recommended Production Pattern (Summary)

| Principle | Details |
|-----------|---------|
| **Always validate first** | `VALIDATION_MODE='RETURN_ERRORS'` is low cost and prevents surprises — especially on first feed runs |
| **Land raw data in a raw table** | Use all `STRING`/`VARIANT` columns. Use idempotent transformation SQL to push clean data to final tables and write bad rows to an error table for human review |
| **For ad-hoc operations** | Extract bad rows using `SELECT` from stage with `TRY_` functions, write to an internal stage or table, fix, and reload only corrected files |
| **Keep an error log** | Use `VALIDATE` / `RESULT_SCAN(LAST_QUERY_ID())` to capture error metadata and persist to a triage table |

---

## 10. References

| Topic | Link |
|-------|------|
| `COPY INTO <table>` (VALIDATION_MODE, ON_ERROR, PATTERN, PURGE) | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table) |
| `VALIDATE(table, JOB_ID => ...)` table function | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/functions/validate) |
| `RESULT_SCAN(LAST_QUERY_ID())` — capture result sets | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/functions/result_scan) |
| `COPY_HISTORY` / Load History for auditing | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/functions/copy_history) |
| Querying staged file metadata (`METADATA$FILENAME`, etc.) | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/querying-stage) |
| `COPY INTO <location>` — unload data to stage | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/copy-into-location) |
| Troubleshooting bulk data loads | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/data-load-bulk-ts) |
| Snowflake metadata tips | [The Information Lab](https://www.theinformationlab.nl/2022/08/26/snowflake-skills-3-metadata/) |
