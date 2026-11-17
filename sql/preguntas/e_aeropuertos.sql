-- (e) Viajes y tarifa media de los que empiezan o terminan en JFK o LaGuardia,
-- identificados por nombre de zona. Tarifa media sin los viajes con tarifa <= 0 (R09).
SELECT
    d.anio_mes,
    count(*) AS viajes,
    round(avg(f.fare_amount) FILTER (WHERE f.fare_amount > 0), 2) AS tarifa_media
FROM fact_trips f
JOIN dim_date d ON f.fecha = d.fecha
JOIN dim_zone zo ON f.pu_zone_id = zo.zone_id
JOIN dim_zone zd ON f.do_zone_id = zd.zone_id
WHERE d.anio_mes IN ('{mes}', '{mes_anterior}')
  AND (zo.zone IN ('JFK Airport', 'LaGuardia Airport')
       OR zd.zone IN ('JFK Airport', 'LaGuardia Airport'))
GROUP BY d.anio_mes
ORDER BY d.anio_mes DESC;
