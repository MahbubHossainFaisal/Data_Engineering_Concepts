# Snowflake Features — Clone and Swap

## What Is This About?

Cloning and Swapping are two complementary Snowflake features that leverage immutable micro-partitions and metadata manipulation to achieve powerful, zero-downtime operations on tables, schemas, and databases.

**Cloning** creates instant, independent copies of objects without duplicating physical data — perfect for backups, testing, and sandboxing. **Swapping** atomically exchanges the metadata references of two tables, enabling zero-downtime deployments and rollbacks in production environments.

Together, these features exemplify Snowflake's philosophy: avoid expensive physical operations by manipulating metadata intelligently. Clone a 500 GB table in milliseconds. Refresh your production table while queries continue uninterrupted.

---

## Table of Contents

1. [Clone Feature — Overview and Internals](#1-clone-feature--overview-and-internals)
2. [How Cloning Works — Zero-Copy Mechanism](#2-how-cloning-works--zero-copy-mechanism)
3. [Copy-on-Write Behavior](#3-copy-on-write-behavior)
4. [Clone Use Cases and Examples](#4-clone-use-cases-and-examples)
5. [Swap Feature — Overview and Syntax](#5-swap-feature--overview-and-syntax)
6. [How Swap Works — Metadata Swapping](#6-how-swap-works--metadata-swapping)
7. [Swap Use Cases and Examples](#7-swap-use-cases-and-examples)
8. [Clone vs Swap Comparison](#8-clone-vs-swap-comparison)
9. [Best Practices](#9-best-practices)
10. [Gotchas and Limits](#10-gotchas-and-limits)
11. [Common Questions & Answers](#11-common-questions--answers)

---

## 1. Clone Feature — Overview and Internals

### What Is Cloning?

Imagine you're a data engineer at a healthcare analytics company managing a `PATIENT_FACT` table containing patient demographics and medical histories. This table is 500 GB and serves critical production dashboards.

You need to:
- Create a sandbox version for testing ETL transformations
- Back up the table before applying risky logic
- Create a dev environment for your team to experiment safely

A naive approach would be:
```sql
CREATE TABLE PATIENT_FACT_BACKUP AS SELECT * FROM PATIENT_FACT;
```

**The problem:** This physically copies ALL 500 GB of data to storage, doubling your storage costs and taking minutes or hours depending on the size.

**The solution:** Snowflake's **Zero-Copy Cloning**.

> Zero-Copy Cloning creates an instant, fully independent copy of an object (table, schema, or database) **without physically copying any data**. The clone shares the same underlying data blocks as the original until either is modified.

```sql
CREATE TABLE PATIENT_FACT_BACKUP CLONE PATIENT_FACT;
```

This completes in **milliseconds**, regardless of table size.

---

## 2. How Cloning Works — Zero-Copy Mechanism

### Understanding Micro-Partitions and Metadata

Snowflake's architecture consists of three layers:

1. **Storage Layer (S3, Azure Blob, GCP)**: All data is stored as immutable micro-partitions (typically 50–500 MB compressed each). These files can never be modified in-place.

2. **Metadata Layer (Cloud Services)**: Each table maintains metadata that maps logical columns and structure to physical micro-partition files. This metadata is versioned — every DML/DDL operation creates a new metadata snapshot.

3. **Compute Layer (Virtual Warehouse)**: Virtual warehouses read data by referencing micro-partitions via metadata.

### The Cloning Magic

When you clone a table:

```sql
CREATE TABLE PATIENT_FACT_CLONE CLONE PATIENT_FACT;
```

Snowflake does **not** copy files from S3/Blob. Instead:

1. It reads the *metadata* of `PATIENT_FACT` (which micro-partitions exist, their structure, constraints, etc.)
2. It creates a *new* metadata entry for `PATIENT_FACT_CLONE` pointing to the **same micro-partition files**

Result:

| Component              | PATIENT_FACT      | PATIENT_FACT_CLONE |
| ---------------------- | ----------------- | ------------------ |
| Metadata               | ✓ Separate        | ✓ Separate         |
| Underlying Data (S3)   | Micro-partitions  | Same files (shared)|

Both tables are independent from a **logical perspective** but share physical storage initially.

### Key Insight

Since object storage files are immutable, Snowflake can safely share them. No modification to the original affects the clone, and vice versa — **until changes occur**.

---

## 3. Copy-on-Write Behavior

### How Independence Works After Cloning

This is the critical piece: How can both tables be independent if they share data?

**Answer: Copy-on-Write (CoW)**

When either the source table or the clone undergoes a DML operation (INSERT, UPDATE, DELETE), Snowflake:

1. **Does NOT modify the shared micro-partition files** (they're immutable anyway)
2. **Creates new micro-partitions** for the modified table containing only the changed data
3. Updates that table's metadata to reference the new micro-partitions
4. The other table's metadata remains unchanged

### Real-World Example

Starting state:
```sql
CREATE TABLE SALES AS
SELECT 1 AS ID, 'Pen' AS PRODUCT, 10 AS PRICE
UNION ALL
SELECT 2, 'Book', 20;

CREATE TABLE SALES_CLONE CLONE SALES;
```

At this point, both tables share micro-partitions:

| Table        | Metadata Points To       | Data Visible               |
| ------------ | ------------------------ | -------------------------- |
| SALES        | MP1 (ID 1,2)            | ID=1 (Pen, 10), ID=2 (Book, 20) |
| SALES_CLONE  | MP1 (ID 1,2)            | ID=1 (Pen, 10), ID=2 (Book, 20) |

Now, delete from the original:
```sql
DELETE FROM SALES WHERE ID = 1;
```

What happens internally:

1. Snowflake creates a **new micro-partition** for SALES containing only ID=2
2. SALES's metadata now points to MP2 (new micro-partition)
3. SALES_CLONE's metadata still points to MP1 (unchanged)

Current state:

| Table        | Metadata Points To | Data Visible                   |
| ------------ | ------------------ | ------------------------------ |
| SALES        | MP2 (new)          | ID=2 (Book, 20)               |
| SALES_CLONE  | MP1 (original)     | ID=1 (Pen, 10), ID=2 (Book, 20) |

**The result:** Both tables are now **completely independent**, even though the clone operation was zero-copy.

---

## 4. Clone Use Cases and Examples

### Use Case 1: Backup Before Risky Operations

```sql
-- Before running a complex transformation
CREATE TABLE ORDERS_BACKUP CLONE ORDERS;

-- Now perform risky operations
UPDATE ORDERS SET STATUS = 'VALIDATED' WHERE quality_score > 0.95;
DELETE FROM ORDERS WHERE order_date < '2020-01-01';

-- If something went wrong, restore from backup
TRUNCATE TABLE ORDERS;
INSERT INTO ORDERS SELECT * FROM ORDERS_BACKUP;
DROP TABLE ORDERS_BACKUP;
```

**Why this works:** Cloning took milliseconds and cost almost nothing. Even if the update fails, you have an instant rollback.

### Use Case 2: Development/Test Sandbox

```sql
-- Prod environment
CREATE TABLE ANALYTICS_DB.PROD.CUSTOMER_MASTER
AS SELECT customer_id, name, email FROM RAW_DATA.CUSTOMERS;

-- Instantly create a sandbox for dev team testing
CREATE TABLE ANALYTICS_DB.DEV.CUSTOMER_MASTER_SANDBOX
CLONE ANALYTICS_DB.PROD.CUSTOMER_MASTER;

-- Dev team can now experiment safely without affecting production
UPDATE ANALYTICS_DB.DEV.CUSTOMER_MASTER_SANDBOX
SET email = CONCAT(email, '_TEST')
WHERE 1=1;
```

### Use Case 3: Point-in-Time Recovery with Time Travel

Combine cloning with Time Travel for powerful recovery:

```sql
-- A table was damaged 2 hours ago. Clone it from Time Travel
CREATE TABLE PRODUCTS_RECOVERED CLONE PRODUCTS AT (OFFSET => -7200);

-- Verify data looks correct
SELECT COUNT(*) FROM PRODUCTS_RECOVERED;

-- If good, restore
TRUNCATE TABLE PRODUCTS;
INSERT INTO PRODUCTS SELECT * FROM PRODUCTS_RECOVERED;
```

### Use Case 4: Temporary Data Validation

```sql
-- Before loading critical data, validate it in a clone
CREATE TABLE RAW_STAGING CLONE RAW_STAGING_INCOMING;

-- Run data quality checks
SELECT COUNT(*) FROM RAW_STAGING WHERE customer_id IS NULL;
SELECT COUNT(DISTINCT order_id) FROM RAW_STAGING;

-- Only if checks pass, accept the original
```

---

## 5. Swap Feature — Overview and Syntax

### What Is Table Swap?

Imagine your ETL pipeline refreshes a critical table every hour. The refresh takes 15 minutes, and during those 15 minutes:
- The old data is visible (stale)
- Queries might fail if they hit incomplete data
- Analysts see inconsistent numbers

With `SWAP`, you:
1. Build the new data in a staging table (while the live table continues serving queries)
2. Once validated, swap atomically → the new table becomes live instantly

```sql
-- Live table serving production
CREATE TABLE CUSTOMER_FACT (customer_id INT, name STRING, region STRING);

-- Build new version in staging (while CUSTOMER_FACT is still live)
CREATE TABLE CUSTOMER_FACT_NEW AS
SELECT customer_id, name, region
FROM raw_data.customers
WHERE last_modified > CURRENT_TIMESTAMP() - INTERVAL '1 hour';

-- Validate CUSTOMER_FACT_NEW...

-- Swap instantly (atomic, zero downtime)
ALTER TABLE CUSTOMER_FACT SWAP WITH CUSTOMER_FACT_NEW;
```

After the swap:
- `CUSTOMER_FACT` contains the new refreshed data
- `CUSTOMER_FACT_NEW` contains the old data
- All privileges, constraints, and grants on `CUSTOMER_FACT` remain intact
- The operation is **atomic** — either fully succeeds or fully fails

---

## 6. How Swap Works — Metadata Swapping

### The Metadata Exchange

Snowflake manages tables via metadata pointers. When you swap:

```sql
ALTER TABLE CUSTOMER_FACT SWAP WITH CUSTOMER_FACT_NEW;
```

Snowflake's Cloud Services layer literally **exchanges the metadata pointers** pointing to micro-partitions:

| Phase                    | CUSTOMER_FACT Metadata    | CUSTOMER_FACT_NEW Metadata |
| ------------------------ | ------------------------- | -------------------------- |
| **Before Swap**          | → Micro-partitions A1, A2 | → Micro-partitions B1, B2  |
| **After Swap (atomic)**  | → Micro-partitions B1, B2 | → Micro-partitions A1, A2  |

This is a **metadata-only operation** — no data files are moved or rewritten. It completes in milliseconds.

### Important: Grants and Ownership Stay with the Table Name

| Aspect              | Behavior                          |
| ------------------- | --------------------------------- |
| Privileges          | Stay with `CUSTOMER_FACT`         |
| Constraints         | Stay with `CUSTOMER_FACT`         |
| Clustering keys     | Stay with `CUSTOMER_FACT`         |
| Ownership           | Stay with `CUSTOMER_FACT`         |
| Dependent tasks     | Continue referencing `CUSTOMER_FACT` |

This is crucial: your downstream queries, BI tools, and roles don't need to know anything changed. They see the same table name, same permissions, same structure — but with fresh data.

### Why Swap Requires Identical Schemas

For the swap to be valid, both tables must have **identical structure**:

```sql
-- This works
ALTER TABLE T1 (ID INT, NAME STRING)
SWAP WITH T2 (ID INT, NAME STRING);

-- This FAILS
ALTER TABLE T1 (ID INT, NAME STRING)
SWAP WITH T2 (ID INT, NAME VARCHAR(100), AGE INT);
```

**Why?** If schemas differ, downstream code depending on the table structure might break. By requiring identical schemas, Snowflake guarantees that swapping is truly a zero-impact data refresh.

---

## 7. Swap Use Cases and Examples

### Use Case 1: Zero-Downtime Daily Refresh

Your company has a `DAILY_SALES_SUMMARY` table queried by 50+ analysts every minute:

```sql
-- Step 1: Create staging table with new data (while live table operates)
CREATE OR REPLACE TABLE DAILY_SALES_SUMMARY_NEW AS
WITH daily_totals AS (
  SELECT
    DATE_TRUNC('DAY', order_date) as sales_date,
    region,
    SUM(amount) as total_amount,
    COUNT(*) as order_count
  FROM raw_orders
  WHERE DATE_TRUNC('DAY', order_date) = CURRENT_DATE - 1
  GROUP BY 1, 2
)
SELECT * FROM daily_totals;

-- Step 2: Validate
SELECT COUNT(*) FROM DAILY_SALES_SUMMARY_NEW;  -- Expected: 50 regions
SELECT SUM(total_amount) FROM DAILY_SALES_SUMMARY_NEW;  -- Correlates with source

-- Step 3: Swap atomically (< 1 millisecond)
ALTER TABLE DAILY_SALES_SUMMARY SWAP WITH DAILY_SALES_SUMMARY_NEW;

-- Step 4: Archive old data for audit (optional)
-- DAILY_SALES_SUMMARY_NEW now contains yesterday's data
```

**Benefit:** Analysts querying `DAILY_SALES_SUMMARY` see updated data instantly. No downtime. No permission changes.

### Use Case 2: Instant Rollback on Data Quality Issues

```sql
-- Initial swap (refresh looks good)
ALTER TABLE FACT_ORDERS SWAP WITH FACT_ORDERS_NEW;

-- 30 minutes later, analyst notices data anomaly
-- Rollback: just swap again!
ALTER TABLE FACT_ORDERS SWAP WITH FACT_ORDERS_NEW;

-- Fact_orders reverts to old state, Fact_orders_new goes back to new
```

**Benefit:** You don't need `undrop` or `recover`. Just swap again to revert.

### Use Case 3: Blue-Green Deployments in ETL

```sql
-- Blue environment (production)
CREATE TABLE BLUE_CUSTOMERS AS SELECT * FROM raw_customers;

-- Build Green environment (new transformations)
CREATE TABLE GREEN_CUSTOMERS AS
SELECT
  customer_id,
  UPPER(TRIM(full_name)) as cleaned_name,
  CASE WHEN email LIKE '%@%.%' THEN email ELSE NULL END as email_validated,
  CAST(signup_date AS DATE) as signup_ts
FROM raw_customers;

-- Validate GREEN
-- Test queries
-- Run data quality checks
-- Once confident...

-- Switch to GREEN instantly
ALTER TABLE BLUE_CUSTOMERS SWAP WITH GREEN_CUSTOMERS;
```

### Use Case 4: Schema Evolution with Zero Downtime

```sql
-- Original table
CREATE TABLE EMPLOYEES (ID INT, NAME STRING, SALARY NUMBER);

-- New version with schema changes
CREATE TABLE EMPLOYEES_V2 (
  ID INT,
  NAME STRING,
  SALARY NUMBER,
  DEPARTMENT STRING,  -- New column
  START_DATE DATE     -- New column
);

INSERT INTO EMPLOYEES_V2
SELECT ID, NAME, SALARY, 'UNKNOWN', NULL FROM EMPLOYEES;

-- Swap to new schema
ALTER TABLE EMPLOYEES SWAP WITH EMPLOYEES_V2;

-- Downstream queries now have access to new columns
```

---

## 8. Clone vs Swap Comparison

| Aspect                 | Clone                               | Swap                                |
| ---------------------- | ----------------------------------- | ----------------------------------- |
| **Purpose**            | Create instant copy                 | Atomically exchange table data      |
| **Data copied?**       | No (initially)                      | No                                  |
| **Schema requirement** | Can differ                          | Must be identical                   |
| **Independence**       | Yes (after first write via CoW)     | N/A (distinct tables)              |
| **Downtime impact**    | None (creates new object)           | None (metadata swap only)          |
| **Typical use case**   | Backup, testing, sandbox            | Production refresh, deployment     |
| **Storage cost**       | Minimal (until divergence)          | Minimal (metadata only)            |
| **Privileges**        | Not copied (must re-grant)          | Retained by original table name    |
| **Can undo?**          | Yes (drop the clone)                | Yes (swap again)                   |
| **Works with schemas/dbs?** | Yes | Tables only |

---

## 9. Best Practices

1. **Use Clone for backups before mass DML**

   ```sql
   CREATE TABLE orders_preupdate_backup CLONE orders;
   UPDATE orders SET status = 'processed' WHERE created_date < '2020-01-01';
   -- Keep backup around during retention period in case issues arise
   ```

2. **Use Swap for production table refreshes**

   Instead of:
   ```sql
   TRUNCATE TABLE daily_summary;
   INSERT INTO daily_summary SELECT * FROM staging;
   ```

   Do this:
   ```sql
   CREATE TABLE daily_summary_new AS SELECT * FROM staging;
   ALTER TABLE daily_summary SWAP WITH daily_summary_new;
   ```

   The former has a window where the table is empty or inconsistent. The latter is atomic.

3. **Always validate before swapping**

   ```sql
   CREATE TABLE target_new AS SELECT * FROM source WHERE validation = TRUE;
   SELECT COUNT(*) expected_rows FROM target_new;
   SELECT SUM(amount) expected_total FROM target_new;
   -- Only after validation
   ALTER TABLE target SWAP WITH target_new;
   ```

4. **Combine Clone with Time Travel for recovery**

   ```sql
   -- Table was corrupted 3 hours ago
   CREATE TABLE table_recovered CLONE table_name AT (OFFSET => -10800);
   ```

5. **Document your cloning/swap procedures**

   - Which tables are backed up pre-operation?
   - How long are backups retained?
   - What validation triggers a swap?
   - How is rollback coordinated?

6. **Monitor storage growth from clones**

   Once clones diverge from their source via CoW, they consume separate storage. Monitor this with:
   ```sql
   SELECT
     table_name,
     bytes / (1024*1024*1024) as size_gb
   FROM information_schema.tables
   WHERE schema_name = 'YOUR_SCHEMA'
   ORDER BY bytes DESC;
   ```

7. **Test recovery workflows in non-prod**

   Practice swapping and cloning in dev before relying on them in production.

### Best Practice Checklist

- [ ] Document which tables use cloning for backups
- [ ] Set up pre-DML clone automation for critical tables
- [ ] Validate data quality before every swap operation
- [ ] Monitor clone storage and costs
- [ ] Test swap/clone recovery in non-prod environments
- [ ] Implement monitoring/alerting for failed swaps
- [ ] Include rollback procedures in deployment runbooks

---

## 10. Gotchas and Limits

- **Swap requires identical schema** — Even a single column mismatch causes failure. Plan schema changes separately.

- **Swap is table-level only** — You cannot swap schemas or databases. Clone can, but swap cannot.

- **Privileges are not cloned** — When you clone a table, GRANT statements don't transfer. You must manually grant to the clone. (Cloning schemas/databases can optionally include grants with `INCLUDE ALL`.)

- **Temporary tables cannot be cloned** — Temporary tables are session-scoped. You can clone transient tables, but not temporary ones.

- **Views and materialized views cannot be cloned** — Only physical storage-backed objects (tables, schemas, databases, streams, stages, file formats).

- **Cloning a dropped table requires Time Travel window** — If you drop a table and its Time Travel retention has expired, even cloning can't recover it.

- **Streams attached to tables prevent swapping** — If a table has an active stream tracking changes, you cannot swap it. Drop or suspend the stream first.

- **Time Travel history doesn't swap** — When you swap two tables, their Time Travel histories remain independent. Querying `table AT (OFFSET => ...)` still returns that specific table's history, not the swapped data.

---

## 11. Common Questions & Answers

### What is zero-copy cloning in Snowflake and how does it differ from CTAS?

**Answer:**

Zero-copy cloning creates a copy of a table, schema, or database **instantly without physically copying data**. It copies only the metadata pointing to existing micro-partitions.

CTAS (Create Table As Select) physically writes a new data set to storage.

| Operation | Data Movement      | Time              | Cost  |
| --------- | ------------------ | ----------------- | ----- |
| CLONE     | No (metadata only) | Instant (ms)      | $0.00 |
| CTAS      | Yes (full copy)    | Minutes to hours  | High  |

```sql
CREATE TABLE emp_clone CLONE emp;  -- Instant, metadata only
CREATE TABLE emp_copy AS SELECT * FROM emp;  -- Physical copy
```

For a 500 GB table, cloning takes ~100 ms and costs nothing. CTAS takes 10+ minutes and consumes credits.

---

### How does Copy-on-Write ensure independence between source and clone?

**Answer:**

Initially, source and clone share the same micro-partition files (immutable in object storage). When either table is modified:

1. Snowflake creates **new micro-partitions** for the modified table containing changed data
2. Updates that table's metadata to reference the new micro-partitions
3. The unmodified table's metadata remains unchanged

Result: Both tables diverge into independent copies, each referencing their own micro-partitions.

```sql
CREATE TABLE t1 AS SELECT 1 as id, 'A' as value;
CREATE TABLE t2 CLONE t1;
-- Both point to same micro-partition

DELETE FROM t1 WHERE id = 1;
-- t1 now references new micro-partition (excluded row)
-- t2 still references original micro-partition (includes row)

SELECT * FROM t1;  -- (0 rows)
SELECT * FROM t2;  -- (1 row: id=1, value='A')
```

---

### What happens when the source table is dropped after cloning?

**Answer:**

The clone remains **fully functional and intact**. Snowflake uses reference counting internally — micro-partitions are deleted only when no object references them.

```sql
CREATE TABLE source AS SELECT * FROM values (1),(2);
CREATE TABLE clone CLONE source;
DROP TABLE source;
SELECT * FROM clone;  -- Still works perfectly
```

The clone is independent. It doesn't rely on the source table existing.

---

### Can cloning be done across schemas and databases?

**Answer:**

**Yes**, within the same Snowflake account:

```sql
CREATE TABLE prod_db.public.sales_clone
CLONE analytics_db.staging.sales;
```

**Cross-account cloning** is not directly supported. For that, use database replication or data sharing.

---

### Can we clone a table that was dropped but still within Time Travel retention?

**Answer:**

Yes! One of Snowflake's most powerful recovery features:

```sql
-- SALES table was dropped
-- But within retention period, you can still clone it
CREATE TABLE sales_recovered
CLONE sales AT (BEFORE (TIMESTAMP => '2025-02-26 10:00:00'));
```

Even though `sales` is dropped, its metadata and micro-partitions are retained. Cloning from a historical point restores the data instantly.

---

### What objects can be cloned?

**Can clone:**
- Tables
- Schemas (optionally including grants with `INCLUDE ALL`)
- Databases
- Streams
- Stages
- File formats

**Cannot clone:**
- Views
- Materialized views
- Sequences
- Transient/temporary tables (temporary cannot be cloned; transient can be)

These are logical or session-scoped objects without physical storage backing.

---

### Do cloned tables inherit privileges?

**Answer:**

No. Privileges are **not copied** during cloning. You must grant them explicitly:

```sql
GRANT SELECT ON TABLE emp_clone TO ROLE analyst;
```

**Exception:** When cloning schemas or databases, you can use `INCLUDE ALL` to include grants:

```sql
CREATE SCHEMA dev_schema CLONE prod_schema INCLUDE ALL;
```

---

### What is the difference between swapping and renaming a table?

**Answer:**

| Operation | Swaps Data? | Preserves Grants? | Downtime | Reversible? |
| --------- | ----------- | ----------------- | -------- | ----------- |
| Swap      | Yes         | Yes               | None     | Yes (re-swap) |
| Rename    | No          | Yes               | None     | No          |

Swapping exchanges data between two tables while preserving privileges on the original name. Renaming just changes the table's name, not its data.

For production refreshes, swap is superior because it's atomic, reversible, and maintains all permissions.

---

### What happens if tables being swapped have different structures?

**Answer:**

Snowflake will **reject the swap**:

```sql
ALTER TABLE t1 SWAP WITH t2;
-- Error: cannot swap tables with different structures
```

Both tables must have:
- Identical columns (same names, order, data types)
- Identical constraints
- Identical clustering keys

This guarantee ensures downstream code doesn't break from unexpected schema changes.

---

### Can table swap be undone?

**Answer:**

Not directly with an `UNDO` command, but yes — you can **swap again** to revert:

```sql
ALTER TABLE sales SWAP WITH sales_new;  -- Refresh
-- ... later, issue discovered ...
ALTER TABLE sales SWAP WITH sales_new;  -- Rollback to old state
```

Each swap is reversible as long as both tables exist.

---

### How do swap and clone interact with Time Travel?

**Answer:**

Both preserve Time Travel independently:

- **Cloning:** The clone inherits the source's data but starts its own Time Travel history from the clone point onward
- **Swapping:** Each table retains its own Time Travel history. Querying `table AT (...)` returns that table's historical versions, not the swapped data

```sql
CREATE TABLE orders CLONE orders_historical AT (TIMESTAMP => '2025-02-25');
-- orders now contains data from that timestamp
-- But orders can be time-traveled independently from that point forward

ALTER TABLE live SWAP WITH staged;
-- live's time travel still shows its own history before swap
-- staged's time travel shows its own history before swap
```

---

### What are the best use cases for clone vs swap?

**Use Clone for:**
- Backups before risky operations
- Development/testing sandboxes
- Recovery with Time Travel
- Data validation in isolated environments

**Use Swap for:**
- Production table refreshes with zero downtime
- Blue-green deployments
- Instant rollback capabilities
- Schema evolution with backward compatibility

---

## References

- [Cloning Databases, Schemas, and Tables](https://docs.snowflake.com/en/user-guide/object-clone)
- [Zero-Copy Cloning](https://docs.snowflake.com/en/user-guide/object-clone-intro)
- [ALTER TABLE SWAP WITH](https://docs.snowflake.com/en/sql-reference/sql/alter-table-swap-with)
- [Snowflake Micro-partitions](https://docs.snowflake.com/en/user-guide/tables-clustering-keys)
- [Time Travel with Cloning](https://docs.snowflake.com/en/user-guide/data-time-travel)
- [Streams on Cloned Tables](https://docs.snowflake.com/en/user-guide/streams-clone)
