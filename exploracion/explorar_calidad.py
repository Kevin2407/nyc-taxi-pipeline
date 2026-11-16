import duckdb

ARCHIVOS = {
    "2024-03": "data/raw/yellow/year=2024/month=03/yellow_tripdata_2024-03.parquet",
    "2025-03": "data/raw/yellow/year=2025/month=03/yellow_tripdata_2025-03.parquet",
}
ZONAS = "data/raw/zones/taxi_zone_lookup.csv"

for mes, ruta in ARCHIVOS.items():
    origen = f"read_parquet('{ruta}', hive_partitioning = false)"
    total = duckdb.sql(f"SELECT count(*) FROM {origen}").fetchall()[0][0]
    print("=====", mes, "=====", total, "filas")

    reglas = {
        "subida fuera del mes": f"strftime(tpep_pickup_datetime, '%Y-%m') <> '{mes}'",
        "bajada <= subida": "tpep_dropoff_datetime <= tpep_pickup_datetime",
        "distancia <= 0": "trip_distance <= 0",
        "total negativo": "total_amount < 0",
        "pasajeros nulo o 0": "passenger_count IS NULL OR passenger_count = 0",
        "zona origen inexistente": f"PULocationID NOT IN (SELECT LocationID FROM '{ZONAS}')",
        "zona destino inexistente": f"DOLocationID NOT IN (SELECT LocationID FROM '{ZONAS}')",
    }

    for nombre, condicion in reglas.items():
        n = duckdb.sql(f"SELECT count(*) FROM {origen} WHERE {condicion}").fetchall()[0][0]
        print(f"  {nombre:26} {n:>9}  ({n / total:.2%})")