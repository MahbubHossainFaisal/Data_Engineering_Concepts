# COPY Command Parameters — TRUNCATECOLUMNS, ENFORCE_LENGTH, FORCE & PURGE

## What Is This About?

The `COPY INTO` command has several options that control what happens when data doesn't fit perfectly, when you try to load the same file twice, and what happens to files after they're loaded. These four parameters come up constantly in real-world pipelines:

- **TRUNCATECOLUMNS** — Should Snowflake silently shorten values that are too long for the target column?
- **ENFORCE_LENGTH** — Should Snowflake reject rows where values don't fit the target column?
- **FORCE** — Should Snowflake reload a file it has already loaded before?
- **PURGE** — Should Snowflake delete the source file after a successful load?

Understanding these prevents duplicate data, silent data loss, and unexpected errors.

---

## Table of Contents

1. [TRUNCATECOLUMNS — Cut Values to Fit](#1-truncatecolumns--cut-values-to-fit)
2. [ENFORCE_LENGTH — Reject Values That Don't Fit](#2-enforce_length--reject-values-that-dont-fit)
3. [How TRUNCATECOLUMNS and ENFORCE_LENGTH Interact](#3-how-truncatecolumns-and-enforce_length-interact)
4. [FORCE — Reload Already-Loaded Files](#4-force--reload-already-loaded-files)
5. [PURGE — Delete Files After Loading](#5-purge--delete-files-after-loading)
6. [Quick Reference Table](#6-quick-reference-table)
7. [Common Questions & Answers](#7-common-questions--answers)

---

## 1. TRUNCATECOLUMNS — Cut Values to Fit

### The Problem

Your table has a column defined as `VARCHAR(10)`, but some values in the source file are longer than 10 characters. By default, Snowflake rejects those rows — the load fails for them.

### What TRUNCATECOLUMNS Does

When set to `TRUE`, Snowflake **silently cuts** the value to fit the column width instead of rejecting the row. The extra characters are simply dropped.

### Example

Your table:

```sql
CREATE OR REPLACE TABLE customers (
  customer_id INT,
  name        VARCHAR(10)
);
```

Your CSV file:

```
1,Jonathan
2,Alex
3,Christopher
```

`Christopher` is 11 characters — it doesn't fit in a `VARCHAR(10)` column.

**Without TRUNCATECOLUMNS (default behavior):**

```sql
COPY INTO customers
FROM @my_s3_stage/customers.csv
FILE_FORMAT = (TYPE = CSV);
```

The row with `Christopher` is rejected. The other two rows load fine.

**With TRUNCATECOLUMNS = TRUE:**

```sql
COPY INTO customers
FROM @my_s3_stage/customers.csv
FILE_FORMAT = (TYPE = CSV)
TRUNCATECOLUMNS = TRUE;
```

`Christopher` becomes `Christophe` (first 10 characters). All three rows load successfully — but you've silently lost a character.

> **Default:** `TRUNCATECOLUMNS = FALSE` (rows with oversized values are rejected)

---

## 2. ENFORCE_LENGTH — Reject Values That Don't Fit

### What ENFORCE_LENGTH Does

When set to `TRUE`, Snowflake **strictly rejects** any value that exceeds the target column's length. This is the default behavior.

When set to `FALSE`, Snowflake relaxes the length check and allows truncation to happen (if `TRUNCATECOLUMNS = TRUE`).

### Why This Exists

`ENFORCE_LENGTH` acts as a **safety guard**. Even if someone sets `TRUNCATECOLUMNS = TRUE`, `ENFORCE_LENGTH = TRUE` will override it and still reject oversized values. This prevents accidental silent data loss.

> **Default:** `ENFORCE_LENGTH = TRUE` (rows with oversized values are rejected)

---

## 3. How TRUNCATECOLUMNS and ENFORCE_LENGTH Interact

This is the most confusing part, so let's make it crystal clear with every combination:

| TRUNCATECOLUMNS | ENFORCE_LENGTH | What Happens to `Christopher` (11 chars) in a `VARCHAR(10)` |
|:-:|:-:|---|
| `FALSE` (default) | `TRUE` (default) | Rejected — value too long, no truncation allowed |
| `TRUE` | `FALSE` | Accepted as `Christophe` — truncated to fit |
| `TRUE` | `TRUE` | **Rejected** — ENFORCE_LENGTH overrides TRUNCATECOLUMNS |
| `FALSE` | `FALSE` | Accepted as `Christophe` — length check relaxed, truncation happens |

**The key rule:** When both are set to `TRUE`, **ENFORCE_LENGTH wins**. Think of it as:

- `TRUNCATECOLUMNS` is the lenient approach: "just cut it and keep the row."
- `ENFORCE_LENGTH` is the strict approach: "doesn't fit? reject it."
- When both are present, the strict approach takes priority.

**Practical recommendation:** To actually truncate values, set `TRUNCATECOLUMNS = TRUE` **and** `ENFORCE_LENGTH = FALSE`:

```sql
COPY INTO customers
FROM @my_s3_stage/customers.csv
FILE_FORMAT = (TYPE = CSV)
TRUNCATECOLUMNS = TRUE
ENFORCE_LENGTH  = FALSE;
```

---

## 4. FORCE — Reload Already-Loaded Files

### The Problem

Snowflake keeps a **load history** for 64 days. It tracks which files have been loaded into which tables. If you try to load the same file again, Snowflake silently skips it — it assumes you don't want duplicates.

This is usually a good thing. But sometimes you *do* want to reload a file (for testing, backfills, or after fixing an issue).

### What FORCE Does

`FORCE = TRUE` tells Snowflake: "Load this file again, even if you already loaded it before."

### Example

File `sales_20250912.csv` has 100 rows.

**First load:**

```sql
COPY INTO sales_table
FROM @my_s3_stage/sales/
FILE_FORMAT = (TYPE = CSV);
```

100 rows loaded successfully.

**Second load — without FORCE:**

```sql
COPY INTO sales_table
FROM @my_s3_stage/sales/
FILE_FORMAT = (TYPE = CSV);
```

Snowflake checks its load history, sees the file was already processed, and **skips it**. Zero new rows. No duplicates.

**Second load — with FORCE:**

```sql
COPY INTO sales_table
FROM @my_s3_stage/sales/
FILE_FORMAT = (TYPE = CSV)
FORCE = TRUE;
```

Snowflake reloads the file. Your table now has **200 rows** — 100 originals + 100 duplicates.

### When to Use FORCE

| Situation | Use FORCE? |
|-----------|-----------|
| Testing / debugging a load | Yes — useful for quick iteration |
| Backfilling data after a fix | Yes — but only if you've cleared old data first |
| Regular production pipeline | **No** — creates duplicates |
| Re-processing after a file was corrected | Better to rename the file instead (e.g., `_fixed.csv`) |

> **Default:** `FORCE = FALSE` (already-loaded files are skipped)

> **Warning:** In financial, transactional, or analytical systems, duplicate rows can cause serious downstream errors (double-counted revenue, inflated metrics, etc.). Avoid `FORCE = TRUE` in production unless you have a deduplication strategy in place.

---

## 5. PURGE — Delete Files After Loading

### The Problem

After loading files into Snowflake, the source files still sit in the stage (or S3 bucket). Over time, they pile up, taking space and potentially causing confusion about what's been loaded.

### What PURGE Does

`PURGE = TRUE` tells Snowflake: "After you successfully load a file, delete it from the stage."

### Example

**Without PURGE (default):**

```sql
COPY INTO sales_table
FROM @my_s3_stage/sales/
FILE_FORMAT = (TYPE = CSV);
```

Files load into the table, but the CSV files **remain in the stage**. You'd need to clean them up manually later.

**With PURGE:**

```sql
COPY INTO sales_table
FROM @my_s3_stage/sales/
FILE_FORMAT = (TYPE = CSV)
PURGE = TRUE;
```

After a successful load, Snowflake **deletes the source files** from the stage. They're gone.

### Important Details

- **Only successfully loaded files are purged.** If a file fails (due to errors), it stays in the stage.
- **Works with both internal and external stages.** For external stages (S3, Azure, GCS), Snowflake sends a delete request to the cloud provider — the file is removed from the bucket.
- **Deletion is permanent.** Once purged, you can't re-download or reload the file unless you have another copy somewhere.

### When to Use PURGE

| Situation | Use PURGE? |
|-----------|-----------|
| Stage is a temporary landing zone — load and forget | Yes |
| You need raw files for auditing, debugging, or replaying | **No** — keep files around |
| Shared S3 bucket where other teams use the same files | **No** — you'd delete files they still need |
| Automated pipeline with no need for re-processing | Yes — saves storage cost |

> **Default:** `PURGE = FALSE` (files remain in the stage after loading)

---

## 6. Quick Reference Table

| Parameter | What It Does | Default | Risk If Misused |
|-----------|-------------|---------|-----------------|
| **TRUNCATECOLUMNS** | Silently cuts values to fit the target column width | `FALSE` | Silent data loss — you lose characters without any warning |
| **ENFORCE_LENGTH** | Rejects rows where values exceed the column width | `TRUE` | If set to `FALSE`, oversized values may be silently truncated |
| **FORCE** | Reloads files that were already loaded before | `FALSE` | Creates duplicate rows in the target table |
| **PURGE** | Deletes source files from the stage after successful load | `FALSE` | Permanently removes files — can't reload or audit them later |

---

## 7. Common Questions & Answers

### What's the difference between TRUNCATECOLUMNS and ENFORCE_LENGTH?

`TRUNCATECOLUMNS` says "cut the value to fit." `ENFORCE_LENGTH` says "reject the value if it doesn't fit." They control opposite behaviors. By default, Snowflake rejects oversized values (ENFORCE_LENGTH wins). To actually truncate, you need `TRUNCATECOLUMNS = TRUE` **and** `ENFORCE_LENGTH = FALSE`.

---

### If both TRUNCATECOLUMNS=TRUE and ENFORCE_LENGTH=TRUE are set, which wins?

**ENFORCE_LENGTH wins.** The row is rejected, not truncated. ENFORCE_LENGTH is the strict guard — it overrides the lenient TRUNCATECOLUMNS setting.

---

### What happens if I load the same file twice without FORCE?

Snowflake skips it. It tracks file load history for 64 days. If the file name and checksum match a previously loaded file, Snowflake assumes it's already been processed and does nothing. This prevents accidental duplicates.

---

### What's the risk of FORCE=TRUE in production?

**Duplicate rows.** If the original file's data is already in the table and you force-reload it, every row appears twice. This silently corrupts your data — revenue gets double-counted, user counts inflate, reports become unreliable. Only use FORCE for testing or when you've truncated the table first.

---

### Can PURGE delete files from S3 (external stages)?

**Yes.** When `PURGE = TRUE` is used with an external stage pointing to S3, Azure, or GCS, Snowflake sends a delete request to the cloud provider. The file is removed from the bucket — not just from Snowflake's metadata. Be careful if other teams or systems also use those files.

---

### How does PURGE affect my ability to reprocess data?

Once purged, the file is gone. You can't reload it, debug it, or use it for auditing — unless you have a separate backup. If your pipeline might need to reprocess files (e.g., after a schema change or bug fix), don't use PURGE. Keep files around and clean them up manually or with a lifecycle policy after a retention period.
