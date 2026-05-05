--TOTAL SLA BREECH iN ALL SHIPPMENTS ID 

SELECT 
    SHIPMENT_ID,
    EXPECTED_DELIVERY_TS,
    NEXT_SCAN_TYPE,
    NEXT_SCAN_TIMESTAMP,
    CASE
        WHEN EXPECTED_DELIVERY_TS < NEXT_SCAN_TIMESTAMP 
            THEN 'SLA Breach'
        WHEN EXPECTED_DELIVERY_TS > NEXT_SCAN_TIMESTAMP 
            THEN 'SLA Completed'
        ELSE 
            'SLA Met Exactly'
    END AS DELIVERY_SLA

FROM shipping_logistic.shipping_gold_schema.shipping_logistic_silver

WHERE NEXT_SCAN_TYPE = 'DELIVERED'


--SLA BREECH ACCORDING TO THE ZONES TO CHECK WHICH ZONE HAS HIGHEST SLA BREECH SHIPPMENT 

WITH ZONE_BREECH AS(
select SHIPMENT_ID,EXPECTED_DELIVERY_TS,NEXT_SCAN_TIMESTAMP,ZONE,
CASE
        WHEN EXPECTED_DELIVERY_TS < NEXT_SCAN_TIMESTAMP 
            THEN 'SLA Breach'
        WHEN EXPECTED_DELIVERY_TS > NEXT_SCAN_TIMESTAMP 
            THEN 'SLA Completed'
        ELSE 
            'SLA Met Exactly'
    END AS DELIVERY_SLA

from shipping_logistic.shipping_gold_schema.shipping_logistic_silver
WHERE NEXT_SCAN_TYPE = 'DELIVERED'
)

select ZONE,COUNT(*)
from ZONE_BREECH
where DELIVERY_SLA = 'SLA Breach'
group by ZONE


--SLA Breach by Carrier Kaun sa carrier SLA sabse zyada todta hai?
WITH CARRIER_BREECH AS (
SELECT 
    SHIPMENT_ID,
    EXPECTED_DELIVERY_TS,
    NEXT_SCAN_TYPE,
    NEXT_SCAN_TIMESTAMP,
    CARRIER_NAME,
    CASE
        WHEN EXPECTED_DELIVERY_TS < NEXT_SCAN_TIMESTAMP 
            THEN 'SLA Breach'
        WHEN EXPECTED_DELIVERY_TS > NEXT_SCAN_TIMESTAMP 
            THEN 'SLA Completed'
        ELSE 
            'SLA Met Exactly'
    END AS DELIVERY_SLA

FROM shipping_logistic.shipping_gold_schema.shipping_logistic_silver

WHERE NEXT_SCAN_TYPE = 'DELIVERED'
)

select CARRIER_NAME ,COUNT(DELIVERY_SLA)
from CARRIER_BREECH
where DELIVERY_SLA = 'SLA Breach'
group by CARRIER_NAME