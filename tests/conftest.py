"""Base de datos de prueba y datos sintéticos compartidos por los tests.

Los tests que necesitan Postgres usan una base aparte, taxi_test, que se crea al empezar y se
borra al terminar: nunca tocan la base taxi con los datos reales. Corren dentro del contenedor:
    make test        (o: docker compose run --rm herramientas pytest)
"""
import os
from datetime import datetime

import psycopg2
import pyarrow as pa
import pytest

BASE_DE_PRUEBA = "taxi_test"
MES = "2025-03"


def ejecutar_como_admin(sql):
    """Ejecuta una sentencia en la base "postgres" (CREATE/DROP DATABASE no pueden ir en una transacción)."""
    conexion = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"], port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
        dbname="postgres",
    )
    conexion.autocommit = True
    try:
        conexion.cursor().execute(sql)
    finally:
        conexion.close()


@pytest.fixture(scope="session")
def base_de_prueba():
    """Crea la base taxi_test y apunta a ella dbt, dlt y src.base durante los tests."""
    anteriores = {clave: os.environ.get(clave) for clave in ["POSTGRES_DB", "DESTINATION__POSTGRES__CREDENTIALS"]}
    ejecutar_como_admin(f"DROP DATABASE IF EXISTS {BASE_DE_PRUEBA} WITH (FORCE)")
    ejecutar_como_admin(f"CREATE DATABASE {BASE_DE_PRUEBA}")
    os.environ["POSTGRES_DB"] = BASE_DE_PRUEBA
    os.environ["DESTINATION__POSTGRES__CREDENTIALS"] = (
        f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ.get('POSTGRES_PORT', '5432')}/{BASE_DE_PRUEBA}"
    )
    yield BASE_DE_PRUEBA
    for clave, valor in anteriores.items():
        if valor is None:
            os.environ.pop(clave, None)
        else:
            os.environ[clave] = valor
    ejecutar_como_admin(f"DROP DATABASE IF EXISTS {BASE_DE_PRUEBA} WITH (FORCE)")


def viaje_valido(**cambios):
    """Un viaje correcto (no viola ninguna regla). cambios pisa los campos que se pidan."""
    viaje = {
        "vendor_id": 2,
        "tpep_pickup_datetime": datetime(2025, 3, 10, 10, 0, 0),
        "tpep_dropoff_datetime": datetime(2025, 3, 10, 10, 15, 0),
        "passenger_count": 1,
        "trip_distance": 2.5,
        "ratecode_id": 1,
        "store_and_fwd_flag": "N",
        "pu_location_id": 161,
        "do_location_id": 237,
        "payment_type": 1,
        "fare_amount": 15.0,
        "extra": 0.0,
        "mta_tax": 0.5,
        "tip_amount": 3.0,
        "tolls_amount": 0.0,
        "improvement_surcharge": 1.0,
        "total_amount": 22.0,
        "congestion_surcharge": 2.5,
        "airport_fee": 0.0,
        "cbd_congestion_fee": 0.75,
        "archivo_origen": "sintetico.parquet",
        "mes_archivo": MES,
    }
    viaje.update(cambios)
    return viaje


def cargar_raw(viajes):
    """Crea raw.yellow_trips y raw.zonas en la base de prueba, como los dejaría la ingesta."""
    from src.base import conectar

    columnas = list(viajes[0])
    with conectar() as conexion, conexion.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS raw CASCADE; CREATE SCHEMA raw;")
        cursor.execute("""
            CREATE TABLE raw.yellow_trips (
                vendor_id integer, tpep_pickup_datetime timestamp, tpep_dropoff_datetime timestamp,
                passenger_count bigint, trip_distance double precision, ratecode_id bigint,
                store_and_fwd_flag text, pu_location_id integer, do_location_id integer,
                payment_type bigint, fare_amount double precision, extra double precision,
                mta_tax double precision, tip_amount double precision, tolls_amount double precision,
                improvement_surcharge double precision, total_amount double precision,
                congestion_surcharge double precision, airport_fee double precision,
                cbd_congestion_fee double precision, archivo_origen text, mes_archivo text)
        """)
        for viaje in viajes:
            cursor.execute(
                f"INSERT INTO raw.yellow_trips ({', '.join(columnas)}) VALUES ({', '.join(['%s'] * len(columnas))})",
                [viaje[c] for c in columnas],
            )
        cursor.execute("CREATE TABLE raw.zonas (location_id bigint, borough text, zone text, service_zone text)")
        cursor.execute("""INSERT INTO raw.zonas VALUES
            (161, 'Manhattan', 'Midtown Center', 'Yellow Zone'),
            (237, 'Manhattan', 'Upper East Side South', 'Yellow Zone')""")


def parquet_sintetico(filas=3):
    """Un archivo como los de la TLC (nombres originales, sin cbd_congestion_fee como en 2024)."""
    return pa.table({
        "VendorID": pa.array([2] * filas, pa.int32()),
        "tpep_pickup_datetime": pa.array([datetime(2025, 3, 1, 10, i) for i in range(filas)], pa.timestamp("us")),
        "tpep_dropoff_datetime": pa.array([datetime(2025, 3, 1, 10, i + 10) for i in range(filas)], pa.timestamp("us")),
        "passenger_count": pa.array([1] * filas, pa.int64()),
        "trip_distance": pa.array([2.0] * filas),
        "RatecodeID": pa.array([1] * filas, pa.int64()),
        "store_and_fwd_flag": pa.array(["N"] * filas, pa.large_string()),
        "PULocationID": pa.array([161] * filas, pa.int32()),
        "DOLocationID": pa.array([237] * filas, pa.int32()),
        "payment_type": pa.array([1] * filas, pa.int64()),
        **{c: pa.array([1.0] * filas) for c in [
            "fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount",
            "improvement_surcharge", "total_amount", "congestion_surcharge", "Airport_fee"]},
    })
