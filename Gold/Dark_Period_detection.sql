
-- hop_distance_km already hai — 693 km
-- Average truck speed = 40 kmph



-- Kepping the speed as 40 km becasue as realistic to calculate expected_travel_hrs 
-- expected_travel_hrs = hop_distance_km / 40
-- 693 / 40 = 17.3 hrs



WITH Dark_Period AS (
select *,
      ROUND((HOP_DISTANCE_KM)/40) AS Expected_travel_hrs,
      TIMESTAMPDIFF('HOUR', NEXT_SCAN_TIMESTAMP, LEAD(SCAN_TIMESTAMP) OVER (PARTITION BY SHIPMENT_ID ORDER BY SCAN_TIMESTAMP)) AS ACTUAL_TOTAL_TIME,
from shipping_logistic.shipping_gold_schema.shipping_logistic_silver

)

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
 
-- ORDER BY EXTRA_HRS DESC


