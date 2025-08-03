- Clustering in Snowflake

- Query processing in Snowflake
    - When you run a query
        - This is submitted to cloud services layer
        - This layer will do optimization to the query, create executions plan and 
        submit that plan to VWH nodes
        - Nodes will first downlaod the table file HEADERs from all the table header files
        (Which stores the metadata information of each micro partitions)
        - Based on the metadata information in the HEADER file, table files (Micro partitions) will be scanned
        - Based on the filter of the query, micro partitioned will be selected and others
        will be pruned 
        - Then the columns we mentioned in our query, those will be fetched from the selected micro partitioned tables and data storage layer will download it. Then data will be processed in DWH layer and sent back to the cloud service layer.
        -Micro-partitioning is automatically performed on all Snowflake tables. Tables are transparently partitioned using the ordering of the data as it is inserted/loaded.
        - Micro-partion size would be under 50-500 MB uncompressed. With compression size
        would be much smaller.
        - The process of grouping records with micro partitioning is called clustering.
        - If we create a cluster key while creating a table? What happens actually?
            - Purpose of it?
            - Benefits it provides?
        - What are micro partitions? Show through an example of a large table breaking
        it into micro partitions
        - Within each micro partition file, teh values of each attribute and column are grouped together and stored independently refered as columnar storage (Explain with proper example)
        - Comlumns here are heavily compressed using PACs or hybrid columnar
        - Each table file will contain a header which will hold the metadata information
        of that table (explain with detailed example)
      

- Concept of Micro Partition depth
    - What is it?
    - What is purpose of it?
    - What benefits it provide?
    - What problem it solve?
    - Example scenario to understand better
    - Types of micro partition depths
    
- Types of clustering we can do
    - Single cluster e.g. -> cluster by (country)
    - Multi cluster e.g. -> cluster by (country, city)
    - Multi cluster (one is a substring) e.g. -> cluster by (country, substring(city,4))
    - Can also use to_date() in your cluster key

- Pre-cautions before applying cluster keys
    - Clustering keys are not intended for all tables
    - The size of the table, as well as the query performance for the table, should dictate whether to define
    a cluster key or not for the table
    - Table has to be large enough to consist of a sufficient large number of micro-partitions, and the colujmns
    defined in the clustering key have to provide sufficient filtering to select a subset of these micro-partitions
    - In general tabes in the multi-terabyte (TB) range will experience the msot benefit from clusternig, 
    particularly if DML is performed regularly/continually on these tables.


- Clustering in depth

- Checking clustering information
    - Explain command for checking clustering information
    - Explain command for checking a willing to create cluster key information that you want to add for a table.
    - How to choose column combinations for clustering? Explain keeping mind of real life scenarios.
    - After applying clustering and loading data into table, then snowflake starts compute and arranging micro partitions which will take some time. For that also snowflake will charge you for the compute and arrangement work
    - If you are sure about the frequent column that are used for filters mostly, while loading data in tables you
    can do an order by with those columns. In that case you would not need clustering and this will fast and save cost of creating clustering. ( If this we can do then why we need clustering to incur more cost? Why not doing it each time instead of creating clustering)
    - Query how to redefine clustering key and recluster to reorganize the micro partitions in the backend.

- How to choose clustering keys
    - Columns which are more often used in the where clause.
    - columns which are more oftent used in join conditions
    - The order you specify while clustering key is important. As general rule, Snowflake recommends ordering
    the columns from lowest cardinality to highest cardinality.
        - What cardinalities are in this context?
        - How to calculate them and order them from lowest to highest
    - Provide real example scenarios to explain why they need to be considerable?