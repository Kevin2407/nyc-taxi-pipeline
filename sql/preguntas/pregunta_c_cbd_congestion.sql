-- (c) Porcentaje de viajes del mes con cbd_congestion_fee > 0, y las 5 zonas de origen
-- con mayor proporción de esos viajes. Solo zonas con al menos 1.000 viajes en el mes:
-- con menos, una zona con 1 o 2 viajes aparece con 100 %.
with por_zona as (
    select
        f.pu_zone_id,
        count(*) as viajes,
        count(*) filter (where f.cbd_congestion_fee > 0) as viajes_con_cbd
    from {{ ref('fact_trips') }} f
    join {{ ref('dim_date') }} d on f.fecha = d.fecha
    where d.anio_mes = '{{ mes_asignado() }}'
    group by f.pu_zone_id
),
total_mes as (
    select round(100.0 * sum(viajes_con_cbd) / sum(viajes), 1) as pct_mes
    from por_zona
)
select
    t.pct_mes as pct_viajes_con_cbd_en_el_mes,
    z.zone as zona_origen,
    z.borough as barrio,
    p.viajes,
    p.viajes_con_cbd,
    round(100.0 * p.viajes_con_cbd / p.viajes, 1) as pct_zona
from por_zona p
join {{ ref('dim_zone') }} z on p.pu_zone_id = z.zone_id
cross join total_mes t
where p.viajes >= 1000
  and p.pu_zone_id not in (264, 265)
order by pct_zona desc, p.viajes desc
limit 5
