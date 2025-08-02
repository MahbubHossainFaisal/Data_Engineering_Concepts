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
      