-- Time Travel  
    - What is this feature? Explain with a real scenario.
    - What is table retention period? Explain
        - How to check my table's retention period?
        - We can set the retention period to 0 days also. In that case we won't be able to get a previous table version after updating/deleting.
    - Can I undrop a table/schema/database? Explain
    - If you use CREATE/REPLACE table then you can't time travel. Explain
    - How to see a table that I had before update 5 minutes back?
        - For example, offset => -60*5
    - How to recover a previous table if you by mistake update with. Show example with this feature
    - Time travel best practice
        - Create backup table by travelling to older version of table
        - Truncate production table
        - Insert data from backup table to production table
    
    - How time travel works in Snowflake
        - s3 is a blob storage with a relatively simple HTTP(S)-based PUT/GET/DELETE interface
        - Objects i.e. Files can only be overwritten in full. It is not even possible to append data to the end of a file.
        - S3 does, however suppport GET requests for parts (ranges) of a file.
        - Explain How Snowflake keeps different version of a same file then so that we can traverse back/refer to any previous version?
        - When we delete any table 
            - Does snowflake immediately delete the file too? What happens under the hood?
        - Show a architectural diagram to explain that for having metadata layer, Snowflake is able to time travel to previous older versions and we can refer back to those.

- Clone Feature
    - When we say cloning a table, that means cloning the metadata of that table underline.
    But after cloning, both the tables are independent. Explain this
    - Show a demo of this feature.

- Table Swap property
    - Explain the swap technique
    - How Swap technique works under the hood. Explain in details
    - If even one column of the two tables are different then SWAP is not possible! AM I Correct?
    - Show an example with appropriate syntax.
    - SWAP will swap the metadata of the tables. Explain


- Data Sampling Snowflake
    - Why we need sampling? Explain using a real case scenario.
    - Explain AQP (Approximate Query Processing)
    - Show a demo of how we can do sampling in Snowflake
        - sample system, Seed
        - sample row, seed
    - Sampling method
        - SYSTEM method
            - Explain SYSTEM method like how it works with a scenario
        - BERNOULLI method
            - Explain BERNOULLI method like how it works with a scenario
        - When to use what?
        - Advantage and Disadvantage of these algorithms?
    - Clone VS Sampling
        - How Sampling can be more efficient than clone?
    
- Fail Safe Feature
    - What is it ? What is the purpose of it?
    - Explain each nitty gritty things of it.
    - What is transient table vs permanent table and what is the behavior of fail safe feature on these tables.
    - Why and when should we use it?
    - What consequences we would get?
    - Relation between fail safe and retention period
        - Show an example with different possibilities
    - Is there any size limit in Fail safe zone for tables? When your data size will grow exponentialy in fail safe zone?
    - Explain if there is anything to consider regarding fail safe zone storage?

- Table types in Snowflake (Explain each of their purpose and use case with scenario)
    - Permanent
    - Transient
    - Temporary
    - Explain their purpose, pros and cons.
    - Explain their retention period and fail safe period
    - Why a permanent table directly don't enter into fail safe but take some time to enter after dropping.
    - Can we create transient schema and database? What is their purpose then?
