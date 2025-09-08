- Copy Commmand
    - Validate mode
        - Show the types of Validation_mode in details one by one and their purpose.
        - Instructs the copy command to validate the data files instead of loading them into the specific table.
        - The copy command tests the files for errors but does not load them.
        - The command validates the data to be loaded and returns results based on the validation option specified.
        - Show a complete demo with detailed explanation
        - Basically validation_mode compares the file columns with the DDL of the table! (Am I correct?)

    - File level options
        - Using FILE option, you can load specific files into Snowflake table.
        - ON_ERROR = CONTINUE VS ON_ERROR = ABORT (Explain their need by creating a proper real scenario)
        - Explain the PATTERN option and some common pattern examples of partitioned files to laod through copy command.
        - You can't use negation symbol with FILE option. (Explain in details)

    - ON_ERROR
        - Using this you can easily reject records without failing the copy commands
        - When you are building data pipelines, using this option is a must.
        - You can collect rejected records in a separate table. (Show a complete example)
            - How to get the query id of that operation?
            - How to check for rejected records using query id (Show the full query)?
            - How to make a table out of those rejected records (Show the full query)?
        
    - Enforce and Truncate column options
        - Explain about TRUNCATECOLUNS and the purpose of it in details.
        - Explain about ENFORCE_LENGTH and the purpose of it in detils.
        - Show an example of loading files adding these parameters and explain.
        - If we don't set it, do they set by default?

    - Force Option 
        - What is the purpose of using FORCE option?
        - Explain a scenario by using FORCE and without using FORCE to show what it actually does.
        
    - Purge Option
        - What is the purpose of using PURGE option?
        - Explain a scenario by using PURGE and without using PURGE to show what it actually does.
        
    - Load_History View
        - This information schema view enables you to retrieve the history of data loaded into tables using the
        COPY INTO <table> command. The view displays one row for each file loaded.
        - Snowflake retains historical data for COPY INTO commands executed within the previous 14 days only.
        - What is the purpose of Copy History? What can you do with it?
        - Load_History VS Copy_History (Create a use case scenario to show their purpose and differences)
        - Discuss the important columns of LOAD_HISTORY View
        - Discuss the important columns of COPY_HISTORY View
        - Load History have a constraint of 10000 records and you can travel back 14 days of data
        - Copy History provides more info compared to Load_History.