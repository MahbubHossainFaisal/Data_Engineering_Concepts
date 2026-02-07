USE DATABASE ECOM_INGESTION_DB;
select * from RAW.CUSTOMERS_BRONZE;
select * from RAW.ORDERS_BRONZE;
select * from RAW.payments_bronze;


select get_ddl('TABLE','RAW.CUSTOMERS_BRONZE')
create or replace TABLE CUSTOMERS_BRONZE (
	CUSTOMER_ID NUMBER(38,0),
	NAME VARCHAR(16777216),
	EMAIL VARCHAR(16777216),
	SIGNUP_DATE VARCHAR(16777216),
	IS_ACTIVE VARCHAR(16777216),
	UPLOAD_TIME TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
);

-- STAGING CUSTOMERS
create or replace TABLE STAGING.STG_CUSTOMERS (
    ROW_ID NUMBER(38,0),
	CUSTOMER_ID NUMBER(38,0),
	NAME VARCHAR(1000),
	EMAIL VARCHAR(1000),
	SIGNUP_DATE DATE,
	IS_ACTIVE VARCHAR(10)
);
insert into staging.stg_customers
select row_number() over(partition by customer_id order by null) as row_id,
customer_id::number as customer_id, case when name is null then SPLIT_PART(email, '@', 1) else name end as name, 
email, COALESCE(
        TRY_TO_DATE(SIGNUP_DATE, 'YYYY-MM-DD'),
        TRY_TO_DATE(SIGNUP_DATE, 'YYYY/MM/DD')
    ) AS SIGNUP_DATE, is_active
from RAW.CUSTOMERS_BRONZE

delete from staging.stg_customers where row_id=2;
select * from staging.stg_customers;
alter table staging.stg_customers drop column row_id;
select * from staging.stg_customers;