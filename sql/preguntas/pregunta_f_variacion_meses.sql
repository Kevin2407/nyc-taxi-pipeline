-- (f) Variación de viajes totales y de tarifa media entre el mes y el mismo mes de 2024.
-- Tarifa media sin los viajes con tarifa <= 0 (R09).
with por_mes as (
    select
        d.anio_mes,
        count(*) as viajes,
        avg(f.fare_amount) filter (where f.fare_amount > 0) as tarifa_media
    from {{ ref('fact_trips') }} f
    join {{ ref('dim_date') }} d on f.fecha = d.fecha
    group by d.anio_mes
)
select
    actual.viajes as viajes_mes,
    anterior.viajes as viajes_mes_anterior,
    round(100.0 * (actual.viajes - anterior.viajes) / anterior.viajes, 1) as variacion_viajes_pct,
    round(actual.tarifa_media::numeric, 2) as tarifa_media_mes,
    round(anterior.tarifa_media::numeric, 2) as tarifa_media_mes_anterior,
    round((100.0 * (actual.tarifa_media - anterior.tarifa_media) / anterior.tarifa_media)::numeric, 1) as variacion_tarifa_pct
from por_mes actual
join por_mes anterior
  on actual.anio_mes = '{{ mes_asignado() }}'
 and anterior.anio_mes = '{{ mes_anterior() }}'
