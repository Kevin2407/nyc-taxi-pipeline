-- dim_zone: una fila por zona de taxi de la TLC (265 zonas).
select
    location_id as zone_id,
    borough,
    zone,
    service_zone
from {{ ref('stg_zonas') }}
