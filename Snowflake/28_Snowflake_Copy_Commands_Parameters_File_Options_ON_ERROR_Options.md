# COPY Command Parameters — FILES, PATTERN & ON_ERROR Options

## What Is This About?

The `COPY INTO <table>` command is how you load data from files (in S3, Azure, GCS, or a Snowflake stage) into a Snowflake table. It's the backbone of bulk data loading in Snowflake.

This guide focuses on three categories of options that control **which files get loaded**, **how errors are handled**, and **how to capture and debug rejected rows**:

- **FILES** — Load specific files by name
- **PATTERN** — Load files matching a regex pattern
- **ON_ERROR** — Control what happens when a row can't be loaded

For the other COPY parameters (TRUNCATECOLUMNS, ENFORCE_LENGTH, FORCE, PURGE), see the [companion guide](./28_Snowflake_Copy_Command_Parameters_Truncate_EnforceLength_Force_Purge.md).

---

## Table of Contents

1. [FILES — Load Specific Files by Name](#1-files--load-specific-files-by-name)
2. [PATTERN — Load Files Matching a Regex](#2-pattern--load-files-matching-a-regex)
3. [FILES vs PATTERN — When to Use Which](#3-files-vs-pattern--when-to-use-which)
4. [ON_ERROR — What Happens When Rows Fail](#4-on_error--what-happens-when-rows-fail)
5. [Capturing and Debugging Rejected Rows](#5-capturing-and-debugging-rejected-rows)
6. [Loading Compressed Files](#6-loading-compressed-files)
7. [Duplicate File Protection](#7-duplicate-file-protection)
8. [Quick Reference](#8-quick-reference)
9. [Common Questions & Answers](#9-common-questions--answers)

---

## 1. FILES — Load Specific Files by Name

By default, `COPY INTO` tries to load **all files** in the stage path. But what if you only need one or two specific files?

The `FILES` parameter lets you list the exact file names you want to load.

### Example

Your S3 bucket has:

```
s3://company-data/sales/
  ├── sales_20250901.csv
  ├── sales_20250902.csv
  ├── sales_20250903.csv
  └── sales_20250904.csv
```

To load only September 3rd's file:

```sql
COPY INTO sales_table
FROM @my_s3_stage/sales/
FILES = ('sales_20250903.csv')
FILE_FORMAT = (TYPE = CSV);
```

To load multiple specific files:

```sql
COPY INTO sales_table
FROM @my_s3_stage/sales/
FILES = ('sales_20250901.csv', 'sales_20250902.csv')
FILE_FORMAT = (TYPE = CSV);
```

### Limitation — No Exclusion

`FILES` only supports picking files you **want**. You cannot exclude files — there's no `NOT` or `EXCEPT` syntax. If you need to load "everything except file X," use `PATTERN` instead.

---

## 2. PATTERN — Load Files Matching a Regex

`PATTERN` uses **regular expressions** to select files based on their names. This is much more flexible than `FILES` — you can match date ranges, file extensions, folder structures, or even exclude specific files.

### Basic Examples

Load all CSV files from September 2025:

```sql
COPY INTO sales_table
FROM @my_s3_stage/sales/
PATTERN = '.*202509.*[.]csv'
FILE_FORMAT = (TYPE = CSV);
```

Load files from September 1st through 5th:

```sql
COPY INTO sales_table
FROM @my_s3_stage/sales/
PATTERN = '.*2025090[1-5].*'
FILE_FORMAT = (TYPE = CSV);
```

Load only JSON files:

```sql
COPY INTO events_table
FROM @my_s3_stage/events/
PATTERN = '.*[.]json'
FILE_FORMAT = (TYPE = JSON);
```

### Loading from Date-Partitioned Folders

A common S3 structure looks like this:

```
s3://company-data/logs/
  ├── date=20250910/file1.csv
  ├── date=20250911/file2.csv
  ├── date=20250912/file3.csv
  └── date=20250913/file4.csv
```

To load only the last 3 days (Sept 11–13):

```sql
COPY INTO logs_table
FROM @my_s3_stage/logs/
PATTERN = '.*date=202509(11|12|13)/.*[.]csv'
FILE_FORMAT = (TYPE = CSV);
```

The `(11|12|13)` part is a regex "or" — it matches any of those three values.

### Excluding Files with PATTERN

While `FILES` can't exclude, `PATTERN` can — using a regex negative lookahead. For example, to load everything **except** September 1st:

```sql
COPY INTO sales_table
FROM @my_s3_stage/sales/
PATTERN = '^(?!.*20250901).*[.]csv'
FILE_FORMAT = (TYPE = CSV);
```

This regex means: "Match any CSV file whose name does **not** contain `20250901`."

---

## 3. FILES vs PATTERN — When to Use Which

| | **FILES** | **PATTERN** |
|---|---|---|
| **How it works** | You list exact file names | You write a regex that matches file names |
| **Select specific files** | Yes — explicit list | Yes — via regex |
| **Exclude specific files** | Not supported | Yes — using negative lookahead regex |
| **Date-range loading** | Requires listing every file name | Easy — use regex ranges like `(01\|02\|03)` |
| **Simplicity** | Very simple for 1-2 files | Requires regex knowledge, but much more powerful |
| **Best for** | Loading a known, small set of files | Bulk loading based on naming conventions or date partitions |

**Rule of thumb:** Use `FILES` when you know the exact file names and there are only a few. Use `PATTERN` for anything dynamic — date ranges, file type filtering, or exclusions.

---

## 4. ON_ERROR — What Happens When Rows Fail

Real-world files aren't always clean. You'll encounter wrong data types, missing delimiters, unexpected characters, and malformed JSON. The `ON_ERROR` parameter tells Snowflake what to do when it hits a bad row.

### The Options

| Setting | What Snowflake Does | Analogy |
|---------|---------------------|---------|
| `ABORT_STATEMENT` (default) | Stops the entire load. **Nothing** gets inserted — not even the good rows. | Movers find one broken box and refuse to unload the entire truck. |
| `CONTINUE` | Skips the bad rows and loads everything else. | Movers set the broken boxes aside and unload everything that's fine. |
| `SKIP_FILE` | Skips the **entire file** that has even one bad row. Other files still load. | If any box from a specific pallet is broken, skip the whole pallet. |
| `SKIP_FILE_<n>` | Skips a file if it has more than `n` errors. E.g., `SKIP_FILE_5` skips files with 6+ errors. | Allow up to 5 broken boxes per pallet; if more than that, skip the whole pallet. |
| `SKIP_FILE_<n>%` | Skips a file if the error percentage exceeds `n%`. E.g., `SKIP_FILE_10%` skips files where more than 10% of rows are bad. | If more than 10% of the pallet is damaged, skip it. |

### When to Use Which

| Scenario | Recommended Setting | Why |
|----------|-------------------|-----|
| Financial transactions, regulatory data | `ABORT_STATEMENT` | You need 100% accuracy — partial loads are unacceptable |
| Web logs, clickstream, sensor data | `CONTINUE` | High volume, some bad rows are normal — don't block millions of good rows |
| Daily file drops from external vendors | `SKIP_FILE` or `SKIP_FILE_5` | If a file is badly formatted, skip it entirely and load the rest |

### Example — ABORT (default)

```sql
COPY INTO sales_table
FROM @my_s3_stage/sales/
FILE_FORMAT = (TYPE = CSV)
ON_ERROR = 'ABORT_STATEMENT';
```

If even one row fails, the entire operation stops. Zero rows are inserted.

### Example — CONTINUE

```sql
COPY INTO sales_table
FROM @my_s3_stage/sales/
FILE_FORMAT = (TYPE = CSV)
ON_ERROR = 'CONTINUE';
```

Out of 1,000 rows, if 5 are malformed, Snowflake loads 995 and skips 5. The COPY result tells you how many were loaded and how many errored.

---

## 5. Capturing and Debugging Rejected Rows

When you use `ON_ERROR = 'CONTINUE'`, the bad rows are skipped — but you usually want to know *what* went wrong and *which* rows failed.

### Step 1: Get the Query ID of Your COPY Command

Every `COPY INTO` execution gets a unique query ID. Grab it right after running the COPY:

```sql
SELECT LAST_QUERY_ID();
```

You can also search your recent query history:

```sql
SELECT *
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_USER(RESULT_LIMIT => 5));
```

### Step 2: View the Rejected Rows

Use the `VALIDATE` function with the query ID from the COPY command:

```sql
SELECT *
FROM TABLE(VALIDATE(
  sales_table,
  JOB_ID => '_last'
));
```

Replace `'_last'` with the actual query ID if needed. This returns details about every rejected row:

| Column | What It Shows |
|--------|---------------|
| Error message | Why the row was rejected (e.g., "Numeric value 'abc' is not recognized") |
| File name | Which file the bad row came from |
| Line number | Which line in the file |
| Column details | Which column caused the error |
| Row content | The raw content of the failed row |

### Step 3: Save Rejected Rows to a Table for Later Analysis

If you want to keep the error details for debugging or sharing with the upstream team:

```sql
CREATE OR REPLACE TABLE rejected_sales AS
SELECT *
FROM TABLE(VALIDATE(
  sales_table,
  JOB_ID => '_last'
));
```

Now you have a permanent table of everything that went wrong — you can query it, share it, or build alerts around it.

### Checking Load History

For a broader view of recent load operations:

```sql
SELECT *
FROM INFORMATION_SCHEMA.LOAD_HISTORY
ORDER BY LAST_LOAD_TIME DESC;
```

This shows which files were loaded, how many rows succeeded, and how many failed — across all recent COPY operations on the table.

---

## 6. Loading Compressed Files

Snowflake can automatically decompress files during loading. You don't need to unzip anything beforehand.

```sql
COPY INTO sales_table
FROM @my_s3_stage/sales/
FILE_FORMAT = (TYPE = CSV COMPRESSION = GZIP);
```

### Supported Compression Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| `AUTO` | (any) | Snowflake auto-detects the compression — the safest default |
| `GZIP` | `.gz` | Most common for CSV files |
| `BZ2` | `.bz2` | Higher compression ratio, slower |
| `BROTLI` | `.br` | Good balance of speed and compression |
| `ZSTD` | `.zst` | Fast compression, increasingly popular |
| `DEFLATE` | `.deflate` | Standard deflate algorithm |
| `RAW_DEFLATE` | `.raw_deflate` | Deflate without headers |

**Tip:** Use `COMPRESSION = AUTO` to let Snowflake figure it out automatically. It works in most cases.

---

## 7. Duplicate File Protection

By default, Snowflake tracks which files have been loaded into each table (for 64 days). If you try to load the same file again, Snowflake **skips it silently** — no error, no duplicates.

This is usually what you want. But if you need to reload a file (for testing or after fixing it), you have two options:

1. **Rename the file** (e.g., `sales_20250903_v2.csv`) — Snowflake treats it as a new file.
2. **Use `FORCE = TRUE`** — Snowflake reloads the file regardless of history. But this creates duplicates if the old data is still in the table.

See the [FORCE parameter guide](./28_Snowflake_Copy_Command_Parameters_Truncate_EnforceLength_Force_Purge.md#4-force--reload-already-loaded-files) for details.

---

## 8. Quick Reference

| Parameter | What It Does | Default |
|-----------|-------------|---------|
| `FILES` | Load specific files by exact name | Load all files in the path |
| `PATTERN` | Load files matching a regex pattern | Load all files in the path |
| `ON_ERROR = ABORT_STATEMENT` | Stop everything on the first error | This is the default |
| `ON_ERROR = CONTINUE` | Skip bad rows, load everything else | — |
| `ON_ERROR = SKIP_FILE` | Skip the entire file if it has any error | — |
| `ON_ERROR = SKIP_FILE_<n>` | Skip the file if it has more than `n` errors | — |
| `ON_ERROR = SKIP_FILE_<n>%` | Skip the file if error rate exceeds `n%` | — |
| `COMPRESSION` | Decompress files during load (GZIP, BZ2, ZSTD, etc.) | `AUTO` |
| `VALIDATE(table, JOB_ID)` | View rejected rows from a COPY job | — |

---

## 9. Common Questions & Answers

### What's the difference between FILES and PATTERN?

`FILES` takes an explicit list of file names — you name exactly which files to load. `PATTERN` takes a regex and loads all files whose names match. Use `FILES` for a small, known set of files. Use `PATTERN` for date ranges, extensions, folder structures, or exclusions.

---

### Why can't I exclude files with FILES?

`FILES` only supports inclusion — listing the files you want. There's no `NOT` or `EXCEPT` syntax. For exclusion, use `PATTERN` with a negative lookahead regex like `'^(?!.*20250901).*[.]csv'`.

---

### When should I use ABORT vs CONTINUE?

Use `ABORT_STATEMENT` when data correctness is non-negotiable (financial data, regulatory feeds) — you'd rather load nothing than load partial data. Use `CONTINUE` when the volume is high and some bad rows are expected (logs, events, clickstream) — don't let a few bad rows block millions of good ones.

---

### How do I see which rows were rejected?

After a `COPY INTO` with `ON_ERROR = 'CONTINUE'`, run:

```sql
SELECT * FROM TABLE(VALIDATE(sales_table, JOB_ID => '_last'));
```

This returns the file name, line number, error message, and raw content of every rejected row. Save it to a table if you want to keep it for analysis.

---

### How do I load only the last 3 days from a date-partitioned folder?

Use `PATTERN` with a regex that matches the dates you want:

```sql
PATTERN = '.*date=202509(11|12|13)/.*[.]csv'
```

This loads files from the `date=20250911/`, `date=20250912/`, and `date=20250913/` folders.

---

### How does Snowflake handle loading the same file twice?

By default, Snowflake tracks load history for 64 days and **skips** files it has already loaded. This prevents accidental duplicates. To force a reload, use `FORCE = TRUE` (but be aware this creates duplicates if the old data is still in the table).

---

### Can Snowflake load compressed files directly?

Yes. Set `COMPRESSION` in the file format (or use `AUTO` to let Snowflake detect it). Supported formats include GZIP, BZ2, BROTLI, ZSTD, DEFLATE, and RAW_DEFLATE. No need to decompress files before loading.
