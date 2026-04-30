-- TO Calulate the Worst day of Each hub we used first the view to fetch the result which we create earlier in TOTal_TIME_BY EACH HUB Sheet


SELECT * 
FROM SHIPPING_LOGISTIC.PUBLIC.TOTAL_TIME_BY_HUB;

-- Bottlenck score is score we check by multipliying total_delay_shippment_of_day with there avg_delay of day to check is it high because of extra orders or just one order has only one major delay 


WITH Avg_Bottelneck_score AS (
    SELECT
        hub_name,
        TIMESTAMP_DATE,
        DAY_OF_WEEK,
        ROUND(AVG(TOTAL_SHIPMENT_OF_DAY), 2) AS avg_toal_shipment_of_day,
        ROUND(AVG(TOTAL_DELAY_SHIPPMENTS_OF_DAY),2) AS avg_total_delay_shippments_of_day,
        ROUND(AVG(TOTAL_DELAY_HRS_OF_DAY),2) AS avg_total_delay_hrs_of_day,
        ROUND(AVG(AVG_DELAY_HOURS_OF_DAY),2) AS avg_delay_hours_of_day,
        ROUND(AVG(BOTTELNCK_SCORE),2) AS avg_bottelncks_score
    FROM SHIPPING_LOGISTIC.PUBLIC.TOTAL_TIME_BY_HUB
    GROUP BY hub_name, TIMESTAMP_DATE, DAY_OF_WEEK
),

-- Now we give rank to each day according to there avg_bottelnck_score to find the highest score for each hub 
DAYS_RANK AS (
SELECT *,
    RANK() OVER (PARTITION BY HUB_NAME ORDER BY avg_bottelncks_score DESC) AS Rnk
FROM Avg_Bottelneck_score
)

-- Then we filter out only that days where rnk = 1 to find the out the worst day for each hub 
select * 
from DAYS_RANK
where RNK = 1
order by avg_bottelncks_score