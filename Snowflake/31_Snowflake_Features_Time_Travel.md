# Snowflake Features — Time Travel

## What Is This About?

Time Travel is a Snowflake feature that lets you access historical versions of table data for a configured retention period. You can query, clone, or restore past states of objects (tables, schemas, databases) — inspecting or recovering data as of a point in the past. This works for SELECT (query history), CLONE, and UNDROP (restore dropped objects).

If your colleague runs `UPDATE PROD.CUSTOMER SET status = 'inactive'` with a missing `WHERE`, Snowflake has stored the previous state for every changed micro-partition. You can query the table *as it was* before that update (within the retention window) and either copy data back or restore the entire table.

---

## Table of Contents

1. [Retention Period — What It Means and Limits](#1-retention-period--what-it-means-and-limits)
2. [Checking an Object's Time Travel Retention](#2-checking-an-objects-time-travel-retention)
3. [UNDROP — Recovering Dropped Objects](#3-undrop--recovering-dropped-objects)
4. [CREATE OR REPLACE — Why It Breaks Time Travel](#4-create-or-replace--why-it-breaks-time-travel)
5. [Querying Historical Data with AT / BEFORE / OFFSET](#5-querying-historical-data-with-at--before--offset)
6. [Recovering a Table After a Mistaken UPDATE](#6-recovering-a-table-after-a-mistaken-update)
7. [How Time Travel Works Internally](#7-how-time-travel-works-internally)
8. [Best Practices](#8-best-practices)
9. [Gotchas and Limits](#9-gotchas-and-limits)
10. [Common Questions & Answers](#10-common-questions--answers)

---

## 1. Retention Period — What It Means and Limits

The **data retention period** is the number of days Snowflake keeps historical versions for Time Travel. Default is **1 day (24 hours)** for most accounts; Enterprise and above can extend this up to 90 days for permanent tables. A retention of **0** disables Time Travel for that object.

After the Time Travel retention ends, Snowflake keeps data for a further **7 days** as part of **Fail-Safe** for permanent tables. Fail-Safe is only for Snowflake internal recovery and **cannot** be used by users for Time Travel queries.

| Table Type    | Default Time Travel | Max Retention | Fail-Safe Available? | Notes                    |
| ------------- | ------------------- | ------------- | -------------------- | ------------------------ |
| **Permanent** | 1 day               | up to 90 days | Yes (7 days)         | Ideal for production     |
| **Transient** | 1 day               | 1 day         | No                   | Lower cost, no Fail-Safe |
| **Temporary** | 0 days              | 0 days        | No                   | Exists only for session  |

---

## 2. Checking an Object's Time Travel Retention

You can inspect retention settings at different object levels (account, database, schema, table).

### Check at the table level

```sql
SHOW PARAMETERS LIKE 'DATA_RETENTION_TIME_IN_DAYS' IN TABLE my_db.my_schema.my_table;
```

### Check at the schema or database level

```sql
SHOW PARAMETERS LIKE 'DATA_RETENTION_TIME_IN_DAYS' IN SCHEMA my_db.my_schema;
SHOW PARAMETERS LIKE 'DATA_RETENTION_TIME_IN_DAYS' IN DATABASE my_db;
```

This returns the retention value (in days) and where it's set (object level vs inherited).

### Quick metadata check

```sql
DESC TABLE my_db.my_schema.my_table;
-- or
SHOW TABLES IN SCHEMA my_db.my_schema LIKE 'my_table';
```

### Change retention for a table

```sql
ALTER TABLE my_schema.orders SET DATA_RETENTION_TIME_IN_DAYS = 7;
```

You can set retention at database, schema, or table level. Account-level defaults also exist.

---

## 3. UNDROP — Recovering Dropped Objects

If an object was dropped within the Time Travel retention period, you can restore it with `UNDROP`:

```sql
UNDROP TABLE my_schema.orders;
UNDROP SCHEMA my_schema;
UNDROP DATABASE my_database;
```

`UNDROP` restores the most recently dropped version of the object. If the retention window has expired, `UNDROP` will fail — after that, the only hope is Fail-Safe (via Snowflake Support).

If multiple drops/recreates happened, you may need to examine the object history via `SHOW TABLES` history or `INFORMATION_SCHEMA` views to find dropped versions.

---

## 4. CREATE OR REPLACE — Why It Breaks Time Travel

`CREATE OR REPLACE TABLE` performs a **drop + create** behind the scenes. This removes the old table and its metadata, meaning the link to historical data is lost. Time Travel can't present the old table under the same name after `CREATE OR REPLACE` because a new object was created.

```sql
-- The old version of orders is no longer accessible via Time Travel
CREATE OR REPLACE TABLE my_schema.orders AS
SELECT * FROM staging.orders;
```

If you need to remove rows while preserving historical state, use `TRUNCATE` or `DELETE` instead — Time Travel retains history for those operations.

**Rule of thumb:** Only use `CREATE OR REPLACE` when you truly intend to replace the object and discard prior state.

---

## 5. Querying Historical Data with AT / BEFORE / OFFSET

Snowflake provides `AT` and `BEFORE` clauses to request historical state. There are three time specifiers: `TIMESTAMP`, `STATEMENT`, and `OFFSET` (seconds back relative to now).

### Using OFFSET (seconds ago)

```sql
-- See the table as it was 5 minutes (300 seconds) ago
SELECT *
FROM my_schema.orders
AT (OFFSET => -60*5);
```

### Using TIMESTAMP

```sql
SELECT *
FROM my_schema.orders
AT (TIMESTAMP => '2025-10-18 10:15:00'::timestamp);
```

### Using STATEMENT (query ID)

```sql
SELECT *
FROM my_schema.orders
AT (STATEMENT => '01a1234b-0000-1234-0000-abcdef123456');
```

**AT** gives data *as of* that point (inclusive). **BEFORE** gives the state *just before* that time or statement.

---

## 6. Recovering a Table After a Mistaken UPDATE

Scenario: you accidentally ran `UPDATE my_schema.orders SET status='cancelled'` 10 minutes ago.

### Option A — Create a backup from a historical snapshot (CTAS)

```sql
-- 1. Create backup from 10 minutes ago
CREATE TABLE my_schema.orders_backup AS
SELECT *
FROM my_schema.orders AT (OFFSET => -60*10);

-- 2. Verify
SELECT COUNT(*) FROM my_schema.orders_backup;
SELECT COUNT(*) FROM my_schema.orders;

-- 3. Restore
BEGIN;
TRUNCATE TABLE my_schema.orders;
INSERT INTO my_schema.orders
SELECT * FROM my_schema.orders_backup;
COMMIT;
```

### Option B — Clone the historical version (zero-copy)

```sql
CREATE TABLE my_schema.orders_clone CLONE my_schema.orders AT (OFFSET => -600);
```

Cloning is efficient and quick — metadata points to the same micro-partitions initially. Then swap or copy data from the clone to production per your rollback policy.

### Option C — If the table was dropped

```sql
UNDROP TABLE my_schema.orders;
```

Only works within the retention period.

---

## 7. How Time Travel Works Internally

### S3 and Immutable Files

Snowflake's underlying storage (Amazon S3, Azure Blob, or GCP Cloud Storage) is object storage where objects are immutable. You can't modify a file — you must re-upload the entire file. So how does Snowflake "go back in time" without re-uploading anything? The answer lies in the **metadata layer** and **micro-partitioning**.

### Micro-Partitions

When you load data into a Snowflake table, it breaks data into **immutable micro-partitions** — each typically 50–500 MB compressed. Each micro-partition is stored as a separate immutable file in object storage.

When data changes (INSERT/UPDATE/DELETE), Snowflake **never edits existing files**. Instead, it:

1. Creates *new* micro-partition files for new or changed data.
2. Updates *metadata* to point to the correct set of active partitions.

### The Metadata Layer

Snowflake's metadata layer maintains a **versioned mapping** between logical table data and physical micro-partition files. Each DML or DDL operation creates a **new snapshot** of the metadata:

| Version | Timestamp           | Operation       | Active Micro-partitions |
| ------- | ------------------- | --------------- | ----------------------- |
| 1       | 2025-10-18 10:00:00 | Initial load    | MP1, MP2, MP3           |
| 2       | 2025-10-18 10:10:00 | Update 100 rows | MP1, MP2', MP3          |
| 3       | 2025-10-18 10:20:00 | Insert 10k rows | MP1, MP2', MP3, MP4     |

Unchanged micro-partitions are reused. When you time travel 10 minutes back, you're telling Snowflake to show the table at an older metadata version. No files are changed — only **which micro-partitions** are read changes.

### What Happens When You DROP a Table

When you `DROP TABLE`, Snowflake does **not** delete the S3 files immediately:

1. Metadata is updated to mark the table as *dropped* — the table becomes invisible to users.
2. The underlying micro-partition files remain in storage, linked to the "dropped table" version, until the retention period expires.
3. After retention expires, files are retained another 7 days in Fail-Safe, then permanently deleted.

### Architecture Diagram

```
                ┌────────────────────────────┐
                │  Cloud Services Layer      │
                │  (Metadata + Control Plane)│
                ├────────────────────────────┤
                │  Table Metadata History    │
                │  • Version 1: MP1, MP2     │
                │  • Version 2: MP1, MP3     │
                │  • Version 3: MP1, MP3, MP4│
                └──────────┬─────────────────┘
                           │
                           ▼
          ┌────────────────────────────────────────────┐
          │      Snowflake Storage Layer (S3/Blob)     │
          │────────────────────────────────────────────│
          │ MP1 ──┐                                    │
          │ MP2 ──┘  Immutable columnar micro-partitions│
          │ MP3 ──┐   (Files stored in object storage)  │
          │ MP4 ──┘                                    │
          └────────────────────────────────────────────┘
                           │
          ┌────────────────┴──────────────────────────┐
          │          Compute Layer (Virtual WH)       │
          │  Queries reference micro-partitions based │
          │  on metadata version requested (AT/B4)    │
          └──────────────────────────────────────────┘
```

### Analogy — Git for Data

Think of Time Travel like Git:

- **S3** = the repository's object store (files never change)
- **Snowflake Metadata** = Git commits
- **Each DML/DDL** = a new commit
- **`AT (OFFSET => ...)`** = checkout to an older commit

Snowflake just changes which "commit" (metadata version) you're seeing.

### Quick Example

```sql
-- Step 1: Create a table and insert data
CREATE OR REPLACE TABLE sales (id INT, amount NUMBER);
INSERT INTO sales VALUES (1, 100), (2, 200);

-- Step 2: Update a value
UPDATE sales SET amount = 999 WHERE id = 1;

-- Step 3: View current version
SELECT * FROM sales;

-- Step 4: Time travel to before the update
SELECT * FROM sales AT (OFFSET => -60*5);
```

You'll see the original value `100` again — Snowflake reverted to the metadata that pointed to the previous partition.

### Summary of Internal Components

| Component           | Role                                        | Behavior                           |
| ------------------- | ------------------------------------------- | ---------------------------------- |
| **Micro-partition** | Small, compressed immutable data block      | Stored on S3 / Blob / GCS         |
| **Metadata layer**  | Logical view of which partitions are active  | Updated on each DML/DDL            |
| **Time Travel**     | Lets you query older metadata snapshots      | Works via `AT` / `BEFORE`          |
| **DROP TABLE**      | Marks metadata as inactive                   | Files kept until retention expires |
| **Fail-Safe**       | 7-day internal recovery window               | For Snowflake-managed restore only |

---

## 8. Best Practices

1. **Retention strategy by environment** — Production/permanent tables: keep Time Travel > 1 day (consider 7–30 days depending on RPO and cost for Enterprise accounts). Development/transient tables: set lower retention (0–1 day) to save storage costs.

2. **Never use `CREATE OR REPLACE` in prod to remove rows** — use `TRUNCATE` if you want to empty a table but keep history available for rollback.

3. **Automated pre-flight backup before mass DML** — before large updates/deletes, create a snapshot/clone:

```sql
CREATE OR REPLACE TABLE my_schema.orders_preupdate_clone CLONE my_schema.orders;
```

4. **Use zero-copy CLONE for quick snapshots** (cheap, fast) and use CTAS for immutable backup copies if you prefer independence.

5. **Document and require change approval for any job that runs DDL/DML at scale** — include a step that creates a clone or backup automatically.

6. **Use role separation and guarded scripts** — require higher privilege and a confirmation step for destructive queries.

7. **Monitor Time Travel storage costs** — older versions consume storage; balance retention window vs cost.

8. **Test UNDROP and recovery workflows in non-prod** — practice makes you fast when real incidents happen.

### Best Practice Checklist

- [ ] Set sensible `DATA_RETENTION_TIME_IN_DAYS` per environment.
- [ ] Require a pre-DML clone/backup step in all mass update jobs.
- [ ] Avoid `CREATE OR REPLACE` in prod unless intended.
- [ ] Test `UNDROP` and restore workflows.
- [ ] Monitor Time Travel storage (billing) and tune retention accordingly.
- [ ] Use zero-copy CLONE for fast snapshots and CTAS if you want an independent copy.

---

## 9. Gotchas and Limits

- **Max retention** depends on edition: standard accounts default to 1 day and can be set to 0 or 1; Enterprise+ allow up to 90 days for permanent tables.

- **Temporary and transient tables** have different retention and Fail-Safe behavior — usually not suitable for long-term recovery.

- **CREATE OR REPLACE** destroys Time Travel ability for the prior object (drop + recreate semantics).

- **UNDROP** only restores within the Time Travel window. After that, Fail-Safe cannot be used by users.

- **Offsets are seconds**: when you specify OFFSET, it's in seconds (so `-60*5` = -300 sec). `TIMESTAMP` accepts explicit timestamps.

---

## 10. Common Questions & Answers

### What is Time Travel and what operations does it enable?

Time Travel allows you to access historical data (previous versions of tables, schemas, or databases) for a defined retention period. It enables three operations: **query** historical data using `AT` or `BEFORE` clauses, **clone** objects as they existed at a past point in time, and **undrop** objects that were dropped within the retention period.

```sql
SELECT *
FROM sales.orders
AT (OFFSET => -300);   -- See the table as it was 5 minutes ago
```

---

### How do you access a table's state from 10 minutes ago?

Use the `AT` or `BEFORE` clause with OFFSET, TIMESTAMP, or STATEMENT parameters. For 10 minutes ago (600 seconds):

```sql
SELECT *
FROM my_schema.orders
AT (OFFSET => -600);
```

`AT` gives data *as of* that point. `BEFORE` gives data *just before* that point.

---

### What happens with CREATE OR REPLACE TABLE — can you time travel to the previous version?

No. `CREATE OR REPLACE TABLE` performs a drop + create behind the scenes. The old version no longer exists for Time Travel. If you instead use `TRUNCATE TABLE`, the old version *would* still be recoverable for the retention period.

---

### What is Fail-Safe and how is it different from Time Travel?

Fail-Safe is a 7-day period after the Time Travel window expires, during which Snowflake can recover data internally for disaster recovery purposes.

| Feature         | Accessible by user? | Duration     | Purpose                                 |
| --------------- | -------------------- | ------------ | --------------------------------------- |
| **Time Travel** | Yes                  | 0–90 days    | Query or recover data by yourself       |
| **Fail-Safe**   | No (Snowflake only)  | Fixed 7 days | For Snowflake-managed disaster recovery |

---

### How do you restore a dropped table?

Use `UNDROP TABLE` — available only within the Time Travel retention window:

```sql
UNDROP TABLE my_schema.orders;
```

You can also undrop schemas and databases. If the retention period has expired, UNDROP will fail.

---

### How does zero-copy cloning interact with Time Travel?

Zero-copy cloning and Time Travel complement each other. Time Travel gives you historical access, while Clone lets you materialize that historical snapshot as a live, independent object:

```sql
CREATE TABLE orders_clone CLONE orders AT (OFFSET => -3600);
```

This creates `orders_clone` exactly as `orders` looked 1 hour ago — instantly and without duplicating storage. Clones share underlying micro-partitions, so the initial cost is near zero. Any changes after cloning create new micro-partitions only for changed data.

---

### How would you architect automated safe updates to production tables?

Before large modifications, create a zero-copy clone:

```sql
CREATE OR REPLACE TABLE orders_backup CLONE orders;
```

Perform the update, and if something goes wrong, restore from the backup:

```sql
TRUNCATE TABLE orders;
INSERT INTO orders SELECT * FROM orders_backup;
```

Keep the retention period at 7–30 days for production data so you have a recovery window even without manual backups.

---

### Is XML querying related to Time Travel?

No — they are independent features. Time Travel works on any table regardless of the data format stored in it (structured columns, VARIANT/JSON, VARIANT/XML, etc.). Any table with a non-zero retention period supports Time Travel.

---

## References

- [Understanding & using Time Travel](https://docs.snowflake.com/en/user-guide/data-time-travel)
- [Snowflake Time Travel & Fail-safe](https://docs.snowflake.com/en/user-guide/data-availability)
- [Working with Temporary and Transient Tables](https://docs.snowflake.com/en/user-guide/tables-temp-transient)
- [AT | BEFORE clause](https://docs.snowflake.com/en/sql-reference/constructs/at-before)
- [UNDROP TABLE](https://docs.snowflake.com/en/sql-reference/sql/undrop-table)
- [CREATE object CLONE](https://docs.snowflake.com/en/sql-reference/sql/create-clone)
- [CREATE TABLE](https://docs.snowflake.com/en/sql-reference/sql/create-table)
- [SHOW TABLES](https://docs.snowflake.com/en/sql-reference/sql/show-tables)
