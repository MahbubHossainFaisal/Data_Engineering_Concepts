- Query Acceleration Service
    - What is Query Acceleration service?
    - What is the purpose of it?
    - What problem it solves
    - What advantage it brings to snowflake?
    - Provide an actual scenario where QAS is needed to feel the problem realistically and explain
    how QAS would solve it.

- Creating warehouse with QAS
    - It is like an option that can be found when creating a warehouse.
    - A way to overcome the problem of queueing of queries
        - Adding multicluster
    - Explain what is horizontal scaling of clusters (Multi-cluster mode on)
        - Purpose
        - Benefits
        - Problems
    - Explain what is vertical scaling of clusters
        - Is it possible? If so, in which way? If not, why?
        - Purpose
        - Benefits
        - Problems

- QAS scale factor?
    - What is it?
    - What is the purpose of it and what problem it resolve?
    - How it works?
    - What advantage it brings up?
    - Provide an actual scenario where QAS scale factor is needed to feel the problem realistically.

- Queries that are eligible for QAS
    - What are the main criterias of a query being eligible to have QAS. Explain with great detail
    - How can we check that eligibility using Snowflake (like checking the possible query completion time and what we are getting currently using estimate query acceleration function and query_acceleration_eligible.)
    - Only the fetch and filtering operations are executed on QAS.
- 