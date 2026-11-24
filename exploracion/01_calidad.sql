-- Exploración 1: reglas de calidad obligatorias sobre los datos crudos (raw.yellow_trips).
-- Cuántas filas viola cada regla en cada mes, antes de decidir severidades.
-- Una fila puede violar varias reglas, así que los porcentajes no se suman.
with zonas as (select location_id from raw.zonas),
viajes as (select * from raw.yellow_trips),
conteos as (
    select
        mes_archivo,
        count(*) as filas,
        count(*) filter (where to_char(tpep_pickup_datetime, 'YYYY-MM') <> mes_archivo) as subida_fuera_del_mes,
        count(*) filter (where tpep_dropoff_datetime <= tpep_pickup_datetime) as bajada_no_posterior,
        count(*) filter (where trip_distance <= 0) as distancia_no_positiva,
        count(*) filter (where total_amount < 0) as total_negativo,
        count(*) filter (where passenger_count is null or passenger_count = 0) as pasajeros_nulo_o_cero,
        count(*) filter (where pu_location_id not in (select location_id from zonas)) as zona_origen_inexistente,
        count(*) filter (where do_location_id not in (select location_id from zonas)) as zona_destino_inexistente
    from viajes
    group by mes_archivo
),
duplicados as (
    select mes_archivo, count(*) - count(distinct (
        vendor_id, tpep_pickup_datetime, tpep_dropoff_datetime, passenger_count, trip_distance,
        ratecode_id, store_and_fwd_flag, pu_location_id, do_location_id, payment_type, fare_amount,
        extra, mta_tax, tip_amount, tolls_amount, improvement_surcharge, total_amount,
        congestion_surcharge, airport_fee, cbd_congestion_fee)) as duplicados_exactos
    from viajes
    group by mes_archivo
)
select c.*, d.duplicados_exactos
from conteos c join duplicados d using (mes_archivo)
order by mes_archivo;
