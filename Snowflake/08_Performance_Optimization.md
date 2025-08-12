- Performance Tuning
    - We add indexes, primary keys
    - We create table partitions
    - We analyze query execution plan
    - Remove unnecessary large-table full-table scans
    - Cache small-table full-table scans
    - Verify optimal index usage
    - Using hints to tune Oracle SQL
    - Self-order the table joins

- While in terms of query performance tuning
    - Snowflake query optimizer and virtual warehouse layer already optimize query performance
    - As a developer what is the job then?
        - To be sensible using the tool
            - which helps to reduce processing cost
            - which helps to reduce storage cost
            - Because whatever action you are imposing on Snowflake, it will incur a cost

- A scenario
    - Which query will perform better?
        - Query 01: SELECT * FROM EMP;
        - Query 02: SELECT EMP_NAME, EMP_ADDR FROM EMP;

- Some important ideas for performance tuning
    - If several developers have to use some same schema/tables, they should use the same VWH so that data would be pulled from same local cache which will reduce cost.
    - Order your data by filter columns which you will use most or the columns which you will use frequently for joining during data loading process (which will reduce the need of clustering and save cost)
    - Use multicluster warehouse instead of spinning up existing cluster to bigger size
    - The main goal needs to be reduce the processing + storage cost. (In Snowflake, performance tuning means cost tuning)

- There are some items which Snowflake doesn't use
    - There is no concept of index
    - No concept of primary key, foreign key constraints (The only constraint applicable is not null constraint)
    - No need of transaction management
    - There is no buffer pool
    - You will never encounter out of memory execution

- As there is no transaction management, buffer pool, memory exception, any of the properties of conventional database,
Then how ACID transactions are happening under Snowflake?

- How query optimization works?
    - Query management and optimization
        - When you submit a query this steps happens
            - Parsig
            - Object resolution
            - Access control
            - Plan optimization
            - Once the plan is ready, then this query plan will be submitted to the VWH nodes to process and compute data.
        - Why Snowflake doesn't use Indexes? and if so, How it has overcome the need of indexes?
            - Some reasons for which snowflake doesn't use indexes
                - Storage medium is s3 and data format is compressed files
                - Maintaining indexes significantly increases volume of data and data loading time.
                - User need to explicitly create indexes, which goes against snowflake philosophy of SAS.
                - Maintaining indexes can be complex, expensive and risky process
            - Micro-partitioning is automatically performed on all Snowflake tables. Tables are transparently partitioned using the ordering of the data asa it is inserted/loaded. Additionaly we have metadata headers defining each micro partitions which leverages by VWH and query optimizers to process data by applying techniques like
                - Pruning
                - Zone maps
                - Data Skipping
            - Then we don't need indexes because the way snowflake processes data is completely different than the conventional databases.

- Concurrency control
    - What is ACID transaction?
        - Explain each of the term in depth and proper valid examples.
    - How Snowflake follows this? Show some use cases of Where Snowflake follows ACID principles.
    - Show some important concurrency cases which are important to understand and show how Snowflake reacts in those cases in order to explain how Snowflake does concurrency control.
