{{ config(meta={'dagster': {'ref': {'name': 'agg_zone_hour'}}}) }}
-- La tabla agregada tiene que sumar los mismos viajes e ingresos que fact_trips.
with f as (select count(*) as viajes, round(sum(total_amount)::numeric, 2) as ingreso from {{ ref('fact_trips') }}),
     a as (select sum(viajes) as viajes, round(sum(ingreso_total)::numeric, 2) as ingreso from {{ ref('agg_zone_hour') }})
select f.viajes, a.viajes, f.ingreso, a.ingreso
from f cross join a
where f.viajes <> a.viajes or f.ingreso <> a.ingreso
