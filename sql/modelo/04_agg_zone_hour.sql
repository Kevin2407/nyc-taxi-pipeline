-- agg_zone_hour: una fila por zona de origen, fecha y hora de subida.
CREATE OR REPLACE TABLE agg_zone_hour AS
SELECT
    pu_zone_id,
    fecha,
    hora_subida,
    count(*) AS viajes,
    sum(total_amount) AS ingreso_total,
    avg(duracion_min) AS duracion_media_min
FROM fact_trips
GROUP BY pu_zone_id, fecha, hora_subida
ORDER BY fecha, hora_subida, pu_zone_id;
