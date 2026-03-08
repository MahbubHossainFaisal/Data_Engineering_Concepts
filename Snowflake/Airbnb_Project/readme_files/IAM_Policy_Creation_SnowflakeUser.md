# IAM Policy Creation for Snowflake in LocalStack

## Overview

This guide provides a comprehensive walkthrough for setting up **Identity & Access Management (IAM)** in LocalStack to secure your Snowflake data pipeline. By following the Principle of Least Privilege, you'll create a dedicated service account with minimal, specific permissions rather than using master credentials.

---

## Key Concepts

### Principle of Least Privilege (PoLP)

In professional data engineering environments, we never expose "Master" keys. Instead, we:
- Create **specific users** with **specific permissions**
- Grant only the **minimum access** required to perform their tasks
- Enable **granular tracking and control** of data access
- **Revoke access easily** without affecting other services

### IAM Components You'll Create

| Component | What It Is | Why You Need It |
|-----------|-----------|-----------------|
| **Policy** | A JSON "rulebook" defining permissions | Specifies exactly what actions are allowed |
| **User** | A service account identity | Represents Snowflake in your system |
| **Attachment** | Link between user and policy | Grants the user their permissions |
| **Access Keys** | Credentials (ID + Secret) | How Snowflake authenticates itself |

---

## Step-by-Step Setup Guide

### **Step 1: Define the Policy (The "Rulebook")**

The policy is a JSON document that explicitly lists what actions Snowflake is allowed to perform.

**Action:** Create a file named `snowflake_policy.json` in your project folder.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion"
      ],
      "Resource": "arn:aws:s3:::snowflake-bucket/source-data/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::snowflake-bucket"
    }
  ]
}
```

**What Each Permission Does:**

- **`s3:ListBucket`**: Allows Snowflake to "see" and list all files in the bucket
- **`s3:GetObject`**: Allows Snowflake to "read" and retrieve data from files
- **`s3:GetObjectVersion`**: Allows Snowflake to access specific versions of objects
- **Resource `arn:aws:s3:::snowflake-bucket/source-data/*`**: Restricts access to only the `source-data/` folder (the `*` wildcard means all files within it)

**Why This Matters:** By limiting the Resource ARN, Snowflake cannot access other sensitive folders in your S3 bucket, even if it wanted to.

---

### **Step 2: Create the IAM User (The "Identity")**

Now we create a dedicated service account that represents Snowflake in your system.

**Command:**
```bash
aws iam create-user \
  --user-name snowflake_service_user \
  --endpoint-url=http://localhost:4566
```

**Expected Output:**
```json
{
  "User": {
    "Path": "/",
    "UserName": "snowflake_service_user",
    "UserId": "AIDAI######",
    "Arn": "arn:aws:iam::000000000000:user/snowflake_service_user",
    "CreateDate": "2026-03-09T10:00:00.000Z"
  }
}
```

**Why This Step:**
- Creates a **dedicated identity** for Snowflake (not a shared "admin" account)
- Enables **audit trails** to track which service performed which actions
- Allows **instant access revocation** without affecting other users
- Follows security best practices for service-to-service authentication

---

### **Step 3: Register the Policy (The "Document")**

Upload your policy JSON into LocalStack so it becomes an official IAM policy that can be assigned to users.

**Command:**
```bash
aws iam create-policy \
  --policy-name SnowflakeS3ReadPolicy \
  --policy-document file://snowflake_policy.json \
  --endpoint-url=http://localhost:4566
```

**Expected Output:**
```json
{
  "Policy": {
    "PolicyName": "SnowflakeS3ReadPolicy",
    "PolicyId": "ANPA######",
    "Arn": "arn:aws:iam::000000000000:policy/SnowflakeS3ReadPolicy",
    "Path": "/",
    "DefaultVersionId": "v1",
    "AttachmentCount": 0,
    "CreateDate": "2026-03-09T10:01:00.000Z"
  }
}
```

**Key Takeaways:**
- LocalStack converts your JSON file into an **official AWS ARN** (Amazon Resource Name)
- The ARN format is: `arn:aws:iam::000000000000:policy/SnowflakeS3ReadPolicy`
- This ARN will be used in the next step to link the policy to the user

---

### **Step 4: Attach the Policy to the User (The "Handshake")**

Now we connect the user and the policy—giving the user the permissions defined in the rulebook.

**Command:**
```bash
aws iam attach-user-policy \
  --user-name snowflake_service_user \
  --policy-arn arn:aws:iam::000000000000:policy/SnowflakeS3ReadPolicy \
  --endpoint-url=http://localhost:4566
```

**What Happens:**
- No JSON output is returned (this is normal—it just means success)
- The user `snowflake_service_user` now **officially has** the permissions from `SnowflakeS3ReadPolicy`
- The user still cannot log in yet (no credentials exist)

**Why This Step Is Critical:**
- Without this attachment, the policy and user exist separately like two puzzle pieces that don't connect
- This is where **actual security is enforced**—the user can only do what the policy allows

---

### **Step 5: Generate Credentials (The "Keys")**

Finally, we generate the actual login credentials (username + password) that Snowflake will use.

**Command:**
```bash
aws iam create-access-key \
  --user-name snowflake_service_user \
  --endpoint-url=http://localhost:4566
```

**Expected Output:**
```json
{
  "AccessKey": {
    "UserName": "snowflake_service_user",
    "AccessKeyId": "AKIA####################",
    "Status": "Active",
    "SecretAccessKey": "##########+##########/##########",
    "CreateDate": "2026-03-09T10:02:00.000Z"
  }
}
```

**Critical Security Notes:**

- **Save these credentials immediately** — the `SecretAccessKey` cannot be retrieved again
- Store in a secure location (password manager, secrets vault, or `.env` file with `.gitignore`)
- Never commit these credentials to Git
- Treat access keys like passwords — don't share them

**Format for Snowflake Configuration:**
```
Access Key ID:     AKIA####################
Secret Access Key: ##########+##########/##########
```

---

## Complete Summary Table

| Step | Component | Action | Output/Purpose |
|------|-----------|--------|----------------|
| **1** | JSON Policy File | Define permissions | Lists allowed S3 actions and resource paths |
| **2** | IAM User | Create service account | Provides identity: `snowflake_service_user` |
| **3** | IAM Policy | Register rulebook | Creates ARN: `arn:aws:iam::000000000000:policy/SnowflakeS3ReadPolicy` |
| **4** | Attachment | Link user + policy | Grants user the permissions from the policy |
| **5** | Access Keys | Generate credentials | Provides `AccessKeyId` and `SecretAccessKey` for authentication |

---

## Security Checklist

Before using these credentials in Snowflake, verify:

- Policy file is stored in your project directory
- User `snowflake_service_user` was created successfully
- Policy `SnowflakeS3ReadPolicy` was created and shows correct ARN
- Policy is attached to the user (no errors in Step 4)
- Access keys were generated and saved securely
- Credentials are NOT committed to version control

---

## Next Steps

1. **Configure Snowflake** with the generated `AccessKeyId` and `SecretAccessKey`
2. **Test the connection** from Snowflake to LocalStack S3
3. **Verify permissions** by testing that:
   - Snowflake can LIST files in the bucket
   - Snowflake can READ files from `source-data/`
   - Snowflake cannot access files outside `source-data/`
4. **Monitor access** using CloudTrail or LocalStack logs

---

## Troubleshooting

### Access Key Not Working?
- Verify the endpoint URL is correct: `http://localhost:4566`
- Check that LocalStack is running: `docker ps | grep localstack`
- Confirm the user exists: `aws iam get-user --user-name snowflake_service_user --endpoint-url=http://localhost:4566`

### Permission Denied Errors?
- Verify the policy is attached: `aws iam list-attached-user-policies --user-name snowflake_service_user --endpoint-url=http://localhost:4566`
- Check the S3 bucket name matches between policy and actual bucket
- Ensure the path `source-data/*` exists in your S3 bucket

### Lost Your Secret Access Key?
- You must generate a new one with `aws iam create-access-key`
- Delete the old key with `aws iam delete-access-key`

---

## References

- AWS IAM Documentation: https://docs.aws.amazon.com/iam/
- LocalStack IAM Implementation: https://docs.localstack.cloud/services/iam/
- S3 Action Reference: https://docs.aws.amazon.com/IAM/latest/UserGuide/list_amazons3.html
- Principle of Least Privilege: https://en.wikipedia.org/wiki/Principle_of_least_privilege
