-- (a) Las 10 zonas de origen con más viajes en el mes y su variación contra el mismo mes del año anterior.
-- Se excluyen las zonas 264 (Unknown) y 265 (Outside of NYC): no son un lugar (regla R11).
WITH viajes_por_zona AS (
    SELECT
        a.pu_zone_id,
        sum(a.viajes) FILTER (WHERE d.anio_mes = '{mes}') AS viajes_mes,
        sum(a.viajes) FILTER (WHERE d.anio_mes = '{mes_anterior}') AS viajes_mes_anterior
    FROM agg_zone_hour a
    JOIN dim_date d ON a.fecha = d.fecha
    WHERE a.pu_zone_id NOT IN (264, 265)
    GROUP BY a.pu_zone_id
)
SELECT
    z.zone AS zona_origen,
    z.borough AS barrio,
    v.viajes_mes,
    v.viajes_mes_anterior,
    round(100.0 * (v.viajes_mes - v.viajes_mes_anterior) / v.viajes_mes_anterior, 1) AS variacion_pct
FROM viajes_por_zona v
JOIN dim_zone z ON v.pu_zone_id = z.zone_id
ORDER BY v.viajes_mes DESC
LIMIT 10;
