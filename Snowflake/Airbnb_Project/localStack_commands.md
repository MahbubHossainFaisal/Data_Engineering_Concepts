:: =====================================================================
:: LOCALSTACK DATA ENGINEERING WORKFLOW (S3 INGESTION)
:: =====================================================================
:: First in a cmd file use - localstack start -> Which will start the LocalStack server.

:: Then create another cmd and can use below commands 
:: 1. SET IDENTITY: These tell the AWS CLI who is making the request. 
:: Since it's LocalStack, we use "test" for everything.
set AWS_ACCESS_KEY_ID=test
set AWS_SECRET_ACCESS_KEY=test
set AWS_DEFAULT_REGION=us-east-1

:: 2. CREATE STORAGE: The 'mb' (make bucket) command creates the S3 bucket.
:: Note: We use hyphens (-) because underscores (_) are illegal in S3 names.
:: The --endpoint-url tells the CLI to talk to your PC (LocalStack), not the real internet.
aws s3 mb s3://snowflake-data-bucket --endpoint-url=http://localhost.localstack.cloud:4566

:: 3. NAVIGATE: Change Directory (cd) to the folder where your actual data file lives.
cd Desktop\aws-project

:: 4. INGEST DATA: The 'cp' (copy) command uploads your local CSV into the S3 bucket.
:: This acts as your "Landing Zone" or "Staging Area" for your data pipeline.
aws s3 cp users.csv s3://snowflake-data-bucket/ --endpoint-url=http://localhost.localstack.cloud:4566

:: 5. VERIFY: The 'ls' (list) command checks the contents of the virtual bucket.
:: If you see the filename and size (45 bytes), your data ingestion was successful.
aws s3 ls s3://snowflake-data-bucket/ --endpoint-url=http://localhost.localstack.cloud:4566

:: =====================================================================
:: NOTE: If you stop LocalStack, this bucket will disappear unless you 
:: use a "Persistence" setup (Docker Compose with Volumes).
:: =====================================================================