import duckdb

ARCHIVOS = {
    "2024-03": "data/raw/yellow/year=2024/month=03/yellow_tripdata_2024-03.parquet",
    "2025-03": "data/raw/yellow/year=2025/month=03/yellow_tripdata_2025-03.parquet",
}

for mes, ruta in ARCHIVOS.items():
    origen = f"read_parquet('{ruta}', hive_partitioning = false)"

    total = duckdb.sql(f"SELECT count(*) FROM {origen}").fetchall()[0][0]
    distintas = duckdb.sql(
        f"SELECT count(*) FROM (SELECT DISTINCT * FROM {origen})"
    ).fetchall()[0][0]

    print(mes, "| total:", total, "| distintas:", distintas, "| sobran:", total - distintas)