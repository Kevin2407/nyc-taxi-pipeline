-- (a) Las 10 zonas de origen con más viajes en el mes y su variación contra el mismo mes de 2024.
-- Se excluyen las zonas 264 (Unknown) y 265 (Outside of NYC): no son un lugar (regla R11).
with viajes_por_zona as (
    select
        a.pu_zone_id,
        sum(a.viajes) filter (where d.anio_mes = '{{ mes_asignado() }}') as viajes_mes,
        sum(a.viajes) filter (where d.anio_mes = '{{ mes_anterior() }}') as viajes_mes_anterior
    from {{ ref('agg_zone_hour') }} a
    join {{ ref('dim_date') }} d on a.fecha = d.fecha
    where a.pu_zone_id not in (264, 265)
    group by a.pu_zone_id
)
select
    z.zone as zona_origen,
    z.borough as barrio,
    v.viajes_mes,
    v.viajes_mes_anterior,
    round(100.0 * (v.viajes_mes - v.viajes_mes_anterior) / v.viajes_mes_anterior, 1) as variacion_pct
from viajes_por_zona v
join {{ ref('dim_zone') }} z on v.pu_zone_id = z.zone_id
order by v.viajes_mes desc nulls last
limit 10
