Act as a top tech company DATA Engineering Lead expert in Snowflake. You will teach me about Snowflake Architecture. I will provide you points that you need to discuss. Please discuss those with great details. Explain them like as you are more a story teller who teaches people with great storyline by giving proper scenarios and solutions to those scenarios based on the topic. 

Please reflect on the below rules while replying to my questions.
 **Rules**: 	
 - You have to cover the fundamentals
 - You have to go in detail 	
 - If I didn't add any important topic in my list of topics, also add that details in your response.  	
 - Add questions that are must needed to be interview ready. (But don't mention interview in title of your response)  	
 - Properly validate and verify your response, nothing important should be missed from the discussion. 	
 - Add proper examples where things are a bit complicated to understand to make things easy. 	
 - Remember you are a teacher! So each step of your response should be like proper way of teaching! Apply the best way to teach!  	
 - If the points are unorganized. Please make them organized and explain step by step. 	
 - Teach me like I am a noob student who need great in detail explanation of things. 	
 - Please be intelligent enough to make things easier to understand with proper case scenario and example. 	
 - I want more elaborated, real case scenario example with story based approach to make things easier to grab into memory and learn in a fun way. 	 
 - At last, your goal would be to provide detail in such a way that would clear my fundamentals in Fast API perspective.
 - Don't use complex terms or words while explaining. your task is to make me understand in the simplest but most effective way possible without compromising context.
 possible.    
 
 Respect the factors mentioned above and When you are ready, ask me for the topics!

- Snowflake architecture consists of 3 layers
    - Cloud services
    - Virtual Warehouses
    - Data Storage

- Data Storage
    - This layer store all table data and query results

- Virtual warehouses (Muscles of the system)
    - This layer handles query execution within elastic clusters of virtual machines

-  Cloud Servcies (Collection of Services)
    - Manages virtual warehouses
    - Manages Quereis we run on Snowflake
    - Manages Transaction and metadata information
    - Provides acces control, usage statistics and query optimization and other servcies

- Shared Disk Architecture
    - What is it?
    - What is the purpose of it?
    - What problem it solves?
    - Where it is needed?
    - Major problems with this architecture
        - Scalability is limited
        - Hard to maintain data consistency accross the cluster
        - Bottleneck of communication with shared disk.

- Shared Nothing Architecture
    - It solves the major problems of Shared disk architecture (Explain how)
    - It scales processing and compute together which eliminates bottlenecks of communication with a shared disk
    - It moves data storage closer to the compute
    - It has also problem
        - Data distributed across the cluster requires shuffling between nodes
        - Performance is heavily dependent on how data is distributed across the nodes
        in the system
        - Compute can't be sized independently of storage as they are tightly coupled

        - Hetergeneous workload in homogenous hardware
        - Membership changes
        - Problem with Software Upgrades

- Multi cluster Shared Architecture
    - Cloud servcies layer works as the bridge between data service layer and compute service layer
    - Handles many things like authentication, access control, metadata and storage, query optimization and security
    - Cloud service layer handles how to submit queries to virtual warehouse layer
    to pull respective data from data storage layer
    - As storage is not tied to a particular compute node and compute can be scaled up and
    scaled down easily.

