-- Reporte de calidad por mes: filas leídas, aceptadas y en cuarentena.
-- Cada número se cuenta en una tabla distinta (staging, válidos, cuarentena):
-- así la reconciliación compara conteos independientes y detecta filas perdidas.
with leidas as (
    select mes_archivo, count(*) as filas from {{ ref('stg_yellow_trips') }} group by mes_archivo
),
aceptadas as (
    select mes_archivo, count(*) as filas from {{ ref('trips_validos') }} group by mes_archivo
),
en_cuarentena as (
    select mes_archivo, count(*) as filas from {{ ref('cuarentena') }} group by mes_archivo
)
select
    l.mes_archivo,
    l.filas as filas_leidas,
    coalesce(a.filas, 0) as filas_aceptadas,
    coalesce(c.filas, 0) as filas_cuarentena,
    round(100.0 * coalesce(c.filas, 0) / l.filas, 2) as pct_cuarentena,
    now() as fecha_hora
from leidas l
left join aceptadas a on a.mes_archivo = l.mes_archivo
left join en_cuarentena c on c.mes_archivo = l.mes_archivo
order by l.mes_archivo
