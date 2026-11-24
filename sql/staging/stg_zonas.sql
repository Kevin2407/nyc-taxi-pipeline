-- Staging de zonas: 265 filas, una por zona de taxi de la TLC.
select
    location_id::integer as location_id,
    borough,
    zone,
    service_zone
from {{ source('raw', 'zonas') }}
