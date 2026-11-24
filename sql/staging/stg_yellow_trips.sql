-- Staging de viajes: una fila por fila de los archivos, sin filtrar nada.
-- Elige explícitamente las columnas del contrato más las dos de trazabilidad,
-- y deja afuera las columnas internas que pudiera agregar dlt.
select
    vendor_id,
    tpep_pickup_datetime,
    tpep_dropoff_datetime,
    passenger_count,
    trip_distance,
    ratecode_id,
    store_and_fwd_flag,
    pu_location_id,
    do_location_id,
    payment_type,
    fare_amount,
    extra,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    total_amount,
    congestion_surcharge,
    airport_fee,
    cbd_congestion_fee,
    archivo_origen,
    mes_archivo
from {{ source('raw', 'yellow_trips') }}
