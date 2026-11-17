-- (c) Porcentaje de viajes del mes con cbd_congestion_fee > 0, y las 5 zonas de origen
-- con mayor proporción de esos viajes. Solo zonas con al menos 1.000 viajes en el mes:
-- con menos, una zona con 1 o 2 viajes aparece con 100 %.
WITH por_zona AS (
    SELECT
        f.pu_zone_id,
        count(*) AS viajes,
        count(*) FILTER (WHERE f.cbd_congestion_fee > 0) AS viajes_con_cbd
    FROM fact_trips f
    JOIN dim_date d ON f.fecha = d.fecha
    WHERE d.anio_mes = '{mes}'
    GROUP BY f.pu_zone_id
),
total_mes AS (
    SELECT round(100.0 * sum(viajes_con_cbd) / sum(viajes), 1) AS pct_mes
    FROM por_zona
)
SELECT
    t.pct_mes AS pct_viajes_con_cbd_en_el_mes,
    z.zone AS zona_origen,
    z.borough AS barrio,
    p.viajes,
    p.viajes_con_cbd,
    round(100.0 * p.viajes_con_cbd / p.viajes, 1) AS pct_zona
FROM por_zona p
JOIN dim_zone z ON p.pu_zone_id = z.zone_id
CROSS JOIN total_mes t
WHERE p.viajes >= 1000
  AND p.pu_zone_id NOT IN (264, 265)
ORDER BY pct_zona DESC, p.viajes DESC
LIMIT 5;
