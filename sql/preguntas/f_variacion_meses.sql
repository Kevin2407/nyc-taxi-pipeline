-- (f) Variación de viajes totales y de tarifa media entre el mes y el mismo mes del año anterior.
-- Tarifa media sin los viajes con tarifa <= 0 (R09).
WITH por_mes AS (
    SELECT
        d.anio_mes,
        count(*) AS viajes,
        avg(f.fare_amount) FILTER (WHERE f.fare_amount > 0) AS tarifa_media
    FROM fact_trips f
    JOIN dim_date d ON f.fecha = d.fecha
    GROUP BY d.anio_mes
)
SELECT
    actual.viajes AS viajes_mes,
    anterior.viajes AS viajes_mes_anterior,
    round(100.0 * (actual.viajes - anterior.viajes) / anterior.viajes, 1) AS variacion_viajes_pct,
    round(actual.tarifa_media, 2) AS tarifa_media_mes,
    round(anterior.tarifa_media, 2) AS tarifa_media_mes_anterior,
    round(100.0 * (actual.tarifa_media - anterior.tarifa_media) / anterior.tarifa_media, 1) AS variacion_tarifa_pct
FROM por_mes actual
JOIN por_mes anterior ON actual.anio_mes = '{mes}' AND anterior.anio_mes = '{mes_anterior}';
