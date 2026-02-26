# ⚙️ Snowflake Tasks: Automating Your Data Pipelines

## 🌟 The Problem: Manual ETL at 2 AM

Imagine you're working at **IQVIA**, managing a data warehouse with sales data from multiple regions.

**Your current reality:**
- Every night, files land in S3
- Snowpipe loads them into a raw staging table
- You manually transform the data using SQL scripts
- Then manually aggregate and load into fact tables
- Finally, refresh reports

**The question:** Do you want to log in at 2 AM every night to run `INSERT INTO ... SELECT ...`? 😴

**The answer:** No. That's where **Snowflake Tasks** come in.

---

## 🎯 What Is a Snowflake Task?

> A **Task** in Snowflake is a **scheduled SQL operation** that runs automatically inside Snowflake — think of it as a **native cron job** or **Airflow DAG**, but built directly into the database.

**Key insight:** You don't need external schedulers (Airflow, Azure Data Factory, etc.). Snowflake manages it all.

---

## 💡 Purpose & Problem Solved

### Without Tasks ❌
- Manual SQL execution or external scripts
- External orchestration tool required (Airflow, Airflow is complex)
- Monitoring requires checking multiple systems
- Error handling is scattered across tools

### With Tasks ✅
- Native Snowflake scheduling
- No external dependencies
- Central monitoring via `TASK_HISTORY`
- Simple, self-contained workflows
- Automatic retry logic (3 retries by default)

**Bottom line:** Tasks let you **build, schedule, and monitor data pipelines entirely within Snowflake**.

---

## 🧩 Creating a Simple Task (Step-by-Step)

Let's build a task that loads daily sales data automatically.

### Basic Task Creation

```sql
CREATE OR REPLACE TASK DAILY_SALES_ETL
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = 'USING CRON 0 6 * * * Asia/Dhaka'
  AS
  INSERT INTO FACT_SALES 
  SELECT * FROM STAGING_SALES 
  WHERE LOAD_DATE = CURRENT_DATE();
```

### Breaking It Down

| Component | Meaning |
|-----------|---------|
| `CREATE OR REPLACE TASK` | Define or overwrite a task |
| `DAILY_SALES_ETL` | Task name (must be unique in schema) |
| `WAREHOUSE = COMPUTE_WH` | Which warehouse runs the SQL |
| `SCHEDULE = 'USING CRON ...'` | When to run (cron syntax) |
| `AS` | The actual SQL to execute |

**What this does:** Every day at 6 AM (Dhaka timezone), Snowflake automatically:
1. Wakes up the COMPUTE_WH warehouse
2. Runs the INSERT INTO statement
3. Loads that day's sales data into the fact table
4. Logs the execution result

---

## 🕒 Scheduling Tasks: Two Options

### Option 1: CRON Expression (Precise Timing)

```sql
SCHEDULE = 'USING CRON 0 6 * * * Asia/Dhaka'
```

**Cron breakdown:**
```
0      6      *      *      *      Asia/Dhaka
│      │      │      │      │      └─ Timezone
│      │      │      │      └────────── Day of week (0-6, 0=Sunday)
│      │      │      └───────────────── Month (1-12)
│      │      └──────────────────────── Day of month (1-31)
│      └─────────────────────────────── Hour (0-23)
└──────────────────────────────────────── Minute (0-59)
```

**Examples:**
```sql
SCHEDULE = 'USING CRON 0 6 * * * UTC'          -- Every day 6 AM UTC
SCHEDULE = 'USING CRON 0 9 * * 1-5 UTC'        -- Weekdays 9 AM
SCHEDULE = 'USING CRON 0 0,12 * * * UTC'       -- Midnight & noon
SCHEDULE = 'USING CRON */15 * * * * UTC'       -- Every 15 minutes
```

### Option 2: INTERVAL (Relative Timing)

```sql
SCHEDULE = '1 HOUR'
```

→ Runs every 1 hour **after the previous execution completes.**

**Examples:**
```sql
SCHEDULE = '30 MINUTE'               -- Every 30 minutes
SCHEDULE = '1 DAY'                   -- Every day (at same time)
SCHEDULE = '3 HOUR'                  -- Every 3 hours
```

**Key difference:**
- **CRON** = Fixed time (e.g., 6 AM every day)
- **INTERVAL** = Relative time (e.g., 1 hour after previous run ends)

---

## 💤 Suspending & Resuming Tasks

### Important: Tasks Start Suspended!

When you create a task, it's **SUSPENDED by default** — meaning it won't run automatically.

```sql
-- Create task
CREATE TASK DAILY_SALES_ETL
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = 'USING CRON 0 6 * * * UTC'
  AS INSERT INTO FACT_SALES ...;

-- Task is now SUSPENDED, so let's activate it
ALTER TASK DAILY_SALES_ETL RESUME;
```

### Suspending an Active Task

Sometimes you need to pause temporarily (maintenance, debugging):

```sql
ALTER TASK DAILY_SALES_ETL SUSPEND;
```

The task won't run at its scheduled time, but you can resume it later without recreating.

---

## 📊 Checking Task History

To debug or monitor your tasks, use `TASK_HISTORY`:

```sql
SELECT *
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
  TASK_NAME => 'DAILY_SALES_ETL',
  RESULT_LIMIT => 10
))
ORDER BY SCHEDULED_TIME DESC;
```

**Output columns:**
| Column | Shows |
|--------|-------|
| SCHEDULED_TIME | When task was supposed to run |
| COMPLETED_TIME | When task finished |
| STATE | SUCCESS, FAILED, SKIPPED |
| RETURN_VALUE | SQL result (if any) |
| ERROR_CODE | Error message (if failed) |
| QUERY_ID | Link to query history |

**Pro tip:** Use `QUERY_ID` to drill into the full query execution details.

---

## 🔗 Creating Task Workflows (Dependencies)

Here's where Snowflake Tasks become powerful. You can **chain tasks** so one runs after another — like a DAG (Directed Acyclic Graph).

### Real Scenario: Multi-Layer ETL

Your data layers:
```
Raw Data (S3) 
    ↓
RAW_SALES (loaded by Snowpipe)
    ↓
STAGING_SALES (transformed)
    ↓
FACT_SALES (aggregated)
    ↓
DAILY_REPORTS (output)
```

Instead of one big task, you can create **4 dependent tasks**:

### Step 1: Root Task (Has Schedule)

```sql
CREATE OR REPLACE TASK LOAD_RAW_SALES
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = 'USING CRON 0 2 * * * UTC'
  AS
  INSERT INTO RAW_SALES
  SELECT * FROM @EXTERNAL_STAGE
  (FILE_FORMAT => csv_format);
```

→ Runs at 2 AM, loads data from S3 into RAW_SALES

### Step 2: First Child Task (Triggered by Parent)

```sql
CREATE OR REPLACE TASK TRANSFORM_STAGING
  WAREHOUSE = COMPUTE_WH
  AFTER LOAD_RAW_SALES
  AS
  INSERT INTO STAGING_SALES
  SELECT 
    order_id,
    TRIM(customer_name) AS customer_name,
    CAST(amount AS DECIMAL(10,2)) AS amount
  FROM RAW_SALES
  WHERE LOAD_DATE = CURRENT_DATE();
```

→ Runs **only after** LOAD_RAW_SALES succeeds

### Step 3: Second Child Task

```sql
CREATE OR REPLACE TASK AGGREGATE_FACT
  WAREHOUSE = COMPUTE_WH
  AFTER TRANSFORM_STAGING
  AS
  INSERT INTO FACT_SALES
  SELECT 
    region,
    product_category,
    SUM(amount) AS total_sales,
    COUNT(*) AS transaction_count
  FROM STAGING_SALES
  GROUP BY region, product_category;
```

→ Runs **only after** TRANSFORM_STAGING succeeds

### Step 4: Final Task (Report Refresh)

```sql
CREATE OR REPLACE TASK REFRESH_REPORTS
  WAREHOUSE = COMPUTE_WH
  AFTER AGGREGATE_FACT
  AS
  CALL REFRESH_DAILY_DASHBOARD();
```

→ Runs **only after** AGGREGATE_FACT succeeds

### Visual Task Workflow

```
          ┌──────────────────┐
          │ LOAD_RAW_SALES   │  (Has schedule: 2 AM)
          │   (Root Task)    │
          └────────┬─────────┘
                   │
                   ▼ (on success)
         ┌────────────────────┐
         │TRANSFORM_STAGING   │
         │ (Child Task 1)     │
         └────────┬───────────┘
                   │
                   ▼ (on success)
         ┌────────────────────┐
         │ AGGREGATE_FACT     │
         │ (Child Task 2)     │
         └────────┬───────────┘
                   │
                   ▼ (on success)
         ┌────────────────────┐
         │REFRESH_REPORTS     │
         │ (Child Task 3)     │
         └────────────────────┘
```

### Critical Rules for Tasks

| Rule | Implication |
|------|-------------|
| **Only root has SCHEDULE** | Child tasks trigger automatically |
| **Child task uses AFTER** | Depends on parent success |
| **One parent per child** | A task can't depend on multiple tasks (design your SQL accordingly) |
| **No circular dependencies** | Task A → B → C is OK. But A → B → A fails |
| **No scheduling child tasks** | Child tasks can't have their own schedule |

---

## ⚡ Task Variations (Most Common)

### 1. Simple One-Time Task
```sql
CREATE OR REPLACE TASK REFRESH_MART_NIGHTLY
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = '1 DAY'
  AS
  INSERT INTO DATA_MART
  SELECT * FROM FACT_TABLE;
```

### 2. Stream-Based Incremental Load
```sql
CREATE OR REPLACE TASK CDC_MERGE_CUSTOMER
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = '1 HOUR'
  AS
  MERGE INTO DIM_CUSTOMER d
  USING CUSTOMER_STREAM c
  ON d.customer_id = c.customer_id
  WHEN MATCHED THEN UPDATE SET ...
  WHEN NOT MATCHED THEN INSERT ...;
```

→ Uses a **stream** to capture changes and merge incrementally

### 3. Procedure-Based Task (Complex Logic)
```sql
CREATE OR REPLACE TASK RUN_COMPLEX_ETL
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = 'USING CRON 0 3 * * * UTC'
  AS
  CALL ETL_MAIN_PROCEDURE();
```

→ Calls a **stored procedure** containing multi-step logic

### 4. Dependent Multi-Step Workflow
```sql
-- Master coordinate task
CREATE OR REPLACE TASK ORCHESTRATE_ETL
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = 'USING CRON 0 1 * * * UTC'
  AS
  SELECT 'ETL started at ' || CURRENT_TIMESTAMP();

-- Child 1: Load
CREATE OR REPLACE TASK LOAD_DATA
  WAREHOUSE = COMPUTE_WH
  AFTER ORCHESTRATE_ETL
  AS INSERT INTO ... ;

-- Child 2: Transform
CREATE OR REPLACE TASK TRANSFORM_DATA
  WAREHOUSE = COMPUTE_WH
  AFTER LOAD_DATA
  AS INSERT INTO ... ;

-- Child 3: Quality Check
CREATE OR REPLACE TASK VALIDATE_DATA
  WAREHOUSE = COMPUTE_WH
  AFTER TRANSFORM_DATA
  AS CALL RUN_DATA_QUALITY_CHECKS();
```

---

## 🔍 Troubleshooting: Checking Task Errors

When a task fails, use this query to investigate:

```sql
SELECT 
  scheduled_time,
  completed_time,
  state,
  error_code,
  error_message
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
  TASK_NAME => 'DAILY_SALES_ETL'
))
WHERE state = 'FAILED'
ORDER BY scheduled_time DESC
LIMIT 10;
```

**Common failure reasons:**
- Warehouse is SUSPENDED (auto-resume happens, but give it time)
- Permission denied on table/warehouse
- SQL syntax error in the SQL statement
- Insufficient quota (storage, compute)

---

## 💡 Pro Tips for Production Tasks

| Tip | Why It Matters |
|-----|---------------|
| **Test manually first** | Run the SQL outside the task before scheduling |
| **Use stored procedures** | Cleaner, easier to maintain than inline SQL |
| **Monitor TASK_HISTORY regularly** | Catch failures early |
| **Set appropriate warehouse** | Use a static warehouse, not dynamic clusters |
| **Document your DAG** | If you have 10+ tasks, maintain a diagram |
| **Handle idempotency** | Task may retry; ensure INSERT/MERGE can be re-run safely |
| **Use AFTER sparingly** | Deep chains (>5 tasks) get hard to debug |

---

## 🧩 Common Questions About Tasks

**Q: Can a task call another task directly?**
→ No. Only indirect dependency via `AFTER` clause.

**Q: What if a parent task fails?**
→ Child tasks won't run. The entire DAG stops.

**Q: Can multiple tasks depend on one parent?**
→ Yes! That creates a branching DAG (fan-out pattern).

**Q: Can I change the schedule of a running task?**
→ Yes, use `ALTER TASK task_name SET SCHEDULE = '...'`

**Q: Can I edit the SQL inside a task?**
→ Yes, but it requires recreating the task:
```sql
ALTER TASK task_name SET AS <new_sql>;
```

**Q: How many retries if a task fails?**
→ Automatic retry 3 times before marking FAILED.

**Q: Where do I view all my tasks?**
```sql
SHOW TASKS;
SHOW TASKS IN SCHEMA <schema_name>;
```

---

## 📋 Task Lifecycle Checklist

```
1. Write & test SQL (do this in worksheet first!)
2. CREATE TASK ... WITH SCHEDULE ... AS <sql>
3. Task is created in SUSPENDED state
4. ALTER TASK <name> RESUME  (activate it)
5. Monitor via TASK_HISTORY monthly
6. If needed: ALTER TASK <name> SUSPEND (pause)
7. To modify: DROP TASK old_name, then CREATE new one
```

---

## 🏆 Key Takeaway

**Snowflake Tasks = Native ETL Orchestration**

- ✅ Schedule SQL without external tools
- ✅ Chain tasks for complex workflows
- ✅ Monitor & debug using TASK_HISTORY
- ✅ Set it and forget it (mostly)
- ✅ Cost-effective (only compute when running)

Use them for:
- Daily/hourly data loads
- Incremental updates
- Report refresh
- Data quality checks
- Any recurring SQL operation

---

