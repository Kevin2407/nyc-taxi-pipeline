-- fact_trips: una fila por viaje aceptado por las reglas de calidad.
CREATE OR REPLACE TABLE fact_trips AS
SELECT
    fecha_subida AS fecha,
    hora_subida,
    pu_location_id AS pu_zone_id,
    do_location_id AS do_zone_id,
    payment_type,
    passenger_count,
    trip_distance,
    duracion_min,
    velocidad_mph,
    fare_amount,
    tip_amount,
    propina_pct,
    total_amount,
    cbd_congestion_fee,
    airport_fee,
    flags
FROM read_parquet('{curada}', hive_partitioning = true);
