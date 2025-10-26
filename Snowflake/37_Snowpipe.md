- Snowpipe
    - What is it?
    - What is the purpose of it?
    - What problem it solve?
    - Explain the workflow of Snowpipe taking a real case scenario.
    - Snowpipe Demo
        - Show a step by step demo of Snowpipe integration along with S3 configurations needed.
        - Explain notification channel as well.
    - In Snowpipe, snowflake will manage the warehouse.
    - discuss the most important queries/useful syntax regarding Snowpipe that are needed in day 
    to day tasks.
    - How to check for any error in Snowpipe? (For example, using copy history info schema) What is the strategy as snowpipe doesn't through 
    any error or notification in terms of any error.
    - You can't alter the copy command under same pipe object! You have to recreate the pipe object again in order to do that.
    - If you CREATE and replace a snowpipe object again,then you have to also refresh the pipe object metadata. Is there any way to refresh pipe object metadata? (Explain)
    - It is always good practice to have 1 pipe object for one S3 bucket, even if we have multiple pipe obejcts, notification channel will be same. Explain.
    - Suppose we uploaded a file in s3 and snowpipe got triggered and file got loaded in table . Now If we truncate the table and upload file2 in s3 how snowpipe will behave? Will all the files will get laoded again? Or only the latest one? 
    - Snowpipe copies data to the table based on the name of the files but only copy command do that based on the hash value of the files. Explain in details and all the possible scenarios possible here.

-- Tasks in Snowflake
    - What are tasks in snowflake?
    - What are their purpose?
    - What problem they solve?
    - Explain the followings using a real case scenario.
        - create a task
        - schedule a task
        - suspend a task
        - check task history
        - create task workflow
    - Explain the most used tasks variations.
    - Explain task dependency
        - use graph diagram to make things easily understandable.
        - Show real world example to understand it best.


-- Streams in Snowflake
    - What is stream?
    - What is their purpose?
    - What problem it solves?
    - In snowflake, File is written one time (correct me if I am wrong).
        - We can't append/update later. Files have these limitations.
        - When you update a file, old file gets deleted and new file gets created
    - Explain stream object and how it works
         - To monitor these old/new files we can create an object which is called stream object
            - When you define that object, you can capture these changes to the table / in a new table immediately.This process is called changed data capture.
        - stream itself doesn't contain any table data. A stream only stores the offset for the
        source table and returns CDC records by leveraging the versioning history for the source table.
        - There are two types of stream object
            - standard
            - append only
    - Can I say stream objects are like github versions of a file? Correct me if I am wrong!
    - Show a demo using a real life scenario to understand the workflow of stream and offset.
    