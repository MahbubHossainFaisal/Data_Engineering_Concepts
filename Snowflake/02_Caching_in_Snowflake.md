- What happens after firing a query
    - It goes to cloud services layer
        - They do optimization in the query according to need
    - Then it goes to Virtual Warehouse layer
        - Data will be pulled from Storage Layer
        - Data processing will happen in this layer
        - Then processed data will be returned to cloud services layer
    - Remote Disk IO is the data/Storage layer
    - Local Disk IO is Virtual VWH
    - If you run a query first time, It goes to all layers to finally get results
    - But if you run a same query again and again, from the second time -> Cloud service
    layer will use it's caching layer to show the already generated results for the same query before and without using VWH layer and Storage layer it will provide response output. Which will make the query show results much faster and without using compute and storage again. [ I can be wrong here regarding where caching is stored. Is it in cloud storage layer or Virtual Warehouse layer! I am confused or in both.]

    - What happens if we stop cloud services layer caching?

- Snowflake Caching
    - Remote Disk
    - Local Disk Cache
    - Result Cache
    
    - Some clarifications needed regarding
        - Local Disk Cache vs Result Cache
        - What Local disk cache store? with example
        - What Result cache store? with example
        - How Result cache is reducing customer's processing cost?

- Lessions learned from the Architecture and Caching sections
    - You need a VWH to execute queries
    - Always use limit clause with select * from queries to optimize cost.
    - For cost reduction during development activity, we can keep virtual warehouses running/active for longer at least for 15 mins.
    time. Because, if it got suspended all the caching of micro partitioned data present
    in the VWH would be gone. And for a new query, even though it is same like a previous 
    query, data will be fetched from storage layer again which be costlier.
    - Share the VWH when group of users are working on the common tables.
    - Never disable cloud service layer cache 



