# dbt Setup Guide with `uv`

Using `uv` with Python 3.12 is a highly efficient way to manage your dbt environment because `uv` is significantly faster than `pip` and handles virtual environments automatically.

Here is the step-by-step approach to incorporating dbt and the Snowflake adapter using `uv`.

## Step 1: Initialize the Project

Since you have already run `uv init`, you have a `pyproject.toml` file. This file acts as the configuration hub for your project's dependencies.

```powershell
uv init --python 3.12
```

**Explanation:** This ensures your project is explicitly pinned to Python 3.12.

## Step 2: Add dbt-snowflake

Run the following command to add the necessary packages.

```powershell
uv add dbt-snowflake
```

**Explanation:** This command performs three actions at once: it installs `dbt-core`, installs the `dbt-snowflake` adapter, and records both in your `pyproject.toml` file for consistency.

## Step 3: Activate the Environment

`uv` creates its own virtual environment in a folder named `.venv`.

```powershell
.\.venv\Scripts\activate
```

**Explanation:** This enters the isolated "bubble" where your Python 3.12 and dbt tools live. You will see `(.venv)` appear in your terminal prompt.

## Step 4: Initialize the dbt Project structure

Now that the tools are installed, generate the dbt starter files.

```powershell
dbt init airbnb_analytics
```

**Explanation:** This creates the standard dbt folders (`models`, `seeds`, `macros`). Follow the prompts to enter your Snowflake account credentials and warehouse details.

## Step 5: Verify Connectivity

Confirm everything is linked correctly.

```powershell
cd airbnb_analytics
dbt debug
```

**Explanation:** This tests the connection between your local `uv` environment and your Snowflake cloud database.
