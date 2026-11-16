import duckdb

ARCHIVOS = {
    "2024-03": "data/raw/yellow/year=2024/month=03/yellow_tripdata_2024-03.parquet",
    "2025-03": "data/raw/yellow/year=2025/month=03/yellow_tripdata_2025-03.parquet",
}

for mes, ruta in ARCHIVOS.items():
    print("=====", mes, "=====")
    origen = f"read_parquet('{ruta}', hive_partitioning = false)"

    filas = duckdb.sql(f"SELECT count(*) FROM {origen}").fetchall()[0][0]
    print("Filas:", filas)

    duckdb.sql(f"""
        SELECT column_name, column_type
        FROM (DESCRIBE SELECT * FROM {origen})
    """).show()