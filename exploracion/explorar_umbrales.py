"""Mediciones que justifican los umbrales y las reglas propias de calidad.

Se ejecuta desde la raíz del repo:  python exploracion/explorar_umbrales.py
Los resultados están comentados en exploracion/HALLAZGOS.md (sección 5).
"""
import duckdb

ARCHIVOS = {
    "2024-03": "data/raw/yellow/year=2024/month=03/yellow_tripdata_2024-03.parquet",
    "2025-03": "data/raw/yellow/year=2025/month=03/yellow_tripdata_2025-03.parquet",
}

# Velocidad promedio en millas por hora, solo para viajes con duración y distancia positivas.
VELOCIDAD = """
    trip_distance / (date_diff('second', tpep_pickup_datetime, tpep_dropoff_datetime) / 3600.0)
"""

for mes, ruta in ARCHIVOS.items():
    origen = f"read_parquet('{ruta}', hive_partitioning = false)"
    print("=====", mes, "=====")

    print("1) Distancia: percentiles, máximo y cuántos viajes superan cada tope (millas)")
    duckdb.sql(f"""
        SELECT
            round(quantile_cont(trip_distance, 0.99), 1)   AS p99,
            round(quantile_cont(trip_distance, 0.999), 1)  AS p99_9,
            round(quantile_cont(trip_distance, 0.9999), 1) AS p99_99,
            max(trip_distance)                             AS maximo,
            count(*) FILTER (WHERE trip_distance > 50)     AS mas_de_50,
            count(*) FILTER (WHERE trip_distance > 100)    AS mas_de_100,
            count(*) FILTER (WHERE trip_distance > 1000)   AS mas_de_1000
        FROM {origen}
    """).show()

    print("2) Viajes con distancia 0: ¿se cobraron?")
    duckdb.sql(f"""
        SELECT
            count(*)                                  AS distancia_cero,
            count(*) FILTER (WHERE total_amount > 0)  AS con_cobro_positivo,
            round(median(total_amount), 2)            AS total_mediano
        FROM {origen}
        WHERE trip_distance <= 0
    """).show()

    print("3) Tarifa (fare_amount) menor o igual a 0, por tipo de pago")
    duckdb.sql(f"""
        SELECT
            payment_type,
            count(*)                                   AS tarifa_no_positiva,
            count(*) FILTER (WHERE total_amount < 0)   AS con_total_negativo,
            count(*) FILTER (WHERE total_amount >= 0)  AS con_total_no_negativo
        FROM {origen}
        WHERE fare_amount <= 0
        GROUP BY payment_type
        ORDER BY payment_type
    """).show()

    print("4) Velocidad promedio: percentiles y cuántos viajes superan cada tope (mph)")
    duckdb.sql(f"""
        SELECT
            round(quantile_cont(velocidad, 0.5), 1)    AS mediana,
            round(quantile_cont(velocidad, 0.99), 1)   AS p99,
            round(quantile_cont(velocidad, 0.999), 1)  AS p99_9,
            count(*) FILTER (WHERE velocidad > 65)     AS mas_de_65,
            count(*) FILTER (WHERE velocidad > 80)     AS mas_de_80,
            count(*) FILTER (WHERE velocidad > 100)    AS mas_de_100
        FROM (
            SELECT {VELOCIDAD} AS velocidad
            FROM {origen}
            WHERE tpep_dropoff_datetime > tpep_pickup_datetime AND trip_distance > 0
        )
    """).show()

    print("5) Bajada anterior o igual a la subida, por tipo de pago")
    duckdb.sql(f"""
        SELECT
            payment_type,
            count(*) AS bajada_no_posterior,
            count(*) FILTER (WHERE tpep_dropoff_datetime = tpep_pickup_datetime) AS misma_hora_exacta
        FROM {origen}
        WHERE tpep_dropoff_datetime <= tpep_pickup_datetime
        GROUP BY payment_type
        ORDER BY payment_type
    """).show()

    print("6) Viajes con zona 264 (Unknown) o 265 (Outside of NYC)")
    duckdb.sql(f"""
        SELECT
            count(*) FILTER (WHERE PULocationID IN (264, 265)) AS origen_desconocido,
            count(*) FILTER (WHERE DOLocationID IN (264, 265)) AS destino_desconocido,
            count(*) FILTER (WHERE PULocationID IN (264, 265) OR DOLocationID IN (264, 265)) AS alguno
        FROM {origen}
    """).show()
