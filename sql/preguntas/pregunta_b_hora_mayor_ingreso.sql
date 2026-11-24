-- (b) La hora del día con mayor ingreso promedio por viaje, en cada uno de los dos meses.
-- Ingreso por viaje = total_amount. Promedio = ingreso total / viajes de esa hora
-- (no promedio de promedios, que daría mal con zonas de distinta cantidad de viajes).
with por_hora as (
    select
        d.anio_mes,
        a.hora_subida,
        sum(a.viajes) as viajes,
        sum(a.ingreso_total) / sum(a.viajes) as ingreso_promedio
    from {{ ref('agg_zone_hour') }} a
    join {{ ref('dim_date') }} d on a.fecha = d.fecha
    where d.anio_mes in ('{{ mes_asignado() }}', '{{ mes_anterior() }}')
    group by d.anio_mes, a.hora_subida
)
-- distinct on se queda con la primera fila de cada mes según el orden: la de mayor ingreso.
select distinct on (anio_mes)
    anio_mes,
    hora_subida,
    viajes,
    round(ingreso_promedio::numeric, 2) as ingreso_promedio
from por_hora
order by anio_mes desc, ingreso_promedio desc
