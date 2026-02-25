# ❄️ Snowflake Data Sampling — *“The Art of Getting Fast Answers from Big Data”*

---

## 🧩 Part 1: The Core Concepts of Sampling

---

### 🤔 Why Do We Need to Sample Data?

Imagine you're on the data team at **ShopFast**, an e-commerce giant.
You have a massive 3 TB table called `EVENTS` that logs every user click and purchase.

You're asked to:
*   Build a quick dashboard showing daily conversion trends.
*   Provide a dataset for the ML team to experiment with.

The problem? Running a `SELECT COUNT(*)` on a 3 TB table is slow and expensive. You can't wait 10 minutes just to get one number for a prototype.

This is where **Sampling** comes in. Instead of querying the whole table, you query a small, smart subset.

> **Sampling** is the technique of selecting a subset of data from a large table to perform analysis much more quickly and cost-effectively.

It’s a trade-off: you get **speed** and **lower cost** in exchange for a small, manageable amount of **error**.

---

### ⚙️ How Sampling Works Internally (The Two Main Methods)

Snowflake gives you two ways to sample, and they work very differently.

#### 1. `BERNOULLI` (or `ROW`) Sampling — *The Fair Method*
This is the default method. Think of it as **flipping a coin for every single row**.

*   **Mechanism:** Each row has an independent `p/100` probability of being included.
*   **Result:** A true, statistically random, and unbiased sample.
*   **Downside:** Slower, because Snowflake has to look at every row to make a decision.

```sql
-- This gives each row a 10% chance of being selected
SELECT * FROM EVENTS SAMPLE BERNOULLI (10);

-- Shorter syntax (Bernoulli is default)
SELECT * FROM EVENTS SAMPLE (10);
```

#### 2. `SYSTEM` (or `BLOCK`) Sampling — *The Fast Method*
This method is much faster. Instead of flipping a coin for each row, it flips a coin for each **micro-partition** (the underlying 16MB data blocks).

*   **Mechanism:** If a micro-partition is chosen, **all rows** inside it are selected.
*   **Result:** A very fast sample, but it can be biased if your data is clustered (e.g., sorted by date).
*   **Upside:** Often dramatically faster and cheaper for large tables.

```sql
-- This selects 10% of the data blocks, not rows
SELECT * FROM EVENTS SAMPLE SYSTEM (10);
```

---

### ⚖️ Trade-Offs: BERNOULLI vs. SYSTEM

| Method        | Pros                                         | Cons                                                    | Best For...                               |
| ------------- | -------------------------------------------- | ------------------------------------------------------- | ----------------------------------------- |
| **BERNOULLI** | ✅ Unbiased, true random sample              | ❌ Slower, more expensive                               | Statistical analysis, ML model training   |
| **SYSTEM**    | ✅ Much faster, cheaper                      | ⚠️ Can be biased if data is ordered/clustered           | Quick EDA, dashboards, rapid prototyping  |

---

### 💡 Real-World Analogy

Imagine you want to know the most popular pizza topping in a city.

*   **Bernoulli Sampling:** You call thousands of randomly selected people from the phone book. It's slow but very accurate.
*   **System Sampling:** You randomly select 5 pizza restaurants and survey everyone inside them. It's super fast, but you might get a biased result if you accidentally picked 3 vegan restaurants.

---
---

## ⚡ Part 2: Practical Questions & Answers

---

### **1️⃣ What’s the difference between `SAMPLE (10)` and `SAMPLE SYSTEM (10)`?**

✅ **Answer:**
`SAMPLE (10)` uses the default **Bernoulli (row-based)** method, where every row has an independent 10% chance of being selected. It's statistically pure but slower.

`SAMPLE SYSTEM (10)` uses **System (block-based)** sampling, which selects 10% of the micro-partitions. It's much faster but can introduce bias if the data within those blocks isn't random.

| Characteristic | `SAMPLE (10)` | `SAMPLE SYSTEM (10)` |
|----------------|---------------|----------------------|
| **Method**     | Bernoulli (Row) | System (Block)       |
| **Speed**      | Slower        | Faster               |
| **Bias**       | Unbiased      | Potentially Biased   |
| **Default?**   | Yes           | No                   |

---

### **2️⃣ How can you make a sample reproducible for testing?**

✅ **Answer:**
You use the `SEED` (or `REPEATABLE`) keyword. This makes the sample deterministic, meaning you get the same result every time you run it on an unchanged table.

**Crucially, `SEED` only works with `SYSTEM` sampling.**

📘 **Example:**
This query will always return the exact same sample of rows, making it perfect for sharing with teammates or for consistent testing.

```sql
-- Create a reproducible 5% sample for the dev team
CREATE OR REPLACE TABLE DEV.EVENTS_SAMPLE AS
SELECT * FROM PROD.EVENTS SAMPLE SYSTEM (5) SEED (42);
```

---

### **3️⃣ When is it better to use `CLONE` instead of `SAMPLE` for a dev environment?**

✅ **Answer:**
It depends on what you need: **an exact copy** or **a smaller dataset**.

*   Use **`CLONE`** when you need a **full, exact copy** of the production data for debugging or final testing. Cloning is instant and doesn't duplicate storage initially.
*   Use **`SAMPLE`** when you need a **small, lightweight dataset** for rapid development, prototyping, or running quick experiments. A sampled table is physically smaller, so queries on it are faster and cheaper.

| Operation | Use For...                                    | Resulting Data Size |
|-----------|-----------------------------------------------|---------------------|
| **CLONE** | Full fidelity debugging, UAT, backups         | Full (Logical Copy) |
| **SAMPLE**| Rapid prototyping, EDA, initial ML training   | Reduced (Physical Subset) |

---

### **4️⃣ How can you check if `SYSTEM` sampling is creating a biased result?**

✅ **Answer:**
You validate it by comparing key metrics from a `SYSTEM` sample against a `BERNOULLI` sample or the full dataset.

📘 **Example:**
Run these two queries and compare the distributions.

```sql
-- Metric from a fast SYSTEM sample
SELECT EVENT_TYPE, COUNT(*)
FROM EVENTS SAMPLE SYSTEM (1)
GROUP BY 1;

-- Metric from a slower but unbiased BERNOULLI sample
SELECT EVENT_TYPE, COUNT(*)
FROM EVENTS SAMPLE BERNOULLI (1)
GROUP BY 1;
```
If the counts and proportions are wildly different, your `SYSTEM` sample is likely biased due to data clustering in the micro-partitions, and you should probably use `BERNOULLI` for more accurate analysis.

---

### **5️⃣ What is Stratified Sampling and why would you use it?**

✅ **Answer:**
Standard sampling might miss rare categories in your data (e.g., a `country` that only appears in 0.01% of rows). **Stratified Sampling** ensures that every category is represented proportionally in the sample.

You can implement it in Snowflake using window functions.

📘 **Example:**
This query creates a 1% sample, but it takes 1% from *each* `EVENT_TYPE`, guaranteeing none are missed.

```sql
CREATE OR REPLACE TABLE EVENTS_STRATIFIED_SAMPLE AS
SELECT * FROM (
  SELECT
    *,
    ROW_NUMBER() OVER (PARTITION BY EVENT_TYPE ORDER BY RANDOM()) AS rn,
    COUNT(*) OVER (PARTITION BY EVENT_TYPE) AS category_count
  FROM EVENTS
)
WHERE rn <= category_count * 0.01; -- Take 1% from each event_type
```

---

## 🧠 Summary & Key Takeaway

| Feature              | Bernoulli (Row) Sampling              | System (Block) Sampling               |
| -------------------- | ------------------------------------- | ------------------------------------- |
| **Purpose**          | Unbiased statistical accuracy         | Speed and cost-efficiency             |
| **Mechanism**        | Selects individual rows               | Selects entire data blocks            |
| **Reproducible?**    | No                                    | Yes, with `SEED`                      |
| **Use Cases**        | ML Training, Financial Reporting      | Dashboards, EDA, Quick Prototypes     |

---

> ### 🧩 **Key Takeaway Thought**
>
> Snowflake provides a powerful choice between **perfectly accurate but slower** (`BERNOULLI`) sampling and **blazingly fast but potentially biased** (`SYSTEM`) sampling. Understanding this trade-off is the key to performing cost-effective and efficient data analysis on massive datasets. Always choose the right tool for the job.
