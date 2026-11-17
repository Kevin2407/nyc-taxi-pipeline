-- dim_zone: una fila por zona de taxi de la TLC (265 zonas).
CREATE OR REPLACE TABLE dim_zone AS
SELECT
    location_id AS zone_id,
    borough,
    zone,
    service_zone
FROM zonas
ORDER BY zone_id;
