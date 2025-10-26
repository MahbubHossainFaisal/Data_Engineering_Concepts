- Inorder to store the semi structured data in snowflake we use VARIANT data type

- Load JSON data
    - Show an entire process of creating a table with a sample JSON data
    - Also show how to get different nested children values by query using different examples
        - Show all the important example that are possible.
    - Explain the flatten function with example and how it helps querying JSON column?
    - Explain a scenario where you will use array_size function in that json column
    - Explain this -> table(flatten(v: citiesLived)) cl -- Higher array
                      table(flatten(cl.value:yearlived)) yl; -- Nested Array
        - Don't have to explain the exact thing but the intution of it by creating a scenario. What this is doing!

- Load XML data
    - Show an entire process of creating a table with a sample XML data
        - Show how to insert that xml data.
        - How to get the root element of that xml data?
        - Explain XMLGET() function with proper scenario case.
        - Explain the LATERAL FLATTEN(to_array (....)) function with proper case scenario to understand what it does.
        - How above can be input of another LATERAL FLATTEN(to_array(....))




