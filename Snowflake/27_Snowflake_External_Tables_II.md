# External Tables in Snowflake — Part II (Metadata, Caching & Partitions)

## What Is This About?

[Part I](./27_Snowflake_External_Tables_I.md) covered the fundamentals — what external tables are, why they're better than views on stages, and how to create one. This guide goes deeper into the **operational** side:

- How Snowflake tracks which files belong to an external table (metadata)
- What happens when files are added, deleted, or updated in S3
- How Snowflake's caching layers can show you "stale" data and how to deal with it
- How partitioning works and when to use auto vs manual partitions

If Part I was "what and why," this is "how it actually works in production."

---

## Table of Contents

**Metadata & File Management**

1. [The Most Important Command — Refreshing Metadata](#1-the-most-important-command--refreshing-metadata)
2. [Inspecting What Snowflake Knows About Your Files](#2-inspecting-what-snowflake-knows-about-your-files)
3. [What Happens When You Add, Delete, or Update Files](#3-what-happens-when-you-add-delete-or-update-files)
4. [Understanding Snowflake's Caching Layers](#4-understanding-snowflakes-caching-layers)
5. [Troubleshooting Playbook](#5-troubleshooting-playbook)

**Partitioning**

6. [Why Partitions Matter](#6-why-partitions-matter)
7. [Creating a Partitioned External Table (Auto Partitions)](#7-creating-a-partitioned-external-table-auto-partitions)
8. [Manual Partitions — When You Need Full Control](#8-manual-partitions--when-you-need-full-control)
9. [Auto vs Manual Partitions — Which to Use](#9-auto-vs-manual-partitions--which-to-use)
10. [Useful Metadata Columns for Querying](#10-useful-metadata-columns-for-querying)

**Reference**

11. [Command Cheat Sheet](#11-command-cheat-sheet)
12. [Common Questions & Answers](#12-common-questions--answers)
13. [Best Practices](#13-best-practices)
14. [References](#14-references)

---

# Metadata & File Management

## 1. The Most Important Command — Refreshing Metadata

External tables maintain a **metadata catalog** — a list of which files exist, their sizes, checksums, and when they were registered. But this catalog doesn't update itself automatically unless you've configured event notifications with `AUTO_REFRESH`.

When files change in S3, you need to tell Snowflake to resync its metadata:

```sql
-- Refresh the entire external table's metadata
ALTER EXTERNAL TABLE mydb.public.my_ext_table REFRESH;

-- Refresh only a specific subfolder (faster for partitioned tables)
ALTER EXTERNAL TABLE mydb.public.my_ext_table REFRESH '2025/09/05/';
```

This command reads the S3 path, compares it to what Snowflake has recorded, and:
- **Registers** any new files it finds
- **Unregisters** any files that have been deleted from S3
- **Updates** the record for any files whose contents have changed (different checksum)

You can also manage individual files manually:

```sql
-- Register a specific file without full refresh
ALTER EXTERNAL TABLE my_ext_table ADD FILES ('path/file1.parquet');

-- Unregister a specific file
ALTER EXTERNAL TABLE my_ext_table REMOVE FILES ('path/file1.parquet');

-- Turn auto-refresh on
ALTER EXTERNAL TABLE my_ext_table SET AUTO_REFRESH = TRUE;
```

> **Who can run these?** Only the table owner (or a role with equivalent privileges). You also need `USAGE` on the stage and file format.

---

## 2. Inspecting What Snowflake Knows About Your Files

Snowflake gives you three tools to see the state of your external table's metadata. These are essential for debugging.

### See Currently Registered Files

This shows every file Snowflake currently knows about:

```sql
SELECT *
FROM TABLE(INFORMATION_SCHEMA.EXTERNAL_TABLE_FILES(
  TABLE_NAME => 'MY_EXT_TABLE'
));
```

| Column | What It Shows |
|--------|---------------|
| `FILE_NAME` | Full S3 path of the file |
| `REGISTERED_ON` | When Snowflake first registered this file |
| `FILE_SIZE` | Size in bytes |
| `LAST_MODIFIED` | When the file was last modified in S3 |
| `ETAG` / `MD5` | Checksum — changes when file content changes |

Use this to confirm what files Snowflake *thinks* exist. If a file isn't listed here, Snowflake won't include it in query results.

---

### See the History of File Changes

This shows the audit trail — when files were registered, updated, or unregistered:

```sql
SELECT *
FROM TABLE(INFORMATION_SCHEMA.EXTERNAL_TABLE_FILE_REGISTRATION_HISTORY(
  TABLE_NAME => 'MY_EXT_TABLE',
  START_TIME => DATEADD('hour', -24, CURRENT_TIMESTAMP())
));
```

The `OPERATION_STATUS` column tells you what happened:

| Status | Meaning |
|--------|---------|
| `REGISTERED_NEW` | A new file was discovered and added to the catalog |
| `REGISTERED_UPDATE` | An existing file was overwritten with new contents (different checksum) |
| `UNREGISTERED` | A file was removed from the catalog (deleted from S3) |
| `REGISTER_FAILED` | Something went wrong during registration |

---

### Check Auto-Refresh Pipeline Status

If you've configured `AUTO_REFRESH`, Snowflake uses an internal Snowpipe behind the scenes. You can check its health:

```sql
SELECT SYSTEM$EXTERNAL_TABLE_PIPE_STATUS('MYDB.PUBLIC.MY_EXT_TABLE');
```

This returns JSON showing the execution state, number of pending files, the notification channel (SQS ARN), and the last received message timestamp. Very useful when auto-refresh seems broken.

---

## 3. What Happens When You Add, Delete, or Update Files

Let's walk through each scenario using a real example: your team uploads daily files to `s3://company/data/daily/`.

### Scenario A: A New File Is Added to S3

**With `AUTO_REFRESH = FALSE` (or no event notifications):**
Nothing happens in Snowflake. The file is in S3, but Snowflake's metadata doesn't know about it. Queries won't include data from the new file until you run:

```sql
ALTER EXTERNAL TABLE reports.daily REFRESH;
```

**With `AUTO_REFRESH = TRUE` (and event notifications configured):**
S3 sends a notification to Snowflake's SQS queue. Snowflake picks it up and automatically adds the file to the metadata catalog. You can verify with `SYSTEM$EXTERNAL_TABLE_PIPE_STATUS`.

---

### Scenario B: A File Is Deleted from S3

This is where things get tricky, because Snowflake has **multiple caching layers** that can show you data from a file that no longer exists.

**What happens step by step:**

1. Someone deletes `s3://company/data/daily/2025-09-03/file.csv` from S3.
2. Snowflake's metadata **still lists the file as registered** — it hasn't been told about the deletion yet.
3. If you query the external table, you might still see the deleted file's data (due to caching — explained in the next section).
4. After running `ALTER EXTERNAL TABLE ... REFRESH`, the file is marked as `UNREGISTERED` in the registration history.
5. Now queries will stop returning data from that file.

**If you still see stale data after refreshing,** you may be hitting Snowflake's result cache or warehouse cache. See the [caching section](#4-understanding-snowflakes-caching-layers) for how to clear them.

---

### Scenario C: A File Is Overwritten (Same Name, New Content)

When a file at the same S3 path is replaced with new content:

1. The file's **checksum (ETAG/MD5) changes** in S3.
2. After a refresh, Snowflake's registration history shows `REGISTERED_UPDATE` for that file.
3. Subsequent queries return the new content.

**For a safe, atomic replacement** (so readers don't see a half-updated state):

```sql
BEGIN;
  ALTER EXTERNAL TABLE my_ext_table REMOVE FILES ('path/f1.parquet');
  ALTER EXTERNAL TABLE my_ext_table ADD FILES ('path/f1.parquet');
COMMIT;
```

Wrapping it in a transaction ensures the metadata switches cleanly for concurrent readers.

---

## 4. Understanding Snowflake's Caching Layers

This is critical for understanding why you might see "stale" data from deleted or updated files. Snowflake has **three caching layers**, and each one can return old data independently.

### Cache Layer 1: Result Cache (Cloud Services)

**What it is:** When you run a query, Snowflake saves the complete result. If you (or anyone) runs the **exact same query** again within ~24 hours, Snowflake returns the saved result instantly without scanning any files.

**How it causes stale data:** If you queried the external table before a file was deleted, and then run the same query after deletion, you might get the cached result (which still includes the deleted file's data).

**How to bypass it:**

```sql
ALTER SESSION SET USE_CACHED_RESULT = FALSE;
-- Now re-run your query
```

---

### Cache Layer 2: Metadata Cache (Cloud Services)

**What it is:** Snowflake's control plane caches the metadata catalog (which files are registered). If metadata hasn't been refreshed, Snowflake still thinks the deleted file exists and will plan to read it.

**How to fix it:** Run `ALTER EXTERNAL TABLE ... REFRESH` to resync the metadata.

---

### Cache Layer 3: Warehouse Local Cache (Compute Layer / SSD)

**What it is:** When a virtual warehouse reads file data, it caches the data blocks on local SSD. If the same warehouse reads the same file again, it can use the cached blocks without contacting S3.

**How it causes stale data:** Even after metadata refresh, the warehouse might serve data from its local SSD cache (which still has the old file's blocks).

**How to clear it:** Suspend and resume the warehouse (this drops the local cache):

```sql
ALTER WAREHOUSE my_wh SUSPEND;
ALTER WAREHOUSE my_wh RESUME;
```

Or run the query on a different warehouse.

---

### Summary of Caching Behavior

| What You See | Why | How to Fix |
|-------------|-----|-----------|
| Deleted file's data still appears | Result cache returning a saved result | `ALTER SESSION SET USE_CACHED_RESULT = FALSE;` and re-query |
| Deleted file still listed in metadata | Metadata not refreshed | `ALTER EXTERNAL TABLE ... REFRESH;` |
| Data still appears after metadata refresh | Warehouse SSD cache serving old blocks | Suspend/resume the warehouse, or use a different one |

---

## 5. Troubleshooting Playbook

When something seems off with your external table, run through these steps in order:

**Step 1 — Is the file actually in S3?**

```bash
aws s3 ls s3://company/data/daily/2025-09-05/
```

Confirm the file exists (or doesn't) at the expected path.

**Step 2 — What does Snowflake think?**

```sql
-- What files are currently registered?
SELECT * FROM TABLE(INFORMATION_SCHEMA.EXTERNAL_TABLE_FILES(TABLE_NAME => 'MY_EXT_TABLE'));

-- What changed recently?
SELECT * FROM TABLE(INFORMATION_SCHEMA.EXTERNAL_TABLE_FILE_REGISTRATION_HISTORY(
  TABLE_NAME => 'MY_EXT_TABLE',
  START_TIME => DATEADD('hour', -12, CURRENT_TIMESTAMP())
));

-- Is auto-refresh working?
SELECT SYSTEM$EXTERNAL_TABLE_PIPE_STATUS('MYDB.PUBLIC.MY_EXT_TABLE');
```

**Step 3 — Force a metadata sync:**

```sql
ALTER EXTERNAL TABLE my_ext_table REFRESH;
```

**Step 4 — Rule out result cache:**

```sql
ALTER SESSION SET USE_CACHED_RESULT = FALSE;
-- Re-run your query
```

**Step 5 — Rule out warehouse cache:**

Suspend and resume the warehouse, then re-query. Or run on a different warehouse.

**Step 6 — Manually unregister a file if needed:**

```sql
ALTER EXTERNAL TABLE my_ext_table REMOVE FILES ('path/to/problematic_file');
```

---

# Partitioning

## 6. Why Partitions Matter

Imagine you have **10 million log files** in S3, spanning 3 years. Without partitioning, every query — even one that only wants yesterday's data — must scan metadata for **all 10 million files**. That's slow and expensive.

Partitioning tells Snowflake: "These files are organized into folders by year, month, and day." Now when someone queries for `WHERE year = '2025' AND month = '09' AND day = '05'`, Snowflake immediately knows to only look at files in that specific folder. It skips everything else entirely.

This is called **partition pruning**, and it's the single biggest performance optimization for external tables.

---

## 7. Creating a Partitioned External Table (Auto Partitions)

When your S3 files are organized in a standard folder structure like:

```
s3://company/logs/year=2025/month=09/day=05/file1.json
s3://company/logs/year=2025/month=09/day=06/file2.json
```

You can define the external table to **automatically extract partition values from the folder names**:

```sql
CREATE OR REPLACE EXTERNAL TABLE logs_ext (
  log_data VARIANT,
  year     STRING AS (METADATA$EXTERNAL_TABLE_PARTITION['year']),
  month    STRING AS (METADATA$EXTERNAL_TABLE_PARTITION['month']),
  day      STRING AS (METADATA$EXTERNAL_TABLE_PARTITION['day'])
)
PARTITION BY (year, month, day)
LOCATION = @my_s3_stage/logs/
FILE_FORMAT = (TYPE = JSON);
```

**What `METADATA$EXTERNAL_TABLE_PARTITION` does:** It's a special Snowflake object that reads the partition key-value pairs from folder names (like `year=2025`). Think of it as a dictionary:

```json
{ "year": "2025", "month": "09", "day": "05" }
```

You use it to map folder names into queryable columns.

**Now you can query efficiently:**

```sql
-- Only scans files in the year=2025/month=09/day=05 folder
SELECT COUNT(*) FROM logs_ext
WHERE year = '2025' AND month = '09' AND day = '05';
```

When you run `ALTER EXTERNAL TABLE logs_ext REFRESH`, Snowflake automatically discovers new partitions from the folder structure. No manual work needed.

---

## 8. Manual Partitions — When You Need Full Control

Sometimes your folder structure doesn't follow the standard `key=value` pattern, or you want explicit control over which folders map to which partitions.

For example, quarterly financial data stored like:

```
s3://company/finance/2025-Q1/report.parquet
s3://company/finance/2025-Q2/report.parquet
```

You can define partitions manually:

```sql
CREATE OR REPLACE EXTERNAL TABLE finance_ext (
  report  VARIANT,
  quarter STRING
)
PARTITION BY (quarter)
LOCATION = @my_s3_stage/finance/
FILE_FORMAT = (TYPE = PARQUET);
```

Then add each partition by hand:

```sql
ALTER EXTERNAL TABLE finance_ext
  ADD PARTITION (quarter = '2025-Q1')
  LOCATION = @my_s3_stage/finance/2025-Q1/;

ALTER EXTERNAL TABLE finance_ext
  ADD PARTITION (quarter = '2025-Q2')
  LOCATION = @my_s3_stage/finance/2025-Q2/;
```

To remove a partition:

```sql
ALTER EXTERNAL TABLE finance_ext DROP PARTITION (quarter = '2025-Q2');
```

To see all registered partitions:

```sql
SELECT * FROM TABLE(INFORMATION_SCHEMA.EXTERNAL_TABLE_PARTITIONS(
  TABLE_NAME => 'FINANCE_EXT'
));
```

### The Big Limitation of Manual Partitions

You **cannot** use `ALTER EXTERNAL TABLE ... REFRESH` on a manually partitioned table. Snowflake will return:

> "Operation external table refresh not supported for external tables with user-specified partition"

The reason: `REFRESH` works by auto-discovering partitions from the folder structure. If you've told Snowflake explicitly what the partitions are, these two approaches conflict. With manual partitions, you must `ADD PARTITION` and `DROP PARTITION` yourself every time the data changes.

This also means **`AUTO_REFRESH` doesn't work** with manual partitions.

---

## 9. Auto vs Manual Partitions — Which to Use

| | **Auto Partitions** | **Manual Partitions** |
|---|---|---|
| **How it works** | Snowflake reads folder names like `year=2025/month=09/` and creates partitions automatically | You define each partition explicitly with `ADD PARTITION` |
| **Refresh support** | `REFRESH` works — discovers new partitions automatically | `REFRESH` is **not** supported — you must add/drop partitions manually |
| **Auto-refresh** | Supported (with event notifications) | **Not supported** |
| **Setup effort** | Low — just define the table, Snowflake does the rest | Higher — every new partition needs a manual `ALTER TABLE` |
| **Best for** | Continuously arriving data (logs, events, daily files) | Fixed business periods (quarters, fiscal years) or non-standard folder structures |

**Rule of thumb:** If your data arrives regularly (daily files, streaming events), use auto partitions. If your data is organized into fixed, known periods and you want explicit control, use manual partitions.

---

## 10. Useful Metadata Columns for Querying

Snowflake provides special pseudo-columns you can use when querying external tables:

| Column | What It Shows | Example Use |
|--------|--------------|-------------|
| `METADATA$FILENAME` | Full S3 path of the file each row came from | Filter for a specific file: `WHERE METADATA$FILENAME LIKE '%file1.json'` |
| `METADATA$FILE_ROW_NUMBER` | Row number within the file | Useful for debugging or deduplication |
| `METADATA$FILE_LAST_MODIFIED` | When the file was last modified in S3 | Check data freshness |
| `METADATA$EXTERNAL_TABLE_PARTITION` | The partition key-value pairs for each row | See which partition a row belongs to |

**Example — Query a single specific file:**

```sql
SELECT * FROM logs_ext
WHERE METADATA$FILENAME LIKE '%day=05/file1.json';
```

**Example — Combine partition pruning with file filtering:**

```sql
SELECT * FROM logs_ext
WHERE year = '2025' AND month = '09' AND day = '05'
  AND METADATA$FILENAME LIKE '%file1.json';
```

---

# Reference

## 11. Command Cheat Sheet

```sql
-- ===== Metadata Refresh =====
ALTER EXTERNAL TABLE db.schema.ext_table REFRESH;
ALTER EXTERNAL TABLE db.schema.ext_table REFRESH '2025/09/';

-- ===== Manual File Management =====
ALTER EXTERNAL TABLE db.schema.ext_table ADD FILES ('path/file1.parquet', 'path/file2.parquet');
ALTER EXTERNAL TABLE db.schema.ext_table REMOVE FILES ('path/file1.parquet');

-- ===== Inspect Registered Files =====
SELECT * FROM TABLE(INFORMATION_SCHEMA.EXTERNAL_TABLE_FILES(TABLE_NAME => 'EXT_TABLE'));

-- ===== Registration History (Audit Trail) =====
SELECT * FROM TABLE(INFORMATION_SCHEMA.EXTERNAL_TABLE_FILE_REGISTRATION_HISTORY(
  TABLE_NAME => 'EXT_TABLE',
  START_TIME => DATEADD('day', -1, CURRENT_TIMESTAMP())
));

-- ===== Auto-Refresh Pipeline Health =====
SELECT SYSTEM$EXTERNAL_TABLE_PIPE_STATUS('DB.SCHEMA.EXT_TABLE');

-- ===== Partition Management =====
ALTER EXTERNAL TABLE finance_ext ADD PARTITION (quarter = '2025-Q3') LOCATION = @stage/finance/2025-Q3/;
ALTER EXTERNAL TABLE finance_ext DROP PARTITION (quarter = '2025-Q2');
SELECT * FROM TABLE(INFORMATION_SCHEMA.EXTERNAL_TABLE_PARTITIONS(TABLE_NAME => 'FINANCE_EXT'));

-- ===== Cache Bypass =====
ALTER SESSION SET USE_CACHED_RESULT = FALSE;
```

---

## 12. Common Questions & Answers

### How does Snowflake know which files belong to an external table?

It stores file-level metadata — file names, checksums (ETAG/MD5), last modified timestamps, and registration timestamps. This metadata is updated by `REFRESH` or automatically via event notifications when `AUTO_REFRESH` is enabled.

---

### What happens if you delete a file from S3 but don't refresh?

Snowflake's metadata still lists the file. Queries may still return the deleted file's data (from caches). After you run `REFRESH`, the file is marked `UNREGISTERED` and queries stop including it.

---

### How do you force Snowflake to forget about a specific file?

```sql
ALTER EXTERNAL TABLE my_ext_table REMOVE FILES ('path/to/file');
```

Verify with the registration history — you should see an `UNREGISTERED` event.

---

### Why does my query still show deleted data even after refreshing?

You're likely hitting one of Snowflake's caches. Try these in order:
1. Disable result cache: `ALTER SESSION SET USE_CACHED_RESULT = FALSE;`
2. If still stale, suspend and resume the warehouse to clear the local SSD cache.

---

### How do you safely replace a file without inconsistent reads?

Wrap the metadata change in a transaction:

```sql
BEGIN;
  ALTER EXTERNAL TABLE my_ext_table REMOVE FILES ('path/file.parquet');
  ALTER EXTERNAL TABLE my_ext_table ADD FILES ('path/file.parquet');
COMMIT;
```

---

### Why can't you use REFRESH on a manually partitioned table?

`REFRESH` auto-discovers partitions from folder structure. Manual partitions mean you've told Snowflake explicitly what the partitions are — these two approaches would conflict. With manual partitions, you must manage them yourself using `ADD PARTITION` and `DROP PARTITION`.

---

### When would you choose manual partitioning over auto?

Use manual partitions when your data is organized into fixed, known periods (fiscal quarters, annual reports) or when the folder structure doesn't follow the `key=value` naming convention. Use auto partitions for everything else — especially continuously arriving data like logs or events.

---

## 13. Best Practices

| Practice | Why |
|----------|-----|
| **Configure event notifications + `AUTO_REFRESH = TRUE`** | Keeps metadata in sync automatically — the foundation of reliable external tables |
| **Monitor registration history regularly** | Set up alerts to catch `REGISTER_FAILED` events before they become data gaps |
| **Use transactions for file replacements** | `BEGIN; REMOVE FILES; ADD FILES; COMMIT;` prevents readers from seeing inconsistent state |
| **Consider Iceberg tables for heavy update workloads** | External tables are read-only. If you need ACID updates on files in object storage, Snowflake's Iceberg table support is a better fit |
| **Copy hot data into internal tables** | External tables are slower than internal tables (data still lives in S3). For frequently queried datasets, load them into Snowflake for better performance |
| **Partition by the fields users filter on most** | Date, region, or any high-cardinality filter — partition pruning is the biggest performance lever for external tables |

---

## 14. References

| Topic | Link |
|-------|------|
| Introduction to external tables | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/tables-external-intro) |
| `ALTER EXTERNAL TABLE` (refresh, add/remove files) | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/alter-external-table) |
| `EXTERNAL_TABLE_FILES` function | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/functions/external_table_files) |
| `EXTERNAL_TABLE_FILE_REGISTRATION_HISTORY` | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/functions/external_table_registration_history) |
| `SYSTEM$EXTERNAL_TABLE_PIPE_STATUS` | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/functions/system_external_table_pipe_status) |
| Auto-refresh for external tables on S3 | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/tables-external-s3) |
| Persisted query results (result cache) | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/querying-persisted-results) |
| Warehouse cache optimization | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/performance-query-warehouse-cache) |
| Caching in Snowflake (community article) | [Snowflake Community](https://community.snowflake.com/s/article/Caching-in-the-Snowflake-Cloud-Data-Platform) |
| Apache Iceberg tables in Snowflake | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/tables-iceberg) |
