-- agg_zone_hour: una fila por zona de origen, fecha y hora de subida.
select
    pu_zone_id,
    fecha,
    hora_subida,
    count(*) as viajes,
    sum(total_amount) as ingreso_total,
    avg(duracion_min) as duracion_media_min
from {{ ref('fact_trips') }}
group by pu_zone_id, fecha, hora_subida
