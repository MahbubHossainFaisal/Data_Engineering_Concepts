A scenario -
    - A data analyst has been assigned with a warehouse in snowflake
    - His task is to do query using that warehouse and do data analysis
    - What he does is -> When needed he executes queries, other time he just brainstorm, analyze and invest
    time thought processing from retreived insight of data. In those time, DWH may still running.
    - Snowflake Charges on warehouse open time, either you execute queries in that time or not, it doesn't matter.
    - What we need to identify and represent is how much we are paying Snowflake for that idle time.

- Warehouse Analogy
    - Why it is important to calculate idle time and active time of a warehouse?
        - For cost effectiveness, our main goal of using snowflake DWH is
            - To not over utilize it (leades to increase in cost)
            - To not under utilize it (we are paying but that pay is not worth it)
            - To leveral Snowflake's capability in our advantage.

- A dashboard to monitor Snowflake's warehouse utilization
    - Metadata tables we need for this
        - Warehouse_Metering_History (Explain the columns of this view with their purposes)
        - Query_History (Explain the important columns of this view with their purposes)
        - Warehouse_Event_history (Explain the important columns of this view with their purposes)
        - Also we would need ACCOUNT_ADMIN role to run these views.
        - At last explain how this views combinedly solves our problem of warehouse utilization by creating a proper real case scenario. (Make sure it is detailed and use all the important necessary columns from the views.)
        - You can utilize these metadata and make dashboards for analyzing warehouse idle to and make the best use of snowflake by optimizing cost
        