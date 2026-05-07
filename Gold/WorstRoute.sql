--Here we calculating the worst route where the major dark periods are happing to check which route have highest dark period 

WITH Dark_Period AS (
select *,
      ROUND((HOP_DISTANCE_KM)/40) AS Expected_travel_hrs,
      TIMESTAMPDIFF('HOUR', NEXT_SCAN_TIMESTAMP, LEAD(SCAN_TIMESTAMP) OVER (PARTITION BY SHIPMENT_ID ORDER BY SCAN_TIMESTAMP)) AS ACTUAL_TOTAL_TIME
from shipping_logistic.shipping_gold_schema.shipping_logistic_silver

),

DARK_PERIOD_ROUTE AS (
SELECT * ,
ACTUAL_TOTAL_TIME-Expected_travel_hrs AS EXTRA_HRS,
CASE 
    WHEN HOP_DISTANCE_KM = 0 AND PREV_HUB IS NULL
    THEN 'Staring Point'
    when ACTUAL_TOTAL_TIME is null
    THEN 'Final Delivery'
    WHEN HOP_DISTANCE_KM = 0
    THEN 'Same Hub Movement'
    WHEN ACTUAL_TOTAL_TIME > Expected_travel_hrs 
    THEN 'Dark Period'
    ELSE 'Normal'
END AS VISIBILITY_STATUS
FROM Dark_Period 
)

select ORIGIN_HUB,DESTINATION_HUB,count(VISIBILITY_STATUS)
from DARK_PERIOD_ROUTE
WHERE VISIBILITY_STATUS = 'Dark Period'
GROUP by ORIGIN_HUB,DESTINATION_HUB
ORDER BY count(VISIBILITY_STATUS) DESC