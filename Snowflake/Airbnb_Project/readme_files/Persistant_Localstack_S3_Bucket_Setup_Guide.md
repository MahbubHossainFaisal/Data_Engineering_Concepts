# 🚀 Guide: Persistent Local S3 with LocalStack & Docker

This setup ensures that your S3 buckets and data engineering files survive computer restarts by bridging your Windows Hard Drive to the Docker Container.

## Step 1: The Project Structure

Create a folder on your Desktop named `aws-project`. Inside it, you must have these 3 files:

- `.env` (The Secrets)
- `docker-compose.yml` (The Infrastructure)
- `users.csv` (The Sample Data)

## Step 2: Configuration Files (Copy & Paste)

### File 1: `.env`

Contains your private LocalStack Auth Token.

```plaintext
LOCALSTACK_AUTH_TOKEN=ls-saGI5564-5538-bUgO-QOmE-YeGEqULE2d17
```

### File 2: `docker-compose.yml`

The blueprint that maps your hard drive (`ls_data`) to the cloud container.

```yaml
services:
  localstack:
    image: localstack/localstack:latest
    container_name: localstack_main
    ports:
      - "127.0.0.1:4566:4566"
    environment:
      - PERSISTENCE=1
      - LOCALSTACK_AUTH_TOKEN=${LOCALSTACK_AUTH_TOKEN}
    volumes:
      - "./ls_data:/var/lib/localstack"
      - "/var/run/docker.sock:/var/run/docker.sock"
```

### File 3: `.gitignore` (Optional but Professional)

Prevents your secrets from being uploaded to GitHub.

```plaintext
.env
ls_data/
```

## Step 3: Execution Commands (The Workflow)

Open your VS Code Terminal inside the `aws-project` folder and run these in order:

### 1. Start the Engine

```bash
docker compose up -d
```

**Note:** A folder named `ls_data` will automatically appear on your Desktop. This is your "Physical Cloud."

### 2. Set Your Identity (Windows CMD format)

```dos
set AWS_ACCESS_KEY_ID=test
set AWS_SECRET_ACCESS_KEY=test
set AWS_DEFAULT_REGION=us-east-1
```

### 3. Create the Permanent Bucket

```bash
aws s3 mb s3://snowflake-data-bucket --endpoint-url=http://localhost:4566
```

### 4. Upload the Data (Ingestion)

```bash
aws s3 cp users.csv s3://snowflake-data-bucket/ --endpoint-url=http://localhost:4566
```

### 5. Verify the Content (Audit)

```bash
aws s3 ls s3://snowflake-data-bucket/ --endpoint-url=http://localhost:4566
```

## Step 4: Maintenance (Shutdown & Restart)

- **To Stop:** `docker compose stop` (This pauses the cloud but keeps the data safe in `ls_data`).
- **To Resume:** `docker compose up -d` (Your bucket and `users.csv` will be exactly where you left them).
- **To Delete Everything:** `docker compose down` (Warning: This removes the container, but your `ls_data` folder still holds the backup).
