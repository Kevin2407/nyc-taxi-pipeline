-- fact_trips: una fila por viaje aceptado por las reglas de calidad.
-- Guarda claves (fecha, zonas, tipo de pago) y medidas; los nombres de zona y los
-- atributos de la fecha viven una sola vez en dim_zone y dim_date.
select
    fecha_subida as fecha,
    hora_subida,
    pu_location_id as pu_zone_id,
    do_location_id as do_zone_id,
    payment_type,
    passenger_count,
    trip_distance,
    duracion_min,
    velocidad_mph,
    fare_amount,
    tip_amount,
    propina_pct,
    total_amount,
    cbd_congestion_fee,
    airport_fee,
    flags
from {{ ref('trips_curados') }}
