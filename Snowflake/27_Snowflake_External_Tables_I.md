# External Tables in Snowflake

## What Is This About?

Imagine you have data files (CSV, Parquet, JSON) sitting in an S3 bucket. You want to query them with SQL in Snowflake, but you **don't want to load them into a Snowflake table** first. Maybe the data is too large, maybe it changes frequently, or maybe you just want to explore it without the cost of storing it twice.

Snowflake gives you two options for querying files in S3:

1. **A view on a stage** — the simple approach, but it scans every file every time.
2. **An external table** — the smart approach. It keeps a metadata catalog of which files exist, so it only reads the files it needs.

This guide explains what external tables are, why they're better than views on stages, how to create them, and what their limitations are.

---

## Table of Contents

1. [Why Not Just Query the Stage Directly?](#1-why-not-just-query-the-stage-directly)
2. [How External Tables Solve This](#2-how-external-tables-solve-this)
3. [Creating an External Table — Step by Step](#3-creating-an-external-table--step-by-step)
4. [Internal Table vs External Table](#4-internal-table-vs-external-table)
5. [View on Stage vs External Table](#5-view-on-stage-vs-external-table)
6. [Key Features You Should Know](#6-key-features-you-should-know)
7. [Checking Which Files Are Registered](#7-checking-which-files-are-registered)
8. [Common Questions & Answers](#8-common-questions--answers)
9. [References](#9-references)

---

## 1. Why Not Just Query the Stage Directly?

You *can* query files directly from a stage — either with a `SELECT` statement or by wrapping it in a view:

```sql
CREATE OR REPLACE VIEW patient_records_vw AS
SELECT *
FROM @my_s3_stage (FILE_FORMAT => my_parquet_format);
```

This works, but it has serious problems:

- **Full scan every time.** Every query reads *all* the files in S3 from scratch. Whether you have 10 files or 10,000, Snowflake reads them all.
- **No awareness of what changed.** Snowflake doesn't know which files are new, which were deleted, or which were already processed.
- **Gets slow and expensive fast.** As more files accumulate, every query takes longer and costs more.

For quick exploration on a small dataset, this is fine. For anything bigger or production-grade, you need something smarter.

---

## 2. How External Tables Solve This

An **external table** is a Snowflake object that points to files in S3 (or Azure Blob or GCS), but unlike a simple stage query, it maintains a **metadata catalog** inside Snowflake.

This catalog tracks:

- **Which files exist** in the S3 location
- **When each file was added or modified**
- **When files were deleted**

When you run a query, Snowflake **checks the metadata first** to determine which files are relevant, then reads only those files. It doesn't blindly scan everything.

**The result:**

- **Faster queries** — only relevant files are read
- **Lower cost** — less data scanned means fewer credits consumed
- **Partition pruning** — if your files are organized in folders like `/year=2025/month=09/`, Snowflake can skip entire folders that don't match your filter
- **Automatic updates** — with `AUTO_REFRESH`, Snowflake detects new files as they land in S3

Think of it this way: a view on a stage is like searching a library by reading every single book. An external table is like using the library's catalog to find exactly which shelf has what you need.

---

## 3. Creating an External Table — Step by Step

### Step 1: Create a Stage Pointing to S3

The stage tells Snowflake where the files live.

```sql
CREATE OR REPLACE STAGE my_s3_stage
  URL = 's3://mybucket/raw-data/'
  STORAGE_INTEGRATION = my_s3_integration
  FILE_FORMAT = (TYPE = PARQUET);
```

- **`URL`** — the S3 bucket and folder path where your files are
- **`STORAGE_INTEGRATION`** — the secure connection between Snowflake and your AWS account (uses IAM roles, no hardcoded keys)
- **`FILE_FORMAT`** — tells Snowflake how to read the files (Parquet, CSV, JSON, etc.)

---

### Step 2: Create the External Table

```sql
CREATE OR REPLACE EXTERNAL TABLE patient_records_ext
(
  patient_id STRING AS (value:c1::string),
  name       STRING AS (value:c2::string),
  age        INT    AS (value:c3::int),
  diagnosis  STRING AS (value:c4::string)
)
WITH LOCATION = @my_s3_stage
FILE_FORMAT   = (TYPE = PARQUET)
AUTO_REFRESH  = TRUE
PATTERN       = '.*[.]parquet';
```

**What each part means:**

- **Column definitions** — You define columns and tell Snowflake how to extract them from the file. The `AS (value:c1::string)` syntax means "take the first column from the file and treat it as a string." For Parquet/JSON files with named fields, you'd use `value:patient_id::string` instead.

- **`WITH LOCATION`** — Points to the stage (and optionally a subfolder within it).

- **`AUTO_REFRESH = TRUE`** — Tells Snowflake to automatically detect new files in S3. This requires S3 event notifications to be configured (see the [External Table Refresh guide](./27_Snowflake_External_Table_Refresh.md) for setup details).

- **`PATTERN`** — A regex filter for which files to include. `'.*[.]parquet'` means "only include files ending in `.parquet`."

---

### Step 3: Query It Like a Normal Table

```sql
SELECT * FROM patient_records_ext WHERE age > 50;
```

This looks and feels like querying a regular Snowflake table. Behind the scenes, Snowflake:

1. Checks its metadata catalog to identify which files contain data
2. Reads only the relevant files from S3
3. Returns the results

---

## 4. Internal Table vs External Table

When should you use each? Here's a clear comparison:

| | **Internal Table** | **External Table** |
|---|---|---|
| **Where data is stored** | Inside Snowflake (in optimized micro-partitions) | Outside Snowflake (in S3, Azure, GCS) |
| **Query performance** | Fastest — data is compressed, clustered, and optimized | Moderate — still reads from cloud storage, but metadata helps skip irrelevant files |
| **Storage cost** | You pay Snowflake storage rates | You pay cloud storage rates (typically cheaper) |
| **Can you INSERT/UPDATE/DELETE?** | Yes — full DML support | No — external tables are **read-only** |
| **Metadata** | Fully managed automatically by Snowflake | Managed by the external table object (needs `AUTO_REFRESH` or manual refresh) |
| **Best for** | Data you query frequently, curated/cleaned datasets | Raw data lake exploration, semi-structured data, data you query occasionally |

**Rule of thumb:** If analysts query the data daily, load it into an internal table. If it's raw data that gets queried occasionally, or you need to keep it in S3 for other tools, use an external table.

---

## 5. View on Stage vs External Table

This is a common point of confusion. Both let you query S3 files from Snowflake — but they work very differently under the hood.

| Feature | **View on Stage** | **External Table** |
|---------|-------------------|-------------------|
| **Knows which files exist?** | No — rescans everything every time | Yes — maintains a metadata catalog |
| **Query performance** | Slow — reads all files on every query | Faster — only reads relevant files |
| **Partition pruning** | Not possible | Supported (if files are in partitioned folders) |
| **Cost** | Higher — more data scanned per query | Lower — less data scanned |
| **Auto-refresh** | Not applicable — always reads live | Can auto-detect new/deleted files |
| **File visibility** | Can't see which files are being read | Can query `EXTERNAL_TABLE_FILES` to see all registered files |
| **Setup effort** | Very simple — one line | A bit more work (integration, table definition) |
| **Best for** | Quick one-off exploration on small data | Production queries on large datasets |

### A Concrete Example

Your company has 3 years of daily patient files in S3. An analyst wants data for just last month.

- **With a view on stage:** Snowflake reads all 3 years of files. The query takes 20 minutes.
- **With an external table** partitioned by `year/month/day`: Snowflake reads only last month's folder. The query takes 1 minute.

**Summary:** A view on a stage is simple but "dumb" — it always scans everything. An external table is a smart layer that keeps metadata, optimizes scans, and supports partition pruning.

---

## 6. Key Features You Should Know

### Partitioning — Organize for Speed

If your files in S3 are organized in folders like:

```
s3://mybucket/patient_data/year=2025/month=09/day=06/file1.parquet
```

You can define partition columns when creating the external table. Then, when someone queries:

```sql
SELECT * FROM patient_records_ext WHERE year = 2025 AND month = 9;
```

Snowflake only scans the files in the `year=2025/month=09/` folder — it skips everything else. This is called **partition pruning**, and it can make a massive difference in performance and cost.

**Best practice:** Always partition large external tables by the fields your users filter on most (date, region, etc.).

---

### AUTO_REFRESH — Staying in Sync with S3

When `AUTO_REFRESH = TRUE`, Snowflake automatically detects when new files land in S3 or when files are deleted. It updates the metadata catalog without you doing anything.

This requires S3 event notifications to be configured (covered in the [Refresh guide](./27_Snowflake_External_Table_Refresh.md)).

Without event notifications, you must manually refresh:

```sql
ALTER EXTERNAL TABLE patient_records_ext REFRESH;
```

---

### External Tables Are Read-Only

You cannot `INSERT`, `UPDATE`, or `DELETE` data in an external table. The data lives in S3 — Snowflake can only read it.

If you need to transform or modify the data, copy it into an internal table first:

```sql
CREATE OR REPLACE TABLE patient_records_internal AS
SELECT * FROM patient_records_ext WHERE age > 50;
```

Now you can run DML against the internal table.

---

### Schema Evolution — When Files Get New Columns

Real-world files change over time. Maybe your older Parquet files have 3 columns (`patient_id`, `name`, `age`) but newer ones add a 4th (`diagnosis`).

You can handle this by defining all expected columns upfront:

```sql
CREATE EXTERNAL TABLE patient_records_ext (
  patient_id STRING AS (value:patient_id::string),
  name       STRING AS (value:name::string),
  age        INT    AS (value:age::int),
  diagnosis  STRING AS (value:diagnosis::string)
)
WITH LOCATION = @my_s3_stage
FILE_FORMAT = (TYPE = PARQUET);
```

For older files that don't have the `diagnosis` field, that column simply returns `NULL`. No errors.

**Best practice:** For semi-structured data (JSON, Parquet), define columns using the `VARIANT` path syntax. This way, missing fields return NULL instead of causing failures.

---

## 7. Checking Which Files Are Registered

One major advantage of external tables is visibility. You can see exactly which files Snowflake knows about.

```sql
SELECT *
FROM TABLE(INFORMATION_SCHEMA.EXTERNAL_TABLE_FILES(
  TABLE_NAME   => 'PATIENT_RECORDS_EXT',
  DATABASE_NAME => 'MY_DB',
  SCHEMA_NAME  => 'RAW'
));
```

**What you get back:**

| Column | What It Shows |
|--------|---------------|
| `FILE_NAME` | Full S3 path of the file |
| `LAST_MODIFIED` | When the file was last updated in S3 |
| `ROW_COUNT` | Estimated number of rows (if available) |
| `FILE_SIZE` | Size of the file in bytes |
| `STATUS` | Whether the file is ACTIVE or DELETED |

This tells you **exactly what Snowflake has registered** for the external table. If a file is missing from this list, Snowflake won't include it in query results — you'd need to run a manual refresh.

You can also check the registration history to see when files were added or removed:

```sql
SELECT *
FROM TABLE(INFORMATION_SCHEMA.EXTERNAL_TABLE_FILE_REGISTRATION_HISTORY(
  TABLE_NAME => 'PATIENT_RECORDS_EXT'
));
```

---

## 8. Common Questions & Answers

### Why use external tables instead of just querying staged files?

Querying a stage directly scans **all files every time** — no metadata, no pruning, no awareness of what changed. External tables maintain a metadata catalog, so Snowflake only reads the files it needs. For large datasets, this difference can be 10x or more in query speed and cost.

---

### How does AUTO_REFRESH work?

When enabled, Snowflake listens for S3 event notifications (via an SQS queue). When a file is added or deleted, S3 sends a message, and Snowflake updates its metadata. Without event notifications configured, `AUTO_REFRESH` has no effect and you must refresh manually.

---

### Can I insert, update, or delete data in an external table?

No. External tables are strictly **read-only**. If you need to modify the data, copy it into an internal Snowflake table first, then work with it there.

---

### How does partition pruning work?

If your S3 files are organized in folders like `year=2025/month=09/day=06/`, you define those as partition columns. When a query filters on those columns, Snowflake only scans the matching folders — it skips everything else entirely.

---

### What happens when a file is deleted from S3?

If `AUTO_REFRESH` is on (with event notifications configured), Snowflake detects the deletion and removes the file from its metadata. If auto-refresh is off, the metadata still references the deleted file until you run `ALTER EXTERNAL TABLE ... REFRESH`. Either way, Snowflake never deletes the actual S3 file — it only updates its own metadata catalog.

---

### How do I handle new columns appearing in newer files?

Define all possible columns in your external table definition. For files that don't have a particular column, Snowflake returns `NULL` for that field. Using the `VARIANT` path syntax (`value:column_name::type`) handles this gracefully.

---

## 9. References

| Topic | Link |
|-------|------|
| External tables on S3 (auto-refresh) | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/tables-external-s3) |
| `CREATE EXTERNAL TABLE` (all options) | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/create-external-table) |
| `SHOW EXTERNAL TABLES` | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/show-external-tables) |
| Automatic refresh overview | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/tables-external-auto) |
| Querying data in staged files | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/querying-stage) |
