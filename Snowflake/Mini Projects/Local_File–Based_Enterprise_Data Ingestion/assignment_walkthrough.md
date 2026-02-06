-- Using Github codespace to upload local files to snowflake using snowsql

- How to load csv from local/github repo to snowflake

-- open codespace and upload the data to github in that codespace.

python3 -m pip install --user snowflake-cli

-- Check version
snow --version

-- Add a new connection 
snow connection add
fill up the inputs and finally done with the connection build up with snowflake

-- Check the available list of connection
snow connection list

-- Test your connection
snow connection test -c data_load_assignment

-- set the connection
snow connection set-default data_load_assignment

-- check query is working or not
snow sql -q "SELECT current_version(), current_warehouse(), current_database();"

-- Create RAW stage under RAW schema. (RAW_STAGE)


-- To reflect the latest repo of github in your local codespace
    - git pull
-- Now upload your assignment data there.
    - snow sql -q "PUT file://$(pwd)/assignment_data/* @RAW_STAGE AUTO_COMPRESS=TRUE;"
    - AUTO_COMPRESS = TRUE is a setting that tells Snowflake to automatically compress your files using gzip before they leave your machine and land in the Stage.

-- Raw file upload done.
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

