1) How would you decide which size of VWH to choose for a new ETL pipeline?

2) Can you explain a situation where a multi-cluster VWH would be better than simply increasing
warehouse size?

3) What is the difference between scaling up and scaling out in Snowflake, and when would you prefer one 
over the other?

4) Imagine your warehouse frequently queues queries during peak hours. Would you recommend changing the warehouse
size or modifying the scaling policy? Why?

5) How does the economy scaling policy help reduce cost, and in what use case would it actually harm performance?

6) If I set min=1 and max=5 in a multi-cluster warehouse with standard policy, can you walk me through what happens
as query load increases and then drops?

7) How does snowflake decides when to pin down a cluster, and how does this differ between standard and economy scaling policies?

8) What risks or costs are associated with using maximized mode in a production environment?

9) You have a warehouse that uses 4x-Large clusters in maximizing mode with min=max=6. What could go wrong in terms of billing if the warehouse is left running.

10) Let's say your snowflake credit usage suddenly spikes. How would you go about investigating if the warehouse configuration is responsible?

11) Can you differentiate between Snowflake's 'standard' and 'snowpark optimized' warehouses in terms of use case?

12) If you have to balance cost-efficiency with acceptable latency for a nightly batch load, what warehouse configuration would you recommend?