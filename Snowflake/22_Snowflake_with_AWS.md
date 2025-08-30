- If we keep S3 bucket in the same region that our Snowflake account is from, we would not incur extra cost.
- S3 policies
    - How to create an IAM policy to connect with Snowflake
    - Show a demo of the policy step by step

- IAM Role
    - How to create a IAM Role for Snowflake (Step by Step)

- Attach the S3 policy to that IAM role.

- Create Snowflake Integration object to make a connection between Snowflake and AWS S3 bucket
    - Show the entire process of creating an integration object with Details
    - More number of S3 path can be added in Integration object?
    - How to get the Snowflake ARN and add that to the Trust Relationship of AWS S3. Explain in details
    - Attach that Snowflake external id as well there.


- Query AWS S3 files from Snowflake
    - Create a file format object
    - Create a stage object
        - Add storage integration to the stage object
        - Add file format object
    - Now you will be able to query the data
        - It would be the same like we did query for our internal stage. 
    
    - Show a complete demo example.
    - What would be the differences of this query and Snowflake's traditional query that we do under Snowflake tables? Explain in details
    - What benefits we would not get in this query than our traditional Snowflake queries?

    - Can you do filters and do joins while querying? Show proper examples.
    - Can we create views? Show proper examples.
    - Can we create tables? Shwo proper examples
    - What would be difference of this view and the table?
    - What would be the advantage of Keeping the data on external storages and query from Snowflake?
    - What would be the disadvantage of the same?
    - When should we do this like to keep data in S3 storage and query directly from Snowflake and when we strictly should prohibits it?
    - We would be able to query only those s3 bucket files, which we have added while making the integration object. Provide detailed explanation.

- Load data from s3 to Snowflake
    - Show an step by step query to load data from S3.
    - on_error = 'CONTINUE'. Explain this.
    - How to capture error data in a seperate staging files?
    - How to handle the data, Suppose I want to continue my loading from S3 also but also want to find the errors and fix them to reinsert again. What is the easiest process?


- Unload data from Snowflake to S3
    - How to unload files from snowflake to S3 (Whole query step by step)
    - What things need to be checked in order to understand that everything unloaded to S3 are exact same and we are not missing anything! How to validate and verify?

- AWS CLI basics
    - How to create AWS CLI configuration?
        - Include also how to create access and secret keys of AWS.
        
    - Checking list of files in a s3 bucekt
    - How to copy files from s3 to my local folder?
    - How to upload files from local to S3 bucket


    - Discuss some most important 25 other command names and their short description on AWS CLI


    - When it is important to use CLI instead of console through web browser?
    - 

- There are two ways of copying in Snowflake
    - Through staging (explain with query example)
    - Direct copy (Explain with query example)
    - Direct Unload (Explain with query example)
    - What is the benefit and disadvantages of Direct copy/unload? Explain in details
    - Is zip compression format copyable in Snowflake?
    - How to copy zip files from s3 to snowflake? Show details with example query
        - What would happen if we want to copy a zip file that has more files under it?
        - What would happen if we want to copy a zip file that has only one file under it? 
        - What we can do in order to solve this problem?


