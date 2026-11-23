-- Parte 4 de la consigna: capa curada.
-- Una fila por viaje aceptado (trips_validos), con las columnas derivadas y las zonas.
-- La exportación a Parquet particionado por year/month la hace pipeline/exportar.py.
with validos as (
    select * from {{ ref('trips_validos') }}
),

zonas as (
    select * from {{ ref('stg_zonas') }}
)

select
    v.*,

    -- Duración en minutos. Nunca es <= 0: R02 rechaza esas filas.
    (extract(epoch from v.tpep_dropoff_datetime - v.tpep_pickup_datetime) / 60.0)::double precision as duracion_min,

    -- Velocidad promedio en mph. Nula si la distancia es <= 0 (advertencia R03):
    -- un 0 mph sería un dato falso.
    case
        when v.trip_distance > 0
            then (v.trip_distance
                  / (extract(epoch from v.tpep_dropoff_datetime - v.tpep_pickup_datetime) / 3600.0))::double precision
    end as velocidad_mph,

    -- Fecha, hora (0 a 23) y día de la semana ISO (1 lunes ... 7 domingo) de la subida.
    v.tpep_pickup_datetime::date as fecha_subida,
    extract(hour from v.tpep_pickup_datetime)::int as hora_subida,
    extract(isodow from v.tpep_pickup_datetime)::int as dia_semana,

    -- Propina como porcentaje de la tarifa. Nula si la tarifa es <= 0 (advertencia R09).
    case when v.fare_amount > 0 then v.tip_amount / v.fare_amount * 100 end as propina_pct,

    -- Zonas de origen y destino (R07 garantiza que existen).
    zo.borough as pu_borough,
    zo.zone as pu_zone,
    zd.borough as do_borough,
    zd.zone as do_zone

from validos v
left join zonas zo on v.pu_location_id = zo.location_id
left join zonas zd on v.do_location_id = zd.location_id
