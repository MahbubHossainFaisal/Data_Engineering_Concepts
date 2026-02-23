# Loading and Querying XML Data in Snowflake

## What Is This About?

XML is an older data format, but it's still widely used — especially in healthcare (HL7, clinical trial feeds), finance (SWIFT messages), aviation, and government systems. If you work with data from hospitals, labs, insurance companies, or legacy enterprise systems, you'll eventually encounter XML.

Snowflake can load and query XML natively using the same **VARIANT** data type used for JSON. The key difference is that XML requires a few XML-specific functions — particularly `XMLGET()` — to navigate its tag-based structure.

This guide walks you through loading XML, extracting elements and attributes, flattening nested tags into rows, and joining XML data with regular tables.

---

## Table of Contents

1. [Loading XML Data — Step by Step](#1-loading-xml-data--step-by-step)
2. [XMLGET — Extracting Elements from XML](#2-xmlget--extracting-elements-from-xml)
3. [The "$" Syntax — Getting the Text Inside a Tag](#3-the--syntax--getting-the-text-inside-a-tag)
4. [FLATTEN with TO_ARRAY — Expanding Repeating Tags into Rows](#4-flatten-with-to_array--expanding-repeating-tags-into-rows)
5. [Nested FLATTEN — Multi-Level XML](#5-nested-flatten--multi-level-xml)
6. [Working with XML Attributes](#6-working-with-xml-attributes)
7. [Counting Repeated Tags](#7-counting-repeated-tags)
8. [Joining XML Data with Regular Tables](#8-joining-xml-data-with-regular-tables)
9. [Quick Reference](#9-quick-reference)
10. [Common Questions & Answers](#10-common-questions--answers)

---

## 1. Loading XML Data — Step by Step

The process is nearly identical to loading JSON — create a stage, create a table with a VARIANT column, and run COPY INTO with `TYPE = 'XML'`.

### Sample XML File: `patients.xml`

```xml
<patients>
  <patient>
    <id>101</id>
    <name>John Doe</name>
    <visits>
      <visit>
        <date>2024-01-15</date>
        <diagnosis>Fever</diagnosis>
      </visit>
      <visit>
        <date>2024-02-10</date>
        <diagnosis>Cold</diagnosis>
      </visit>
    </visits>
  </patient>
  <patient>
    <id>102</id>
    <name>Jane Smith</name>
    <visits>
      <visit>
        <date>2024-03-05</date>
        <diagnosis>Allergy</diagnosis>
      </visit>
    </visits>
  </patient>
</patients>
```

### Step 1: Create a Stage and Upload

```sql
CREATE OR REPLACE STAGE xml_stage;
```

```bash
PUT file://patients.xml @xml_stage;
```

### Step 2: Create a Table with a VARIANT Column

```sql
CREATE OR REPLACE TABLE patient_xml (
  v VARIANT
);
```

### Step 3: Load the XML

```sql
COPY INTO patient_xml
FROM @xml_stage/patients.xml
FILE_FORMAT = (TYPE = 'XML');
```

### Step 4: View the Raw Data

```sql
SELECT * FROM patient_xml;
```

The entire XML document is now stored as a single VARIANT value. All the nested structure is preserved.

---

## 2. XMLGET — Extracting Elements from XML

With JSON, you access fields using dot notation (`v:name`). With XML, you use the **`XMLGET()`** function instead, because XML's tag-based structure doesn't map directly to dot notation.

### Syntax

```sql
XMLGET(xml_expression, 'tag_name')
```

This returns the child element with that tag name. Think of it as saying: "Go inside this XML node and find the tag called X."

### Example — Get Patient Nodes

```sql
SELECT
  XMLGET(v, 'patient') AS patient_node
FROM patient_xml;
```

This extracts the `<patient>` elements from inside the `<patients>` root. However, this alone doesn't split multiple `<patient>` tags into separate rows — for that, you need FLATTEN (covered in [section 4](#4-flatten-with-to_array--expanding-repeating-tags-into-rows)).

---

## 3. The "$" Syntax — Getting the Text Inside a Tag

When you use `XMLGET()` to get a tag like `<id>101</id>`, the result is the entire XML element (tag + content). To extract just the **text value inside** the tag, you use `:"$"`.

```sql
-- Returns the XML element: <id>101</id>
XMLGET(p.value, 'id')

-- Returns just the text: 101
XMLGET(p.value, 'id'):"$"::STRING
```

The `"$"` represents the text content of the current XML element. The `::STRING` (or `::INT`) casts it to a usable SQL data type.

**This is the pattern you'll use constantly with XML in Snowflake:**

```sql
XMLGET(node, 'tag_name'):"$"::TYPE
```

---

## 4. FLATTEN with TO_ARRAY — Expanding Repeating Tags into Rows

In JSON, arrays are explicit (`[...]`), so FLATTEN can work directly on them. In XML, repeating tags (like multiple `<patient>` elements) aren't wrapped in an array — they're just sibling tags.

To flatten XML, you need an extra step: **wrap the elements in an array first** using `TO_ARRAY()`, then flatten that array.

The pattern:

```sql
LATERAL FLATTEN(TO_ARRAY(XMLGET(v, 'tag_name')))
```

### Example — One Row Per Patient

```sql
SELECT
  XMLGET(p.value, 'id'):"$"::STRING   AS patient_id,
  XMLGET(p.value, 'name'):"$"::STRING AS patient_name
FROM patient_xml,
LATERAL FLATTEN(TO_ARRAY(XMLGET(v, 'patient'))) p;
```

| patient_id | patient_name |
|------------|-------------|
| 101        | John Doe    |
| 102        | Jane Smith  |

**What's happening:**

1. `XMLGET(v, 'patient')` — extracts the `<patient>` elements from the root
2. `TO_ARRAY(...)` — wraps them into an array so FLATTEN can iterate over them
3. `LATERAL FLATTEN(...)` — produces one row per `<patient>` element
4. `p.value` — refers to each individual `<patient>` node
5. `XMLGET(p.value, 'id'):"$"::STRING` — reaches inside each patient and gets the ID text

---

## 5. Nested FLATTEN — Multi-Level XML

Each `<patient>` has a `<visits>` section containing multiple `<visit>` elements. To get one row per visit, you chain multiple FLATTEN calls — just like with nested JSON arrays, but with `TO_ARRAY(XMLGET(...))` at each level.

```sql
SELECT
  XMLGET(p.value, 'id'):"$"::STRING        AS patient_id,
  XMLGET(p.value, 'name'):"$"::STRING      AS patient_name,
  XMLGET(vs.value, 'date'):"$"::STRING     AS visit_date,
  XMLGET(vs.value, 'diagnosis'):"$"::STRING AS diagnosis
FROM patient_xml,
LATERAL FLATTEN(TO_ARRAY(XMLGET(v, 'patient'))) p,
LATERAL FLATTEN(TO_ARRAY(XMLGET(p.value, 'visits'))) v1,
LATERAL FLATTEN(TO_ARRAY(XMLGET(v1.value, 'visit'))) vs;
```

| patient_id | patient_name | visit_date | diagnosis |
|------------|-------------|------------|-----------|
| 101        | John Doe    | 2024-01-15 | Fever     |
| 101        | John Doe    | 2024-02-10 | Cold      |
| 102        | Jane Smith  | 2024-03-05 | Allergy   |

**How the chaining works:**

| Step | What It Does |
|------|-------------|
| `XMLGET(v, 'patient')` → FLATTEN | Expands each `<patient>` into a row |
| `XMLGET(p.value, 'visits')` → FLATTEN | Accesses the `<visits>` wrapper inside each patient |
| `XMLGET(v1.value, 'visit')` → FLATTEN | Expands each `<visit>` inside `<visits>` into a row |
| `XMLGET(vs.value, 'date'):"$"` | Extracts the visit date text |
| `XMLGET(vs.value, 'diagnosis'):"$"` | Extracts the diagnosis text |

The result is a fully relational table — one row per (patient, visit) — ready for joins, aggregations, and dashboards.

---

## 6. Working with XML Attributes

XML elements can have **attributes** — metadata stored inside the opening tag itself. For example:

```xml
<flight id="F101" source="NYC" destination="LON" duration="7h" />
```

Here, `id`, `source`, `destination`, and `duration` are all **attributes** (not child elements).

### Accessing Attributes — Use the `@` Prefix

In Snowflake, attributes are accessed with the `@` prefix:

```sql
SELECT
  f.value:"@id"::STRING          AS flight_id,
  f.value:"@source"::STRING      AS source,
  f.value:"@destination"::STRING AS destination,
  f.value:"@duration"::STRING    AS duration
FROM flight_xml,
LATERAL FLATTEN(TO_ARRAY(XMLGET(flight_data, 'flight'))) f;
```

**The rule:**
- **Child elements** (like `<name>John</name>`) → use `XMLGET(node, 'name'):"$"`
- **Attributes** (like `id="F101"` in the tag) → use `node:"@id"`

You can extract both in the same query:

```sql
SELECT
  emp.value:"@id"::STRING                     AS employee_id,
  XMLGET(emp.value, 'name'):"$"::STRING       AS employee_name,
  XMLGET(emp.value, 'department'):"$"::STRING AS department
FROM employee_xml,
LATERAL FLATTEN(TO_ARRAY(XMLGET(xml_data, 'employee'))) emp;
```

---

## 7. Counting Repeated Tags

To count how many times a tag repeats (e.g., how many `<visit>` elements a patient has), combine `TO_ARRAY()` with `ARRAY_SIZE()`:

```sql
SELECT
  XMLGET(p.value, 'id'):"$"::STRING AS patient_id,
  ARRAY_SIZE(TO_ARRAY(XMLGET(XMLGET(p.value, 'visits'), 'visit'))) AS visit_count
FROM patient_xml,
LATERAL FLATTEN(TO_ARRAY(XMLGET(v, 'patient'))) p;
```

| patient_id | visit_count |
|------------|------------|
| 101        | 2          |
| 102        | 1          |

The pattern is the same as for flattening, but instead of expanding into rows, `ARRAY_SIZE()` just returns the count.

---

## 8. Joining XML Data with Regular Tables

Once you've flattened XML into rows and extracted fields, you can join it with any regular Snowflake table — just like normal SQL.

```sql
SELECT
  d.department_name,
  e.value:"@id"::STRING      AS employee_id,
  XMLGET(e.value, 'name'):"$"::STRING AS employee_name
FROM employee_xml,
LATERAL FLATTEN(TO_ARRAY(XMLGET(xml_data, 'employee'))) e
JOIN department_table d
  ON XMLGET(e.value, 'dept_id'):"$"::STRING = d.department_id;
```

The key: extract the join key from the XML, cast it to the proper type, and join normally. Snowflake treats the flattened XML rows like any other table rows.

---

## 9. Quick Reference

| Concept | What It Does | Syntax |
|---------|-------------|--------|
| **Load XML** | Load an XML file into a VARIANT column | `COPY INTO table FROM @stage FILE_FORMAT = (TYPE = 'XML')` |
| **XMLGET** | Extract a child element by tag name | `XMLGET(node, 'tag_name')` |
| **"$"** | Get the text content inside an XML tag | `XMLGET(node, 'tag'):"$"` |
| **@ prefix** | Access an XML attribute | `node:"@attribute_name"` |
| **TO_ARRAY** | Wrap XML elements into an array (required before FLATTEN) | `TO_ARRAY(XMLGET(node, 'tag'))` |
| **FLATTEN** | Expand repeating tags into rows | `LATERAL FLATTEN(TO_ARRAY(XMLGET(...)))` |
| **Nested FLATTEN** | Handle multi-level nested XML | Chain multiple `LATERAL FLATTEN(TO_ARRAY(...))` |
| **ARRAY_SIZE** | Count repeating tags | `ARRAY_SIZE(TO_ARRAY(XMLGET(node, 'tag')))` |
| **PARSE_XML** | Convert an XML string to VARIANT | `PARSE_XML('<root>...</root>')` |

### Key Differences from JSON Querying

| | JSON | XML |
|---|---|---|
| **Access a field** | `v:fieldname` (dot notation) | `XMLGET(v, 'tagname')` |
| **Get the value** | Already the value | Need `:"$"` to get text content |
| **Access attributes** | N/A (JSON doesn't have attributes) | `node:"@attr"` |
| **Before FLATTEN** | FLATTEN works directly on arrays | Need `TO_ARRAY()` first, then FLATTEN |

---

## 10. Common Questions & Answers

### What does XMLGET return when the tag doesn't exist?

It returns `NULL`. Your query won't fail — the column will just be empty for that row. This is the same behavior as accessing a missing field in JSON.

---

### Why do we need TO_ARRAY() before FLATTEN for XML?

In JSON, arrays are explicit data structures (`[...]`) that FLATTEN understands directly. In XML, repeating sibling tags aren't wrapped in any array — they're just sequential elements. `TO_ARRAY()` converts those siblings into an array that FLATTEN can iterate over.

---

### What's the difference between `:"$"` and `:"@attr"`?

- `:"$"` extracts the **text content** inside an XML tag: `<name>John</name>` → `John`
- `:"@attr"` extracts an **attribute value** from the opening tag: `<flight id="F101">` → `F101`

These are two fundamentally different places XML stores data, so they need different access syntax.

---

### Can I use ARRAY_SIZE to count repeated XML tags?

Yes. Wrap the tags with `TO_ARRAY()` and pass the result to `ARRAY_SIZE()`:

```sql
ARRAY_SIZE(TO_ARRAY(XMLGET(node, 'repeated_tag')))
```

---

### How do I join XML data with regular tables?

Flatten the XML into rows, extract the join key using `XMLGET(...):"$"::TYPE`, and join like normal SQL. Snowflake treats flattened XML rows the same as any other table rows.

---

### Is XML querying slower than JSON in Snowflake?

The underlying VARIANT storage and querying mechanism is the same for both. The main practical difference is that XML queries tend to be more verbose (more `XMLGET` and `TO_ARRAY` calls) compared to JSON's cleaner dot notation. But the performance characteristics are similar — Snowflake stores both in the same optimized binary columnar format.
