create database shipping_logistic

create schema if not exists shipping_logistic.shipping_gold_schema

CREATE TABLE shipping_logistic.shipping_gold_schema.shipping_logistic_silver (
    hub_id STRING,
    shipment_id STRING,
    order_id STRING,
    customer_id STRING,
    carrier_name STRING,
    shipment_type STRING,
    origin_hub STRING,
    destination_hub STRING,
    distance_km FLOAT,
    zone STRING,
    weight_kg FLOAT,
    booking_timestamp TIMESTAMP,
    sla_hours INT,
    expected_delivery_ts TIMESTAMP,
    delay_profile STRING,
    event_id STRING,
    hub_name STRING,
    scan_status STRING,
    scan_timestamp STRING,
    scan_type STRING,
    next_scan_type STRING,
    next_scan_timestamp STRING,
    duration_hours BIGINT,
    timestamp_hour INT,
    timestamp_date DATE,
    Total_hours_delay_hours_per_id DOUBLE,
    primary_hub STRING,
    expected_dwell_hrs BIGINT
);


select * from shipping_logistic.shipping_gold_schema.shipping_logistic_silver

---> External stage 

CREATE OR REPLACE  STORAGE INTEGRATION azure_adls_silver
TYPE = EXTERNAL_STAGE
STORAGE_PROVIDER = 'AZURE'
AZURE_TENANT_ID = '9280c378-4d67-487f-adbe-f260ef8e4341'
ENABLED = TRUE
STORAGE_ALLOWED_LOCATIONS =('azure://shippingdata.blob.core.windows.net/silvershippingdata/silver/shippment_delays') 

DESCRIBE INTEGRATION azure_adls_silver

SHOW STORAGE INTEGRATIONS

CREATE OR ALTER  FILE FORMAT shipping_gold_laye
TYPE = PARQUET 



create or replace stage azure_silver_stage
URL = 'azure://shippingdata.blob.core.windows.net/silvershippingdata/silver/shippment_delays'
STORAGE_INTEGRATION = azure_adls_silver
FILE_FORMAT = shipping_gold_laye



DESCRIBE STAGE azure_silver_stage

DESC INTEGRATION azure_adls_silver;


COPY INTO shipping_logistic.shipping_gold_schema.shipping_logistic_silver
FROM @azure_silver_stage
FILE_FORMAT = shipping_gold_laye
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
PATTERN = '.*\.parquet'




ALTER TABLE shipping_logistic.shipping_gold_schema.shipping_logistic_silver RENAME COLUMN shippment_id TO shipment_id

drop table shipping_logistic.shipping_gold_schema.shipping_logistic_silver
