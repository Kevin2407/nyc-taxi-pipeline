import duckdb

ARCHIVOS = {
    "2024-03": "data/raw/yellow/year=2024/month=03/yellow_tripdata_2024-03.parquet",
    "2025-03": "data/raw/yellow/year=2025/month=03/yellow_tripdata_2025-03.parquet",
}

for mes, ruta in ARCHIVOS.items():
    print("=====", mes, "=====")
    origen = f"read_parquet('{ruta}', hive_partitioning = false)"

    duckdb.sql(f"""
        SELECT
            payment_type,
            count(*) AS viajes,
            count(*) FILTER (WHERE passenger_count IS NULL) AS pasajeros_nulo,
            count(*) FILTER (WHERE passenger_count = 0) AS pasajeros_cero,
            count(*) FILTER (WHERE total_amount < 0) AS total_negativo
        FROM {origen}
        GROUP BY payment_type
        ORDER BY payment_type
    """).show()