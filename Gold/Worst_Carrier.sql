-- select * 
-- from shipping_logistic.shipping_gold_schema.shipping_logistic_silver

USE DATABASE shipping_logistic;


-- We are using same calucaltions which use for worst carrier for each hub to find all scores which we need 

--IMP

--You can use TIMESTAMP_DATE Column also in group by if you need to see the worst carrier of each day so you can use TIMESTAMP_DATE Column in group by to group result for each according to each carrier 
-- AS My question is to find the Overa ALL worst carrier i was not including the timestamp column in my grouo by 
CREATE view Worst_Carrier AS (
WITH Total_Time_Per_Hub AS (
    SELECT 
        CARRIER_NAME,
        -- TIMESTAMP_DATE,
        COUNT(shipment_id) AS Total_shipment_of_day,
        COUNT(CASE WHEN delay_profile IN ('major', 'minor') THEN 1 END) AS Total_Delay_Shippments_Of_Day,
        SUM(CASE WHEN TOTAL_TIME > 2 THEN TOTAL_TIME ELSE 0 END) AS Total_Delay_HRS_Of_Day
    FROM shipping_logistic.shipping_gold_schema.shipping_logistic_silver
    GROUP BY CARRIER_NAME
),

Avg_Delay AS (
    SELECT 
        CARRIER_NAME,
        -- TIMESTAMP_DATE,
        Total_shipment_of_day,
        Total_Delay_Shippments_Of_Day,
        Total_Delay_HRS_Of_Day,
        ROUND(Total_Delay_HRS_Of_Day / NULLIF(Total_Delay_Shippments_Of_Day, 0), 2) AS Avg_Delay_Hours_of_day
    FROM Total_Time_Per_Hub
),

Bottelenck_Score AS (
    SELECT 
        CARRIER_NAME,
        -- TIMESTAMP_DATE,
        Total_shipment_of_day,
        Total_Delay_Shippments_Of_Day,
        Total_Delay_HRS_Of_Day,
        Avg_Delay_Hours_of_day,
        (Total_Delay_SHIPPMENTS_OF_DAY) * (AVG_DELAY_HOURS_OF_DAY) AS BOTTELNCK_SCORE
    FROM Avg_Delay
)

-- Here also as we are not fetching worst carrier for each day so we are not using the DAYNAME funtion to fetch the week of day from our date 

SELECT *,
    RANK() OVER (
        PARTITION BY CARRIER_NAME
        ORDER BY BOTTELNCK_SCORE DESC
    ) AS rnk,
    -- DAYNAME(TIMESTAMP_DATE) AS DAY_OF_WEEK
FROM Bottelenck_Score
);



--Here we order by result in desc order in BOTTELNCK_SCORE and using limit to only see the worst carrier 


select * 
from SHIPPING_LOGISTIC.PUBLIC.WORST_CARRIER
where rnk = 1
order by BOTTELNCK_SCORE DESC
limit 1 