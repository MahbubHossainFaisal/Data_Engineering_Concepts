- Syntax to create an external table which will take data from s3.
- Why need the concept of external table in Snowflake
    - If we create a view from the s3 files using a stage, for large files and multiples joins
    the view will go to each file and scan them to bring the desired result which is time consuming.
    - The main thing we are missing here is the metadata info .
    - External table fills up this gap
        - It will list all the files that is stored in s3
        - It will record, which files are already present, which are newly added, which are removed/updated
        - When we will fire the query from snowflake, these metadata information will be looked at by snowflake
        and then it will go the particular files to scan and bring out the result.

    - syntax of checking external table files registration history from snowflake
    - Compare in details like what we are getting and what we are missing in each of this
        - Creating view to query s3 data directly
        - Creating external table to query s3 data directly.

    - When you will add a new file to the S3 bucket
        - you won't be able to see that in external table registry
        - For that you have to refresh that metadata table
        - Syntax for the metadata table refresh.

    - When you delete a file from s3 location
        - you won't be able to see that in external table registry
        - For that you have to refresh that metadata table to update with the latest status
        - Syntax for the metadata table refresh.
        - Now that table will show as unregistered in the table registry
        - Even after deleting the file, if we re query that external table it will still fetch result from cloud services cache layer (Explain in detail)
        - Explain this two scenaios deeply
            - If we delete a file in s3
                - When query will fetch data from cloud storage caching layer
                - When query will directly fetch data from remaining s3 files.
    
    - Update Scenario
        - When you will update a file to the S3 bucket
        - you won't be able to see that in external table registry
        - For that you have to refresh that metadata table
        - Syntax for the metadata table refresh.
        - You will see a status named REGISTERED_UPDATE and hash value of that file will change.
    
    - Partitions in External Tables
        - What is the need of creating partition While querying with external tables on s3 files (Hints. When data volumn or number of files grows at a huge list.)
        - Create an external table with the example of PARTITION BY and explain that
        - Basically to query a particular patterns of files, we need this partition (Am I correct?)
        - Show some other function examples that are important in terms of partitioning  
        - How to query a single file using the filename or file_name_part?

    - How to add partitions manually to an external table
        - What is the purpose of metadata$external_table_partition
        - Can you provide a proper example of Manual Partition on External Tables with proper use case scenario?
        - Operation external table refresh not supported for external tables with user-specified partition - Explain in details

    - Auto refresh external tables
        - Using SQS queue
            - How to configure SQS
                - Explain step by step.
        - Using SNS topic
            - How to configure SNS
                - Explain  step by step


