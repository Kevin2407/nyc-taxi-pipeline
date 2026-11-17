-- dim_date: una fila por día calendario con al menos un viaje en la capa curada.
CREATE OR REPLACE TABLE dim_date AS
SELECT DISTINCT
    fecha_subida AS fecha,
    strftime(fecha_subida, '%Y-%m') AS anio_mes,
    year(fecha_subida) AS anio,
    month(fecha_subida) AS mes,
    day(fecha_subida) AS dia,
    isodow(fecha_subida) AS dia_semana,
    dayname(fecha_subida) AS nombre_dia,
    isodow(fecha_subida) >= 6 AS es_fin_de_semana
FROM read_parquet('{curada}', hive_partitioning = true)
ORDER BY fecha;
