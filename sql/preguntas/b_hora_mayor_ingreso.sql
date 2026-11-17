-- (b) La hora del día con mayor ingreso promedio por viaje, en cada uno de los dos meses.
-- Ingreso por viaje = total_amount. Promedio = ingreso total / viajes de esa hora.
SELECT
    d.anio_mes,
    a.hora_subida,
    sum(a.viajes) AS viajes,
    round(sum(a.ingreso_total) / sum(a.viajes), 2) AS ingreso_promedio
FROM agg_zone_hour a
JOIN dim_date d ON a.fecha = d.fecha
WHERE d.anio_mes IN ('{mes}', '{mes_anterior}')
GROUP BY d.anio_mes, a.hora_subida
QUALIFY row_number() OVER (
    PARTITION BY d.anio_mes
    ORDER BY sum(a.ingreso_total) / sum(a.viajes) DESC
) = 1
ORDER BY d.anio_mes DESC;
