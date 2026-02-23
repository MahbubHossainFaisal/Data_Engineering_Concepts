# Loading and Querying Semi-Structured Data in Snowflake

## What Is This About?

Not all data comes in neat rows and columns. APIs return JSON. IoT sensors send nested readings. Mobile apps generate events with varying fields. This kind of data — where the structure isn't fixed — is called **semi-structured data**.

In most databases, handling semi-structured data is painful. You'd have to flatten it outside the database, guess the schema upfront, or store it as a giant text string and parse it every time you query.

Snowflake takes a different approach: it lets you load JSON (and Parquet, Avro, ORC, XML) into a special column type called **VARIANT**, and then query inside it using normal SQL. No pre-processing, no schema design upfront, and surprisingly fast performance.

This guide walks you through loading JSON data, querying nested fields, flattening arrays into rows, and understanding how Snowflake handles it all internally.

---

## Table of Contents

1. [The VARIANT Data Type — A Flexible Container](#1-the-variant-data-type--a-flexible-container)
2. [Loading JSON Data — Step by Step](#2-loading-json-data--step-by-step)
3. [Querying JSON — Dot and Bracket Notation](#3-querying-json--dot-and-bracket-notation)
4. [FLATTEN — Turning Arrays into Rows](#4-flatten--turning-arrays-into-rows)
5. [Nested FLATTEN — Multi-Level Arrays](#5-nested-flatten--multi-level-arrays)
6. [ARRAY_SIZE — Counting Array Elements](#6-array_size--counting-array-elements)
7. [How Snowflake Stores VARIANT Data Internally](#7-how-snowflake-stores-variant-data-internally)
8. [Real-World Use Cases](#8-real-world-use-cases)
9. [Common Questions & Answers](#9-common-questions--answers)

---

## 1. The VARIANT Data Type — A Flexible Container

The **VARIANT** data type is Snowflake's way of storing semi-structured data. Think of it as a flexible container that can hold any structure — objects, arrays, nested hierarchies, numbers, strings — all in a single column.

It supports:

| Format | Example |
|--------|---------|
| **JSON** | API responses, event logs, configuration data |
| **Parquet** | Columnar analytics files from data lakes |
| **Avro** | Streaming data, Kafka messages |
| **ORC** | Hadoop ecosystem files |
| **XML** | Legacy systems, SOAP APIs |

The key idea is **schema-on-read**: you don't define the structure when loading the data. You just dump it into a VARIANT column. When you query it, you decide which fields to extract. This is powerful when the data structure changes frequently (new app versions adding fields, different API responses, etc.).

---

## 2. Loading JSON Data — Step by Step

Let's work through a concrete example. We have a JSON file called `customers.json`:

```json
[
  {
    "id": 1,
    "name": "Alice",
    "age": 30,
    "citiesLived": [
      {"city": "New York", "yearsLived": [2018, 2019, 2020]},
      {"city": "London", "yearsLived": [2021, 2022]}
    ]
  },
  {
    "id": 2,
    "name": "Bob",
    "age": 25,
    "citiesLived": [
      {"city": "Paris", "yearsLived": [2019, 2020]}
    ]
  }
]
```

Notice the complexity: each customer has an array of cities, and each city has its own array of years. This is typical of real-world JSON.

### Step 1: Create a Stage and Upload the File

A stage is a temporary holding area for files before loading.

```sql
CREATE OR REPLACE STAGE my_stage;
```

Upload the file using SnowSQL or AWS CLI:

```bash
PUT file://customers.json @my_stage;
```

### Step 2: Create a Table with a VARIANT Column

You only need **one column** — the VARIANT column stores the entire JSON structure:

```sql
CREATE OR REPLACE TABLE customer_json (
  v VARIANT
);
```

### Step 3: Load the JSON into the Table

```sql
COPY INTO customer_json
FROM @my_stage/customers.json
FILE_FORMAT = (TYPE = 'JSON');
```

### Step 4: Verify the Data

```sql
SELECT * FROM customer_json;
```

Each row in the table is one complete JSON object. The full structure — including nested arrays — is preserved inside the VARIANT column `v`.

---

## 3. Querying JSON — Dot and Bracket Notation

Now that the data is loaded, you can reach inside the JSON and extract specific fields using SQL.

### Extracting Top-Level Fields

Use **colon notation** (`v:fieldname`) to access fields, and `::TYPE` to cast them to the proper SQL data type:

```sql
SELECT
  v:id::INT      AS id,
  v:name::STRING AS name,
  v:age::INT     AS age
FROM customer_json;
```

| id | name  | age |
|----|-------|-----|
| 1  | Alice | 30  |
| 2  | Bob   | 25  |

The `::STRING` and `::INT` casts are important — without them, Snowflake returns the values as VARIANT type, which can behave unexpectedly in comparisons and joins.

### Dot Notation vs Bracket Notation

| Notation | When to Use | Example |
|----------|-------------|---------|
| `v:name` | When the key is a simple name (no spaces, no special characters) | `v:age`, `v:citiesLived` |
| `v['name']` | When the key has spaces, special characters, or starts with a number | `v['employee id']`, `v['1st_name']` |

Both return the same result for simple keys. Use brackets when the key name isn't a clean identifier.

### Accessing Nested Fields and Array Elements

To reach inside nested objects, chain the notation:

```sql
SELECT
  v:id::INT AS id,
  v:citiesLived[0]:city::STRING AS first_city
FROM customer_json;
```

| id | first_city |
|----|-----------|
| 1  | New York  |
| 2  | Paris     |

`[0]` accesses the first element of the `citiesLived` array (arrays are zero-indexed). Then `:city` reaches into that object to get the city name.

---

## 4. FLATTEN — Turning Arrays into Rows

Accessing `[0]`, `[1]`, etc. works for a known number of elements, but what if each customer has a different number of cities? You can't hardcode array indices for every row.

**FLATTEN** solves this. It takes an array and **expands it into multiple rows** — one row per array element. This is the most important function for working with semi-structured data in Snowflake.

### Basic FLATTEN Example

```sql
SELECT
  v:id::INT              AS id,
  c.value:city::STRING   AS city,
  c.value:yearsLived     AS years
FROM customer_json,
LATERAL FLATTEN(input => v:citiesLived) c;
```

| id | city     | years            |
|----|----------|------------------|
| 1  | New York | [2018,2019,2020] |
| 1  | London   | [2021,2022]      |
| 2  | Paris    | [2019,2020]      |

**How to read this:**

- `FLATTEN(input => v:citiesLived)` takes the `citiesLived` array and produces one output row for each element.
- `LATERAL` means the FLATTEN depends on each row from the left-hand table (it "looks sideways" at the current row's data).
- `c` is the alias for the FLATTEN output. Each element is available as `c.value`.
- `c.value:city` reaches into that element (which is a JSON object) and extracts the `city` field.

Alice had 2 cities, so she produces 2 rows. Bob had 1 city, so he produces 1 row.

---

## 5. Nested FLATTEN — Multi-Level Arrays

In our data, each city also has a `yearsLived` array. To get one row per (customer, city, year), you need to flatten **twice** — once for the cities array, and once for the years array inside each city.

```sql
SELECT
  v:id::INT              AS id,
  c.value:city::STRING   AS city,
  y.value::INT           AS year
FROM customer_json,
LATERAL FLATTEN(input => v:citiesLived) c,
LATERAL FLATTEN(input => c.value:yearsLived) y;
```

| id | city     | year |
|----|----------|------|
| 1  | New York | 2018 |
| 1  | New York | 2019 |
| 1  | New York | 2020 |
| 1  | London   | 2021 |
| 1  | London   | 2022 |
| 2  | Paris    | 2019 |
| 2  | Paris    | 2020 |

**What's happening:**

1. The first FLATTEN expands `citiesLived` — one row per city.
2. The second FLATTEN takes each city's `yearsLived` array and expands it — one row per year.
3. The result is a fully flattened, relational-style table that you can aggregate, filter, join, or export.

This pattern — chaining multiple `LATERAL FLATTEN` calls — works for any depth of nesting.

---

## 6. ARRAY_SIZE — Counting Array Elements

Sometimes you don't want to flatten an array — you just want to know **how many elements** it has.

### Count of Top-Level Array Elements

```sql
SELECT
  v:id::INT                    AS id,
  ARRAY_SIZE(v:citiesLived)    AS total_cities
FROM customer_json;
```

| id | total_cities |
|----|-------------|
| 1  | 2           |
| 2  | 1           |

### Count of Nested Array Elements

Combine with FLATTEN to count elements at a deeper level:

```sql
SELECT
  v:id::INT                         AS id,
  c.value:city::STRING              AS city,
  ARRAY_SIZE(c.value:yearsLived)    AS years_count
FROM customer_json,
LATERAL FLATTEN(input => v:citiesLived) c;
```

| id | city     | years_count |
|----|----------|-------------|
| 1  | New York | 3           |
| 1  | London   | 2           |
| 2  | Paris    | 2           |

---

## 7. How Snowflake Stores VARIANT Data Internally

You might wonder: if VARIANT stores arbitrary JSON, doesn't that make queries slow? Surprisingly, no. Snowflake is fast with semi-structured data because of how it handles VARIANT internally.

When you load JSON into a VARIANT column, Snowflake:

1. **Parses the JSON** and converts it into a compressed, binary columnar format — not stored as raw text.
2. **Builds path-based metadata** (internal indexes) so it knows where each nested field lives in the binary data.
3. **Queries specific fields directly** without scanning or parsing the entire JSON each time.

This means when you run:

```sql
SELECT v:citiesLived[0]:city FROM customer_json;
```

Snowflake already knows exactly where that field is in its internal storage. It doesn't re-parse the JSON text — it goes straight to the right bytes.

**The practical takeaway:** Querying specific fields from a VARIANT column is nearly as fast as querying regular structured columns. You don't pay a big performance penalty for using semi-structured data in Snowflake.

---

## 8. Real-World Use Cases

| Scenario | What the Data Looks Like | How Snowflake Helps |
|----------|------------------------|---------------------|
| **API event logs** | JSON with user IDs, timestamps, nested metadata | Store in VARIANT, extract fields like `v:user.id`, `v:event.timestamp` with SQL |
| **IoT sensor data** | Nested arrays of readings per device | FLATTEN the readings array to get one row per (device, reading) |
| **CRM data from APIs** | Customer profiles with nested address lists | FLATTEN addresses, then join with reference tables |
| **Mobile app events** | Varying fields across app versions | Schema-on-read — old events with fewer fields just return NULL for new fields |
| **Data lake integration** | Mix of Parquet and JSON files | Load into VARIANT, extract what you need for dashboards and reports |

---

## 9. Common Questions & Answers

### What is the VARIANT data type?

A flexible column type that can store any semi-structured data (JSON, Parquet, Avro, ORC, XML) without requiring a predefined schema. It's Snowflake's answer to "I don't know the exact structure of my data upfront."

---

### What's the difference between `v:field` and `v['field']`?

Both access the same value. Use dot notation (`v:field`) for simple key names. Use bracket notation (`v['field']`) when the key has spaces, special characters, or starts with a number.

---

### How does FLATTEN work?

It takes a JSON array and produces one output row per element. If a customer has 3 cities in their `citiesLived` array, FLATTEN produces 3 rows for that customer. It's used with `LATERAL` so it can reference the current row's data.

---

### How do I handle arrays inside arrays?

Chain multiple `LATERAL FLATTEN` calls. The first FLATTEN expands the outer array, and the second FLATTEN expands the inner array. You can chain as many levels as needed.

---

### How do I count elements in an array without flattening?

Use `ARRAY_SIZE(v:arrayField)`. It returns the number of elements as an integer.

---

### Why doesn't Snowflake need a schema for JSON data?

Because VARIANT is **schema-on-read**. You load the raw data as-is, and you define which fields to extract at query time. This is ideal when the structure changes frequently — new fields in newer records simply don't exist in older records (they return NULL), and nothing breaks.

---

### Is querying VARIANT data slow compared to regular columns?

No. Snowflake parses VARIANT data into a compressed binary columnar format at load time and builds internal indexes. When you query a specific field, Snowflake goes directly to the right bytes without re-parsing the JSON. Performance is close to querying regular structured columns.

---

### Can I join VARIANT data with regular tables?

Yes. Extract the field you need, cast it to the proper type, and join normally:

```sql
SELECT c.v:id::INT, d.driver_name
FROM customer_json c
JOIN drivers d ON c.v:id::INT = d.customer_id;
```

The key is the `::INT` (or `::STRING`) cast — you need to convert the VARIANT field to a concrete SQL type for joins and comparisons to work correctly.

---

## Quick Reference

| Concept | What It Does | Syntax |
|---------|-------------|--------|
| **VARIANT** | Stores any semi-structured data in one column | `v VARIANT` |
| **Dot notation** | Access a JSON field by name | `v:fieldname` |
| **Bracket notation** | Access a field with special characters in the name | `v['field name']` |
| **Type casting** | Convert VARIANT value to a SQL type | `v:age::INT`, `v:name::STRING` |
| **Array access** | Get a specific element by position (zero-indexed) | `v:array[0]` |
| **FLATTEN** | Expand an array into multiple rows | `LATERAL FLATTEN(input => v:array)` |
| **Nested FLATTEN** | Expand arrays inside arrays | Chain multiple `LATERAL FLATTEN(...)` |
| **ARRAY_SIZE** | Count elements in an array | `ARRAY_SIZE(v:array)` |
| **PARSE_JSON** | Convert a JSON string to VARIANT | `PARSE_JSON('{"key":"value"}')` |
