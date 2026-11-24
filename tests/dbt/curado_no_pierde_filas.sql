{{ config(meta={'dagster': {'ref': {'name': 'trips_curados'}}}) }}
-- La capa curada tiene que tener exactamente las filas aceptadas, mes por mes:
-- si el cruce con zonas perdiera o duplicara filas, este test devuelve el mes y falla.
with validos as (
    select mes_archivo, count(*) as filas from {{ ref('trips_validos') }} group by mes_archivo
),
curados as (
    select mes_archivo, count(*) as filas from {{ ref('trips_curados') }} group by mes_archivo
)
select v.mes_archivo, v.filas as filas_validos, c.filas as filas_curados
from validos v
full join curados c on c.mes_archivo = v.mes_archivo
where v.filas is distinct from c.filas
