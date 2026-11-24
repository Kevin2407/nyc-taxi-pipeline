-- Exploración 3: mediciones que justifican los umbrales y las reglas propias.

-- 3.1 Distancia (millas): percentiles, máximo y cuántos viajes superan cada tope (R04).
select
    mes_archivo,
    round(percentile_cont(0.99)   within group (order by trip_distance)::numeric, 1) as p99,
    round(percentile_cont(0.999)  within group (order by trip_distance)::numeric, 1) as p99_9,
    round(percentile_cont(0.9999) within group (order by trip_distance)::numeric, 1) as p99_99,
    max(trip_distance) as maximo,
    count(*) filter (where trip_distance > 50) as mas_de_50,
    count(*) filter (where trip_distance > 100) as mas_de_100,
    count(*) filter (where trip_distance > 1000) as mas_de_1000
from raw.yellow_trips
group by mes_archivo
order by mes_archivo;

-- 3.2 Viajes con distancia <= 0: ¿se cobraron? (R03)
select
    mes_archivo,
    count(*) as distancia_no_positiva,
    count(*) filter (where total_amount > 0) as con_cobro_positivo,
    round(percentile_cont(0.5) within group (order by total_amount)::numeric, 2) as total_mediano
from raw.yellow_trips
where trip_distance <= 0
group by mes_archivo
order by mes_archivo;

-- 3.3 Tarifa base <= 0 por tipo de pago (R09)
select
    mes_archivo,
    payment_type,
    count(*) as tarifa_no_positiva,
    count(*) filter (where total_amount < 0) as con_total_negativo,
    count(*) filter (where total_amount >= 0) as con_total_no_negativo
from raw.yellow_trips
where fare_amount <= 0
group by mes_archivo, payment_type
order by mes_archivo, payment_type;

-- 3.4 Velocidad promedio (mph), sobre viajes con duración y distancia positivas (R10)
with velocidades as (
    select
        mes_archivo,
        trip_distance / (extract(epoch from tpep_dropoff_datetime - tpep_pickup_datetime) / 3600.0) as velocidad
    from raw.yellow_trips
    where tpep_dropoff_datetime > tpep_pickup_datetime and trip_distance > 0
)
select
    mes_archivo,
    round(percentile_cont(0.5)   within group (order by velocidad)::numeric, 1) as mediana,
    round(percentile_cont(0.99)  within group (order by velocidad)::numeric, 1) as p99,
    round(percentile_cont(0.999) within group (order by velocidad)::numeric, 1) as p99_9,
    count(*) filter (where velocidad > 65) as mas_de_65,
    count(*) filter (where velocidad > 80) as mas_de_80,
    count(*) filter (where velocidad > 100) as mas_de_100
from velocidades
group by mes_archivo
order by mes_archivo;

-- 3.5 Bajada anterior o igual a la subida, por tipo de pago (R02)
select
    mes_archivo,
    payment_type,
    count(*) as bajada_no_posterior,
    count(*) filter (where tpep_dropoff_datetime = tpep_pickup_datetime) as misma_hora_exacta
from raw.yellow_trips
where tpep_dropoff_datetime <= tpep_pickup_datetime
group by mes_archivo, payment_type
order by mes_archivo, payment_type;

-- 3.6 Viajes con zona 264 (Unknown) o 265 (Outside of NYC) (R11)
select
    mes_archivo,
    count(*) filter (where pu_location_id in (264, 265)) as origen_desconocido,
    count(*) filter (where do_location_id in (264, 265)) as destino_desconocido,
    count(*) filter (where pu_location_id in (264, 265) or do_location_id in (264, 265)) as alguno
from raw.yellow_trips
group by mes_archivo
order by mes_archivo;
