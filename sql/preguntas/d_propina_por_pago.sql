-- (d) Propina promedio como porcentaje de la tarifa, por tipo de pago, en los dos meses.
-- propina_pct es nula cuando la tarifa es <= 0 (regla R09); avg() ignora esos viajes.
SELECT
    d.anio_mes,
    f.payment_type,
    CASE f.payment_type
        WHEN 0 THEN 'Tarifa flexible'
        WHEN 1 THEN 'Tarjeta de crédito'
        WHEN 2 THEN 'Efectivo'
        WHEN 3 THEN 'Sin cargo'
        WHEN 4 THEN 'Disputa'
        WHEN 5 THEN 'Desconocido'
        WHEN 6 THEN 'Viaje anulado'
    END AS forma_pago,
    count(*) AS viajes,
    round(avg(f.propina_pct), 2) AS propina_promedio_pct
FROM fact_trips f
JOIN dim_date d ON f.fecha = d.fecha
WHERE d.anio_mes IN ('{mes}', '{mes_anterior}')
GROUP BY d.anio_mes, f.payment_type
ORDER BY d.anio_mes DESC, f.payment_type;
