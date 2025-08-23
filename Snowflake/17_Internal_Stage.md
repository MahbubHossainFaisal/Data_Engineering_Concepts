Some staging command:

- DESC stage [db_name].external_stages.[stage_name]/ [db_name].internal_stages.[stage_name]
- alter stage [stage_name]
- DESC file format [db_name].file_formats.my_csv_format
- Stage object properties (most important ones)
- File format object properties (most important ones)
- difference between the two objects
- We can't execute GET/PUT command from Snowflake WEB UI.


- Internal Staging area
    - Commands
        - Upload data into internal staging area
        - Download data from internal staging area
        - using table stage and named stage for internal staging area
        - Best practices while using internal staging area.

    - A scenario
        - Have to upload a large file for a table
            - Let's use tabe stage as there is only files for single table
            - Need SnowSQL as file size is huge
            - Prepare put command
            - Prepare copy command
            - Need to create file format object
            



    - Describe all the important and most frequent real case issues that dev might face during these tasks and explain the solution of it. For example,
        - Table stages are created automatically.If a stage is made for one table, it can't be used for another table. is it correct??
        - If I have uploaded staging files in internal storage. But I want only some specific columns from
        those files to my table, How can I do that?
        - If I want to keep a track of the file names that my data are getting loaded from in the table, how to do that while data loading? (metadata$filename, metadata$file_row_number)
        - If you doubt some value of a column that might not similar with the file column value, you can check it by dowloading the file manual. Another efficient way is, you can directly query to compare that with internal table staging area from Snowflake. and what if your table column numbers are not matching with the file, keep that scenario in mind too.
        - What is the purpose of doing split_part while copying files from staging to tables.

    - Download data
        - How to download data using SnowSQL?
        - What is unloading?
        - Can I unload on an existing staging file?
        - Then dowload the data from staging to your local folder using get command.

- Named Stage
    - Where Named stage is needed instead of table stage? Describe a scenario
    - Syntax of creating this stage under internal staging area
    - Load files command
    - Validate files are loaded properly command
    - Inserting data from staging command.
    - What if I want to load specific columns for a table. Not all the columns of a staging file.
    - How can I load the same data into multiple tables? as I want to use different columns from the same file
    to go to different tables.

- In which areas named stage data loading commands are different from table stage commands.
