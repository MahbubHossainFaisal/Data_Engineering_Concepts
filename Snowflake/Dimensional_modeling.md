Here’s a curated, ordered list of **YouTube video links** you should watch + practice in sequence to master **dimensional modeling (star schema, facts & dims, SCDs, Snowflake/dbt, etc.)**. I also include small hands-on exercises to do right after watching each. Watch + practice = real learning.

---

## 1. Dimensional Modeling / Star Schema Intro

[Dimensional Modeling / Star Schema — Practical Intro (Kimball-style)](https://www.youtube.com/watch?v=dsKnn89gcSE&utm_source=chatgpt.com)
*Exercise:* Take your sample order/order_items dataset and write down the grain; draw a first draft star schema with sales_fact and dims (date, customer, product).

---

## 2. Data Modeling Tutorial: Star Schema (Kimball Approach)

[Data Modeling Tutorial: Star Schema (Kimball Approach)](https://www.youtube.com/watch?v=gRE3E7VUzRU&utm_source=chatgpt.com)
*Exercise:* Convert a simple 3NF ER model (orders, customers, items) into a star schema. Note dimension attributes and fact measures.

---

## 3. Star vs Snowflake Schema — Conceptual Comparison

[Star vs Snowflake schema](https://www.youtube.com/watch?v=huQJnr5bi_Y&utm_source=chatgpt.com)
*Exercise:* For your product dimension, decide if any part should be snowflaked (e.g. category → subcategory), and draw that variant.

---

## 4. Fact Table Types (Transactional / Periodic / Accumulating)

[Fact Types & Grain in Dimensional Modeling](https://www.youtube.com/watch?v=AALj6r-IWfY&utm_source=chatgpt.com)
*Exercise:* For your domain (e-commerce), define which fact types you’d use (e.g. order_line fact, daily summary fact, return accumulations).

---

## 5. Conformed Dimensions & Surrogate Keys

[Conformed Dimensions: Why & How](https://www.youtube.com/watch?v=mK1MKKRmAoA&utm_source=chatgpt.com)
[Surrogate Keys & Natural Keys in Data Modeling](https://www.youtube.com/watch?v=YO58bvr6o-E&utm_source=chatgpt.com)
*Exercise:* Extend your star schema: mark conformed dims and add surrogate key fields (e.g. customer_key). Decide primary key strategy.

---

## 6. Date / Calendar Dimension

[Build a Date Dimension (Calendar) from Scratch](https://www.youtube.com/watch?v=LwT2yrw7uhA&utm_source=chatgpt.com)
*Exercise:* Create a date_dim table (Snowflake DDL) and populate it for multiple years (e.g. 2020–2030). Add useful attributes (is_weekend, month_name, fiscal_period etc.).

---

## 7. Slowly Changing Dimensions: Type 1 & Type 2 (SQL)

[SCD Type 1 & Type 2 Implementation in SQL](https://www.youtube.com/watch?v=kii_Kukh4po&utm_source=chatgpt.com)
*Exercise:* Implement a `dim_customer` SCD2 logic in your Snowflake environment using staging and dimension tables.

---

## 8. dbt Snapshots & SCD Type 2

[dbt Snapshots + SCD Type 2 demo](https://www.youtube.com/watch?v=caR5S07YJ7Y&utm_source=chatgpt.com)
*Exercise:* In a dbt project, define a snapshot for customers; use changed attributes (e.g. address, segment) to version records.

---

## 9. Snowflake & Star Schema Best Practices

[Snowflake & Star Schemas: Design Considerations](https://www.youtube.com/watch?v=qdcBybbUlq8&utm_source=chatgpt.com)
*Exercise:* Design staging → raw → curated layers in Snowflake for your dataset. Create table DDLs and plan clustering or sort keys.

---

## 10. Snowflake Streams & Tasks for Incremental Loads

[Snowflake pipeline patterns: Streams & Tasks](https://www.youtube.com/watch?v=r21LxKeaP8w&utm_source=chatgpt.com)
*Exercise:* Use a staging table with new/changed rows and build a Snowflake stream + task to upsert into curated tables.

---

## 11. Complete dbt Dimensional Modeling Walkthrough

[Creating a Dimensional Model with dbt](https://www.youtube.com/watch?v=p-j-dcmOOqs&utm_source=chatgpt.com)
*Exercise (Final Project):*

* Build staging raw tables (stg_orders, stg_order_items)
* Build `dim_date`, `dim_customer` (SCD2), `dim_product`, `fact_sales`
* Add dbt tests (not_null, unique, relationships)
* Create sample dashboards/queries (monthly revenue, cohort retention, product ranking)

---

## 12. Bonus / Advanced: SCD2 Edge Cases

(Optional) [Advanced SCD patterns & pitfalls](https://www.youtube.com/watch?v=YhjS3Urge9A&utm_source=chatgpt.com)
*Exercise:* Simulate late arriving data, backdated corrections, and design logic for handling them in your SCD2 pipelines.

---
