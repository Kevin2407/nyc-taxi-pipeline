"""Datos sintéticos compartidos por los tests."""
import duckdb
import pytest

from src import calidad
from src.esquema import cargar_contrato

MES = "2025-03"


def fila_valida():
    """Un viaje correcto: no viola ninguna regla."""
    return {
        "vendor_id": 2,
        "tpep_pickup_datetime": "2025-03-10 10:00:00",
        "tpep_dropoff_datetime": "2025-03-10 10:15:00",
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


@pytest.fixture
def base_sintetica(tmp_path, monkeypatch):
    """Base DuckDB temporal con una tabla zonas mínima. Devuelve una función para cargar viajes."""
    ruta_db = tmp_path / "test.duckdb"
    ruta_zonas = tmp_path / "zonas.csv"
    ruta_zonas.write_text(
        "LocationID,Borough,Zone,service_zone\n"
        "161,Manhattan,Midtown Center,Yellow Zone\n"
        "237,Manhattan,Upper East Side South,Yellow Zone\n"
    )
    monkeypatch.setattr(calidad, "RUTA_DB", ruta_db)
    monkeypatch.setattr(calidad, "RUTA_ZONAS", ruta_zonas)

    def cargar_viajes(filas):
        con = duckdb.connect(str(ruta_db))
        definiciones = []
        for columna in cargar_contrato()["columns"]:
            definiciones.append(f"{columna['name']} {columna['type']}")
        con.execute(f"""
            CREATE TABLE yellow_trips (
                {", ".join(definiciones)},
                archivo_origen VARCHAR,
                mes_archivo VARCHAR
            )
        """)
        for fila in filas:
            columnas = ", ".join(fila.keys())
            huecos = ", ".join(["?"] * len(fila))
            con.execute(f"INSERT INTO yellow_trips ({columnas}) VALUES ({huecos})", list(fila.values()))
        con.close()
        return ruta_db

    return cargar_viajes