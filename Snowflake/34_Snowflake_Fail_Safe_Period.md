# Snowflake Fail-Safe Period

## What Is This About?

Imagine you've deleted some critical data. Time Travel is Snowflake's first line of defense, letting you recover data for a set period. But what happens after that retention period ends? Fail-Safe is Snowflake's last-resort safety net. It's a 7-day period after Time Travel expires during which Snowflake Support *might* be able to recover your data in a disaster scenario. This guide explains what Fail-Safe is, how it differs from Time Travel, what it costs, and why it's not a substitute for a real backup strategy.

---

## Table of Contents

1. [High-level story: what is Fail-safe and why it exists](#1-high-level-story-what-is-fail-safe-and-why-it-exists)
2. [The exact definition and core rules (the “contract” you must remember)](#2-the-exact-definition-and-core-rules-the-contract-you-must-remember)
3. [Time Travel vs Fail-safe — visualize the lifecycle](#3-time-travel-vs-fail-safe--visualize-the-lifecycle)
4. [Transient & Temporary tables — what changes](#4-transient--temporary-tables--what-changes)
5. [SQL examples — how to create and control retention](#5-sql-examples--how-to-create-and-control-retention)
6. [Relationship between Time Travel retention and Fail-safe — scenarios & examples](#6-relationship-between-time-travel-retention-and-fail-safe--scenarios--examples)
7. [Costs & storage — what you will actually pay for](#7-costs--storage--what-you-will-actually-pay-for)
8. [Is there a size limit for Fail-safe? When could Fail-safe storage grow a lot?](#8-is-there-a-size-limit-for-fail-safe-when-could-fail-safe-storage-grow-a-lot)
9. [Practical advice: when to use permanent vs transient tables (decision checklist)](#9-practical-advice-when-to-use-permanent-vs-transient-tables-decision-checklist)
10. [How to recover data from Fail-safe (process overview)](#10-how-to-recover-data-from-fail-safe-process-overview)
11. [Real-world story (scenario) — to make it stick](#11-real-world-story-scenario--to-make-it-stick)
12. [Operational gotchas & best practices (bullet list)](#12-operational-gotchas--best-practices-bullet-list)
13. [Questions (practice & answers)](#13-questions-practice--answers)
14. [Quick checklist before choosing table type / retention (practical)](#14-quick-checklist-before-choosing-table-type--retention-practical)
15. [Final summary — the must-remember points](#15-final-summary--the-must-remember-points)
16. [References](#16-references)

---

## 1. High-level story: what is Fail-safe and why it exists

Imagine Snowflake stores your data in a fortress. When a row is modified or a table dropped, Snowflake keeps a *recent history* (Time Travel) so you — the user — can rewind mistakes. But what if something catastrophic happens (very rare): a major internal system failure, corruption, or operator error that Time Travel can’t handle? Snowflake keeps a final safety buffer called **Fail-safe** — a short, non-configurable window during which Snowflake **may** recover your historical data *internally* (via Snowflake Support) on a best-effort basis. It’s not an extension of Time Travel for you to query; it’s an emergency recovery mechanism. ([Snowflake Docs][1])

---

## 2. The exact definition and core rules (the “contract” you must remember)

1. **Fail-safe is a Snowflake-managed, non-configurable period (7 days)** that immediately follows the end of an object’s Time Travel retention window. During Fail-safe Snowflake can attempt recovery, but regular Time Travel operations (SELECT AT, UNDROP, CLONE FROM ...) are no longer available to users. Recovery occurs only via Snowflake support and can take hours to days. ([Snowflake Docs][1])
2. **It is not a user-accessible backup**: users cannot issue Time Travel queries against data in Fail-safe. It’s for Snowflake’s internal disaster recovery processes only. ([Snowflake Docs][1])
3. **Fail-safe applies only to permanent (standard) objects**. Transient and temporary table types do **not** have a Fail-safe period — once Time Travel expires for these objects, data is purged and cannot be recovered by Snowflake. ([Snowflake Docs][2])
4. **Fail-safe duration is fixed (7 days)** regardless of how long your Time Travel window was. That 7-day Fail-safe starts *after* the Time Travel retention ends. (Time Travel itself is configurable up to the account/edition limits.) ([Snowflake Docs][1])

---

## 3. Time Travel vs Fail-safe — visualize the lifecycle

Think of historical data lifecycle as three zones (left → right):

* **Active data** — current table data.
* **Time Travel zone (user-accessible)** — you can query/clone/restore for `DATA_RETENTION_TIME_IN_DAYS` (configurable; default 1, up to 90 depending on edition). You use `SELECT ... AT (TIMESTAMP)` or `UNDROP`/`CLONE` here.
* **Fail-safe (Snowflake internal)** — a fixed 7-day window AFTER Time Travel; cannot be queried; recovery only by Snowflake support.

So timeline for a permanent table with 1-day Time Travel: Day 0 current → Day 1 user can Time Travel → Days 2–8 in Fail-safe (support recovery only) → then permanently deleted. ([Snowflake Docs][3])

---

## 4. Transient & Temporary tables — what changes

* **Transient tables**: Designed for temporary/transitory data that you still want beyond a session. They *do not* have a Fail-safe period, and Time Travel retention is usually 0 or 1 day (depending on how created). Because they skip Fail-safe, they reduce storage costs but increase risk (no Snowflake recovery after Time Travel expires). Use when recoverability is not required and cost is a concern. ([Snowflake Docs][2])

* **Temporary tables**: Session-scoped (dropped at session end) — also no Fail-safe. Use for per-session scratch space.

**Common wrong assumption corrected**: Some users think Fail-safe is optional to enable per table — it’s not. It’s automatically applied for permanent objects, and absent for transient/temporary tables. ([Snowflake Docs][2])

---

## 5. SQL examples — how to create and control retention

```sql
-- Permanent table with explicit Time Travel retention (days)
CREATE OR REPLACE TABLE sales_permanent (
  id INT,
  amount FLOAT
)
DATA_RETENTION_TIME_IN_DAYS = 7;  -- example, must be within account/edition limits.

-- Transient table (no Fail-safe)
CREATE TRANSIENT TABLE sales_transient (
  id INT,
  amount FLOAT
);
-- Transient table's Time Travel is limited (0 or 1), and it has no Fail-safe.
```

If you later `DROP TABLE sales_permanent;`, for that object:

* For 7 days after the drop you can still Time Travel/UNDROP.
* After those 7 days, the object enters Fail-safe (another fixed 7 days) where only Snowflake support can attempt recovery. After Fail-safe ends, permanent deletion. ([Snowflake Docs][3])

---

## 6. Relationship between Time Travel retention and Fail-safe — scenarios & examples

**Scenario A — short retention (1 day)**

* `DATA_RETENTION_TIME_IN_DAYS = 1` (default for many accounts) → you can Time Travel for 1 day.
* After 1 day, object moves into Fail-safe for **7 days** → recovery possible only by support.
  **Total potential recovery window** = 1 day (user) + 7 days (support) = 8 days (but only first day is user-accessible). ([Snowflake Docs][3])

**Scenario B — extended retention (30 days)**

* `DATA_RETENTION_TIME_IN_DAYS = 30` → user Time Travel for 30 days.
* After those 30 days, object enters Fail-safe for 7 days → support may attempt recovery.
  **Total potential recovery window** = 30 + 7 = 37 days (user only has first 30 days). ([Snowflake Docs][3])

**Scenario C — you shrink retention from 30 → 1 day**

* When you reduce retention, older historical data that falls outside the new retention window is **moved immediately into Fail-safe** (starting the Fail-safe clock for that data). So reducing retention can cause a lot of data to suddenly be moved to Fail-safe. This matters for storage accounting and recovery semantics. ([Snowflake Docs][3])

**Important operational note**: long-running Time Travel queries can *delay* movement into Fail-safe — if a query references older historical versions, Snowflake won’t purge/move that data until the query completes. ([Snowflake Docs][1])

---

## 7. Costs & storage — what you will actually pay for

* **Storage for historical data (Time Travel + Fail-safe)** is visible in the Snowflake UI and counts toward your account's storage costs. Fail-safe historical data is accounted for and billed (i.e., you’re billed for storage used to keep historical data). Use transient tables to avoid Fail-safe storage costs when appropriate. ([Snowflake Docs][4])

* **Shrink retention to save cost?** Be cautious — shrinking retention moves older history to Fail-safe and could temporarily increase Fail-safe storage until it expires. Also, being aggressive with transient tables reduces cost but removes Snowflake recovery options. ([Snowflake Docs][3])

---

## 8. Is there a size limit for Fail-safe? When could Fail-safe storage grow a lot?

* **No documented per-table size cap** on Fail-safe in public Snowflake docs — Fail-safe stores the historical data necessary for recovery. However, moving *lots* of historical data into Fail-safe (for example, by deleting or replacing very large tables, or changing retention windows) will increase your account’s historical storage footprint and thus cost. In practice, Fail-safe storage can be large if you:

  * Run bulk deletes or TRUNCATE on very large permanent tables.
  * Replace large partitions/overwrite large tables frequently.
  * Reduce retention dramatically (e.g., from 90 → 1 day), causing older 89 days of history to move into Fail-safe.
  * Have many large objects with frequent changes (insert/delete/updates) — Time Travel stores the historical change information. ([Snowflake Docs][1])

* **Other factor**: long-running queries prevent the movement of data into Fail-safe — so concurrent large changes plus long-running queries may lead to retained history being larger for longer. ([Snowflake Docs][1])

---

## 9. Practical advice: when to use permanent vs transient tables (decision checklist)

Use **permanent tables** when:

* You need recoverability beyond accidental session mistakes.
* Your data is business-critical and you want support as a last resort.
* You require Time Travel > 0 days and want Snowflake to retain final Fail-safe protection.

Use **transient tables** when:

* Data is strictly transient or reproducible (ETL scratch tables, staging where source can be reloaded).
* You want lower storage costs and are willing to accept irrecoverability after Time Travel expires. ([Snowflake Docs][2])

Also: for very sensitive, long-term backup needs you should still implement your own backup/archival solution (e.g., unload to external cloud storage) — Fail-safe is not intended to replace a backup strategy.

---

## 10. How to recover data from Fail-safe (process overview)

* If you need Fail-safe recovery, you **must** open a Snowflake Support case. Snowflake Support will attempt recovery (this is not instantaneous and is done on a best-effort basis). Expect recovery to take hours to days, and you’ll need ACCOUNTADMIN and follow Snowflake support instructions; recovery is not guaranteed. ([community.snowflake.com][5])

---

## 11. Real-world story (scenario) — to make it stick

You’re at "DataCo" and you run a daily ETL that does `INSERT OVERWRITE` into a 5 TB `orders` permanent table. You set `DATA_RETENTION_TIME_IN_DAYS = 7` because you want to be able to recover a week’s changes.

One day, someone accidentally runs `TRUNCATE TABLE orders;` at 03:00. Because of Time Travel, you can `UNDROP` or query `orders AT (timestamp => '2025-10-12 02:50:00')` and restore the data — painless within 7 days.

Now imagine you had set `DATA_RETENTION_TIME_IN_DAYS = 90`. You discover the mistake after 40 days — Time Travel is gone for the 40th day, but Snowflake still has Fail-safe for 7 days (i.e., days 91–97), so you open a support ticket. Support may be able to recover, but it will take time, and it’s not guaranteed. If `orders` was a transient table instead, it would have been irrecoverable after Time Travel expired. Moral: for critical tables, choose permanent + appropriate retention and also have external backups. ([Snowflake Docs][3])

---

## 12. Operational gotchas & best practices (bullet list)

* **Don’t rely on Fail-safe for routine restores.** Use Time Travel and your own backups for predictable restores. Fail-safe = emergency only. ([Snowflake Docs][1])
* **Choose transient for cheap scratch space**, but automate reproducing data (replayable ETL) because you lose Fail-safe. ([Snowflake Docs][2])
* **Be careful when lowering retention** — it can move large history into Fail-safe and temporarily spike storage usage. ([Snowflake Docs][3])
* **Monitor historical storage in Snowsight** (ACCOUNTADMIN) to see how much data is in Time Travel and Fail-safe and control costs. ([Snowflake Docs][1])
* **Consider cloning and external unload** for long-term archives rather than relying on Fail-safe. ([Snowflake Docs][4])

---

## 13. Questions (practice & answers)

I’ll list the question and a concise answer you should be able to give.

1. **Q:** What is Fail-safe in Snowflake?
   **A:** A 7-day, Snowflake-managed, non-configurable period after Time Travel during which Snowflake can attempt recovery; not user-queryable. ([Snowflake Docs][1])

2. **Q:** Does a transient table have Fail-safe?
   **A:** No — transient and temporary tables do not have Fail-safe; data is purged after Time Travel. ([Snowflake Docs][2])

3. **Q:** If I set `DATA_RETENTION_TIME_IN_DAYS = 30`, how long can I recover data?
   **A:** You can Time Travel yourself for 30 days; after that Snowflake has an additional 7 days of Fail-safe for support recovery (total 37 days potential recovery window). ([Snowflake Docs][3])

4. **Q:** Is Fail-safe the same as a backup?
   **A:** No — Fail-safe is an emergency recovery mechanism, not a replacement for backups or a user-accessible historical store. Use external backups for long-term needs. ([Snowflake Docs][1])

5. **Q:** What happens if I reduce retention from 90 to 1 day?
   **A:** Historical data older than 1 day is moved into Fail-safe immediately and will be recoverable only by support for 7 days. This can temporarily increase Fail-safe storage. ([Snowflake Docs][3])

6. **Q:** How do I get data restored from Fail-safe?
   **A:** Open a Snowflake support case; recovery is performed by Snowflake on a best-effort basis and can take hours–days. ([community.snowflake.com][5])

(You should be able to expand each answer with the lifecycle and examples shown earlier.)

---

## 14. Quick checklist before choosing table type / retention (practical)

* Is the data reproducible from source? → **Yes** → Consider transient + short retention.
* Is the data business-critical and hard/expensive to reproduce? → **Yes** → Permanent + appropriate Time Travel retention.
* Do you need long term archival beyond Time Travel + Fail-safe? → **Yes** → Export/unload to external storage.
* Do you want minimal storage cost and accept irrecoverability? → **Yes** → Use transient or drop retention window. ([Snowflake Docs][2])

---

## 15. Final summary — the must-remember points

* **Fail-safe = 7 days, Snowflake-managed, not user-queryable, only for permanent objects, recovery via support only.** ([Snowflake Docs][1])
* **Transient/temporary tables have no Fail-safe** — choose these when you accept irrecoverability for cost savings. ([Snowflake Docs][2])
* **Time Travel retention (configurable) + 7 days Fail-safe = total potential recovery window**, but only Time Travel is user-accessible. ([Snowflake Docs][3])
* **Be cautious changing retention** — moving data into Fail-safe can temporarily increase storage usage and cost. Monitor Snowsight for historical storage. ([Snowflake Docs][1])

---
## 16. References
[1]: https://docs.snowflake.com/en/user-guide/data-failsafe?utm_source=chatgpt.com "Understanding and viewing Fail-safe"
[2]: https://docs.snowflake.com/en/user-guide/tables-temp-transient?utm_source=chatgpt.com "Working with Temporary and Transient Tables"
[3]: https://docs.snowflake.com/en/user-guide/data-time-travel?utm_source=chatgpt.com "Understanding & using Time Travel"
[4]: https://docs.snowflake.com/en/user-guide/data-cdp-storage-costs?utm_source=chatgpt.com "Storage costs for Time Travel and Fail-safe"
[5]: https://community.snowflake.com/s/article/Fail-safe-data-recovery-steps?utm_source=chatgpt.com "Fail-safe - Data recovery steps"
