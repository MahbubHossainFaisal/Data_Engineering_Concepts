- Virtual Warehouse
    - Comes with different sizes (Explain all the sizes available)
    - Servers/clusters (nothing but EC2 machines running in the background)
    - Credits/Hour
    - Credits/Second
    - Notes

- When someone choose 4X-Large Warehouse! What that means?

- What is the credict compute calculation? Explain the complete breakdown in details with latest updated information from Snowflake.

- One person/account can be assigned to one Virtual Warehouse or Viseversa - Both scenarios are possible
    - If many users assigned to same virtual warehouse, Then user's queries will start queuing up.
    In that case, we can enlarge our virtual warehouse server from small to medium and when queries are done,
    we can shrink it to small again. Else, the medium cluster would start adding cost although it is not getting used in the full capacity.
    - another thing which can be done is, instead of enlargening the existing virtual warehouse, we can add similar size multiple warehouses to process n number of user's query. (Multi cluster VWH). Then we can ask snowflake
    to automatically spin it down.
    - Using these ways above, we can solve the problem of queuing up queries while still maintaining a small DWH.

- While creating a new VWH in Snowflake
    - What is Standard vs Snowpar-optimized VWHs?
        - How they are different from each other and what is their individual purpose?
    - Explain the credits for different size options
    - The value of credits can be different based on the Snowflake edition you are using? What's the reason for that?
    - Explain the most important advance options while creating a new warehouse. For example, Auto resume, Auto suspend, multicluster, query acceleration etc.
    - What is auto scaling mode? Explain in detail with proper example.
    - What is maximized mode? Explain in detail with proper example.

- Scaling policy
    - Suppose if clusters are enabled, How many queries does snowflake queues before it spins up additional cluster?
        - Depends on the scaling policy chosen while creating adding multi cluster. (Explain with proper scenario)
            - Standard policy
            - Economy policy
    - What is the trigger to suspend a cluster if no load is present?

