
Alter table shipping_logistic.shipping_gold_schema.shipping_logistic_silver
add Column TOTAL_TIME int;


select * 
from shipping_logistic.shipping_gold_schema.shipping_logistic_silver

UPDATE shipping_logistic.shipping_gold_schema.shipping_logistic_silver
SET TOTAL_TIME = (TOTAL_HOURS_DELAY_HOURS_PER_ID - EXPECTED_DWELL_HRS)::INT




select * from shipping_logistic.shipping_gold_schema.shipping_logistic_silver

with Total_Time_Per_Hub AS(
SELECT 
    HUB_NAME,
    TIMESTAMP_DATE,
    COUNT(shipment_id) AS Total_shipment_of_day,
    COUNT(CASE WHEN delay_profile IN ('major', 'minor') THEN 1 END) AS Total_Delay_Shippments_Of_Day,
    SUM(CASE WHEN TOTAL_TIME > 2 THEN TOTAL_TIME ELSE 0 END ) AS Total_Delay_HRS_Of_Day
FROM shipping_logistic.shipping_gold_schema.shipping_logistic_silver
group by HUB_NAME,TIMESTAMP_DATE
)

select 
HUB_NAME,
TIMESTAMP_DATE,
Total_shipment_of_day,
Total_Delay_Shippments_Of_Day,
Total_Delay_HRS_Of_Day,
ROUND(Total_Delay_HRS_Of_Day / NULLIF(Total_Delay_Shippments_Of_Day, 0), 2) AS Avg_Delay_Hours_of_day
from Total_Time_Per_Hub
