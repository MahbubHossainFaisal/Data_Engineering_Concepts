# Files Unloading to S3 (Snowflake → S3)

> **Scenario (SkyCart):** You're the data engineering lead for "SkyCart," an e-commerce company. Every morning by 06:00, Marketing expects a fresh, partitioned export of yesterday's orders in S3 for downstream tools (Athena, Glue jobs, a Python notebook). Your job: make the unload **correct, repeatable, and easy to audit** — and be able to prove it.

---

## Table of Contents

1. [The 3 Core Ideas (Fundamentals)](#1-the-3-core-ideas-fundamentals)
2. [One-Time Setup (The Secure Way)](#2-one-time-setup-the-secure-way)
3. [The Unload — Step by Step](#3-the-unload--step-by-step)
4. [Validation — Prove Nothing Is Missing](#4-validation--prove-nothing-is-missing)
5. [Formats, Encryption, Performance & Costs](#5-formats-encryption-performance--costs)
6. [Common Pitfalls & How to Fix Them](#6-common-pitfalls--how-to-fix-them)
7. [Reusable "Daily Export" Pattern](#7-reusable-daily-export-pattern)
8. [Full Walk-Through (Copy/Paste Block)](#8-full-walk-through-copypaste-block)
9. [Validation Checklist](#9-validation-checklist)
10. [Extra Patterns for the Real World](#10-extra-patterns-for-the-real-world)
11. [Self-Test Questions](#11-self-test-questions)
12. [References](#12-references)

---

## 1. The 3 Core Ideas (Fundamentals)

| # | Concept | What It Means |
|---|---------|---------------|
| **1** | **UNLOAD = `COPY INTO <external location>`** | Run `COPY INTO '<s3://...>' FROM (<query>)` or `COPY INTO @my_external_stage/... FROM (<query>)`. Use a named external stage (recommended) or a direct S3 URL with a storage integration. Options control file format (CSV/Parquet/JSON), partitioning, compression, naming, and overwrite behavior. |
| **2** | **Consistency & Repeatability** | Every `SELECT` reads a **single snapshot** as of statement start. To make validation bullet-proof, capture a timestamp and use **Time Travel `AT (TIMESTAMP => ...)`** in both your `COUNT(*)` validation and unload query so they read the **same snapshot**. |
| **3** | **Validation Is Not Optional** | You must prove: row count in S3 == row count from Snowflake at the same snapshot; file set in S3 is what you expect; data shape matches (columns, types, null handling, delimiters). |

> See: [COPY INTO \<location\> — Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/sql/copy-into-location)

---

## 2. One-Time Setup (The Secure Way)

### 2a. Create an AWS IAM Role & Storage Integration

Let Snowflake **assume** an IAM role to write into your bucket/prefix.

```sql
USE ROLE ACCOUNTADMIN;

-- 1) Create storage integration (replace ARNs and bucket path)
CREATE OR REPLACE STORAGE INTEGRATION SKY_OUT_INT
  TYPE                      = EXTERNAL_STAGE
  STORAGE_PROVIDER          = S3
  ENABLED                   = TRUE
  STORAGE_AWS_ROLE_ARN      = 'arn:aws:iam::123456789012:role/skycart-snowflake-writer'
  STORAGE_ALLOWED_LOCATIONS = ('s3://skycart-analytics/exports/');

-- 2) Get values to finish AWS trust (external id, user ARN)
DESCRIBE INTEGRATION SKY_OUT_INT;
```

**In AWS IAM:** Create/update the role trust policy to allow Snowflake's **AWS IAM user ARN** with the **external ID** returned by `DESCRIBE INTEGRATION`, and attach an S3 policy allowing `s3:PutObject`, `s3:ListBucket`, (optionally `s3:DeleteObject` if you'll use `OVERWRITE=TRUE`) on the allowed prefix.

> See: [Storage Integration — Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/sql/create-storage-integration)

---

### 2b. Create a Named External Stage (Recommended)

Named stages centralize credentials and let you query/list files easily later.

```sql
USE ROLE SYSADMIN;
USE DATABASE PROD;
USE SCHEMA SHARED;

CREATE OR REPLACE STAGE SKY_S3_STAGE
  URL                 = 's3://skycart-analytics/exports/'
  STORAGE_INTEGRATION = SKY_OUT_INT;
```

> See: [CREATE STAGE — Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/sql/create-stage)

---

### 2c. Define Reusable File Formats

**Parquet** — great for downstream analytics:

```sql
CREATE OR REPLACE FILE FORMAT FF_PARQUET
  TYPE = PARQUET;
```

**CSV** — for tools that need delimited text:

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

> You can override these inline on the COPY command if needed.
> See: [COPY INTO \<location\> — Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/sql/copy-into-location)

---

## 3. The Unload — Step by Step

**Goal:** Export yesterday's completed orders from `PROD.SALES.ORDERS` into S3, **partitioned by `order_date`** (one folder per day), in **Parquet**, and make it **idempotent**.

### 3a. Capture a Consistent Snapshot Time

```sql
USE ROLE ANALYST;
USE WAREHOUSE ETL_XL;
USE DATABASE PROD;
USE SCHEMA SALES;

SET SNAP_TS = CURRENT_TIMESTAMP();
```

---

### 3b. (Optional) Preview — Validate the Query Before Exporting

```sql
SELECT * FROM (
  SELECT order_id, customer_id, total_amount, order_date, updated_at
  FROM ORDERS
  WHERE status = 'COMPLETED'
    AND order_date = DATEADD(day, -1, CURRENT_DATE())
  QUALIFY ROW_NUMBER() OVER (ORDER BY order_id) <= 5
)
AT (TIMESTAMP => $SNAP_TS);
```

> Snowflake also supports `VALIDATION_MODE = RETURN_ROWS` on `COPY INTO <location>` to run the query without actually unloading.

---

### 3c. Count Rows at the Same Snapshot (For Later Comparison)

```sql
SET ROWS_EXPECTED = (
  SELECT COUNT(*) FROM ORDERS
  AT (TIMESTAMP => $SNAP_TS)
  WHERE status = 'COMPLETED'
    AND order_date = DATEADD(day, -1, CURRENT_DATE())
);

SELECT $ROWS_EXPECTED AS rows_expected;
```

---

### 3d. Unload to S3 — Parquet, Partitioned

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

**Key options explained:**

| Option | Purpose |
|--------|---------|
| `PARTITION BY` | Creates folder layers like `.../partition_0=2025-08-29/...` — ideal for downstream engines |
| `INCLUDE_QUERY_ID` | Stamps filenames with the query ID for traceability and deduplication |
| `DETAILED_OUTPUT` | Returns one row per file with `file_path`, file size, and `rows_unloaded` |

> **Important:** `PARTITION BY` **cannot** be combined with `SINGLE=TRUE` or `OVERWRITE=TRUE`. If you need to overwrite, target a new dated prefix each day (e.g., `.../dt=2025-08-29/`) and manage retention with lifecycle rules.

---

### 3e. (Alternative) Unload to S3 in CSV with Headers

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
MAX_FILE_SIZE       = 50000000       -- ~50 MB target chunks
INCLUDE_QUERY_ID    = TRUE
DETAILED_OUTPUT     = TRUE;
```

> **CSV gotchas:** Think through **NULL vs empty string**, quotes and escapes. Set `NULL_IF` and `FIELD_OPTIONALLY_ENCLOSED_BY` consciously to avoid downstream surprises.

---

## 4. Validation — Prove Nothing Is Missing

### 4A. Use the COPY Result Set as Your First Audit

`COPY INTO <location>` returns a result set you can immediately capture:

```sql
CREATE OR REPLACE TEMPORARY TABLE TMP_UNLOAD_AUDIT AS
SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

SELECT SUM(rows_unloaded) AS rows_in_files FROM TMP_UNLOAD_AUDIT;
```

**Compare totals:**

```sql
SELECT $ROWS_EXPECTED AS rows_expected;
SELECT SUM(rows_unloaded) AS rows_in_files FROM TMP_UNLOAD_AUDIT;
```

These **must match exactly**. If not, investigate (see [Common Pitfalls](#6-common-pitfalls--how-to-fix-them) below).

---

### 4B. List and Verify File/Partition Structure

```sql
LIST @PROD.SHARED.SKY_S3_STAGE/orders/parquet/;
```

You can create a quick directory report (names, sizes, timestamps) and diff it over time.

---

### 4C. Read Back from S3 and Recount in Snowflake

Query staged files directly — no table needed:

```sql
-- Recount Parquet files directly in S3
SELECT COUNT(*) AS rows_read_back
FROM @PROD.SHARED.SKY_S3_STAGE/orders/parquet/
  (FILE_FORMAT => 'FF_PARQUET');

-- Recount CSV files directly in S3
SELECT COUNT(*) AS rows_read_back
FROM @PROD.SHARED.SKY_S3_STAGE/orders/csv/
  (FILE_FORMAT => 'FF_CSV');
```

This is the cleanest way to prove "what's in S3 equals the source snapshot."

> See: [Querying Data in Staged Files — Snowflake Documentation](https://docs.snowflake.com/en/user-guide/querying-stage)

---

### 4D. Optional Content Checks (Spot Checks)

Light spot checks to catch delimiter/encoding issues:

```sql
SELECT
  TO_VARCHAR(METADATA$FILENAME) AS file,
  COUNT(*)                      AS cnt,
  MIN($3)                       AS min_amt,
  MAX($3)                       AS max_amt
FROM @PROD.SHARED.SKY_S3_STAGE/orders/csv/ (FILE_FORMAT => 'FF_CSV')
GROUP BY 1
ORDER BY 1
LIMIT 20;
```

> `METADATA$FILENAME` and friends are accessible when querying staged files.

---

## 5. Formats, Encryption, Performance & Costs

### Choosing a File Format

| Format | Pros | Cons |
|--------|------|------|
| **Parquet** (Snappy compression) | Smaller files, typed columns, faster scans in Athena/Glue/Spark | Less human-readable |
| **CSV** | Human-friendly, ubiquitous | Bigger files, needs careful null/quote handling |
| **JSON / Avro / ORC** | Also supported by Snowflake for unload | Less common for this use case |

---

### Partitioning Strategy

Use `PARTITION BY` on fields you'll filter downstream (e.g., `order_date`, `region`). It creates hierarchical folders and can drastically cut costs in engines like Athena.

> **Remember:** Not compatible with `SINGLE=TRUE` or `OVERWRITE=TRUE`.

---

### Encryption

If your bucket uses **SSE-S3** by default, you're fine. For **KMS**:

```sql
COPY INTO @SKY_S3_STAGE/secure/orders/
FROM ( SELECT ... )
FILE_FORMAT = (FORMAT_NAME = FF_PARQUET)
ENCRYPTION  = (
  TYPE       = 'AWS_SSE_KMS',
  KMS_KEY_ID = 'arn:aws:kms:us-east-1:123456789012:key/abcd-...'
);
```

| Encryption Type | When to Use |
|-----------------|-------------|
| `AWS_SSE_S3` | Bucket default encryption is sufficient |
| `AWS_SSE_KMS` | Compliance requires specific KMS key control |
| `NONE` | Encryption handled elsewhere or not required |

---

### Performance Tips

- **Don't `ORDER BY`** in unload queries unless needed — it forces global sort and slows things down.
- Tune **`MAX_FILE_SIZE`** to produce **50–250 MB** compressed files for balanced parallelism.
- For huge exports, prefer **Parquet** and **partitioning**.
- Size the warehouse appropriately (`ETL_XL` vs `ETL_2XL`) and consider multi-cluster if concurrency is needed.

---

### Costs

| Cost Type | Details |
|-----------|---------|
| **Warehouse time** | You pay for compute during the unload |
| **Cloud egress** | Applies if Snowflake account region ≠ S3 bucket region — keep them co-located |
| **S3 storage & requests** | Standard AWS charges apply |

---

## 6. Common Pitfalls & How to Fix Them

| # | Problem | Cause & Fix |
|---|---------|-------------|
| **1** | **Counts don't match** | You didn't read the same snapshot — ensure both `COUNT(*)` and `COPY` use `AT (TIMESTAMP => $SNAP_TS)`. Also verify filters are identical. For CSV, revisit `FIELD_OPTIONALLY_ENCLOSED_BY`, `ESCAPE_UNENCLOSED_FIELD`, `RECORD_DELIMITER`. |
| **2** | **"AccessDenied" or nothing lands in S3** | Storage integration lacks permission to the exact prefix, or the bucket/trust policy isn't set with Snowflake's **IAM user ARN** + **external ID**. Recheck `DESCRIBE INTEGRATION` and bucket/role policies. |
| **3** | **`PARTITION BY` with `OVERWRITE`/`SINGLE` errors** | By design — use a new dated prefix instead of overwrite; avoid `SINGLE=TRUE` when partitioning. |
| **4** | **Parquet + timezone types** | `TIMESTAMP_TZ` / `TIMESTAMP_LTZ` can error when unloading to Parquet. Cast to `TIMESTAMP_NTZ` first (best practice). |
| **5** | **Zero rows exported** | Snowflake won't create a data file if the query returns 0 rows. If downstream expects the path to exist, create a small marker file separately or design consumers to tolerate missing partitions. |

---

## 7. Reusable "Daily Export" Pattern

A tidy, automatable pattern:

1. **Wrap** the steps into a **stored procedure** (capture snapshot → count → unload → verify → write audit row).
2. **Schedule** with a **TASK** at 05:45 so files are ready by 06:00.
3. **Use a date-stamped prefix:** `.../orders/dt=YYYY-MM-DD/` to avoid overwrites and make lineage clean.

---

## 8. Full Walk-Through (Copy/Paste Block)

```sql
-- ===== 0) Context =====
USE ROLE SYSADMIN;
USE WAREHOUSE ETL_XL;
USE DATABASE PROD;
USE SCHEMA SALES;

-- ===== 1) Snapshot & expected count =====
SET SNAP_TS = CURRENT_TIMESTAMP();

SET ROWS_EXPECTED = (
  SELECT COUNT(*) FROM ORDERS
  AT (TIMESTAMP => $SNAP_TS)
  WHERE status = 'COMPLETED'
    AND order_date = DATEADD(day, -1, CURRENT_DATE())
);

-- ===== 2) Unload to S3 (Parquet, partitioned, auditable names) =====
COPY INTO @PROD.SHARED.SKY_S3_STAGE/orders/parquet/
FROM (
  SELECT
    order_id,
    customer_id,
    total_amount::NUMBER(12,2)      AS total_amount,
    order_date,
    updated_at::TIMESTAMP_NTZ       AS updated_at
  FROM ORDERS AT (TIMESTAMP => $SNAP_TS)
  WHERE status = 'COMPLETED'
    AND order_date = DATEADD(day, -1, CURRENT_DATE())
)
FILE_FORMAT      = (FORMAT_NAME = FF_PARQUET)
PARTITION BY     (TO_VARCHAR(order_date, 'YYYY-MM-DD'))
INCLUDE_QUERY_ID = TRUE
DETAILED_OUTPUT  = TRUE;

-- ===== 3) Audit the COPY output =====
CREATE OR REPLACE TEMPORARY TABLE TMP_UNLOAD_AUDIT AS
SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

SELECT $ROWS_EXPECTED                AS rows_expected;
SELECT SUM(rows_unloaded) AS rows_in_files FROM TMP_UNLOAD_AUDIT;

-- ===== 4) Read back from S3 and compare =====
SELECT COUNT(*) AS rows_read_back
FROM @PROD.SHARED.SKY_S3_STAGE/orders/parquet/
  (FILE_FORMAT => 'FF_PARQUET');

-- ===== 5) List files (eyeball partitions & sizes) =====
LIST @PROD.SHARED.SKY_S3_STAGE/orders/parquet/;
```

> Easy tweaks: add `ENCRYPTION = (TYPE='AWS_SSE_KMS', KMS_KEY_ID='...')`, or switch to CSV with `FILE_FORMAT = FF_CSV`.

---

## 9. Validation Checklist

Use this as a print-worthy reference for every unload:

- [ ] **Same snapshot** used in both count and unload (`AT (TIMESTAMP => $SNAP_TS)`)
- [ ] `COPY` **result set captured**; sum of `rows_unloaded` == expected count
- [ ] **Read-back count** from S3 via stage == expected count
- [ ] **Partitions present** as designed (e.g., `partition_0=YYYY-MM-DD/`)
- [ ] **File sizes reasonable** (not tons of tiny files, not a single huge file)
- [ ] **CSV:** nulls/quotes/escapes validated | **Parquet:** timestamp types cast as needed
- [ ] **Encryption** validated (KMS key ID if required)

---

## 10. Extra Patterns for the Real World

| Pattern | Details |
|---------|---------|
| **Idempotency** | Use `INCLUDE_QUERY_ID=TRUE` to avoid accidental overwrites, or emit into a dated prefix and treat each run as immutable output |
| **Schema Evolution** | Prefer Parquet; CSV + headers is fragile for evolving schemas |
| **Downstream Friendliness** | Pick partition columns your consumers filter by; avoid too many tiny files |
| **Auditing** | Insert a row into an `EXPORT_AUDIT` table with `query_id`, `rows_expected`, `rows_in_files`, `prefix`, and `verification_status` |

---

## 11. Self-Test Questions

1. What are the pros/cons of unloading to a **named external stage** vs a direct **S3 URL** with `STORAGE_INTEGRATION`?

2. How does Snowflake guarantee **read consistency**, and how do you use `AT (TIMESTAMP => ...)` for validation across multiple statements?

3. Why use **`INCLUDE_QUERY_ID`** and **`DETAILED_OUTPUT`** in `COPY INTO <location>`? What do you get back and how do you use it?

4. Explain why **`PARTITION BY`** can't be combined with **`SINGLE=TRUE`** or **`OVERWRITE=TRUE`**, and how you design around it.

5. When would you pick **Parquet** over **CSV**, and what **CSV file format** options prevent data corruption (nulls, quotes, newlines)?

6. How do you **read back** your S3 files in Snowflake to validate counts and content without loading into a table? Show the exact SQL.

7. What permissions/policies are required for a **storage integration** to write to S3, and how do **external ID** and **IAM trust** fit in?

8. What are the **encryption** options for unloading to S3 and when do you need `AWS_SSE_KMS`? Show the syntax.

9. What happens if your query returns **zero rows** and your downstream expects a file? How do you design for this?

---

## 12. References

| Topic | Link |
|-------|------|
| `COPY INTO <location>` (all unload options) | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/copy-into-location) |
| `CREATE STORAGE INTEGRATION` (S3 setup) | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/create-storage-integration) |
| `CREATE STAGE` (named external stages) | [Snowflake Docs](https://docs.snowflake.com/en/sql-reference/sql/create-stage) |
| Querying data in staged files (read-back, metadata) | [Snowflake Docs](https://docs.snowflake.com/en/user-guide/querying-stage) |
