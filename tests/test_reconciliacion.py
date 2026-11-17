"""Tests de la reconciliación de conteos."""
import duckdb

from src import calidad
from tests.conftest import MES, fila_valida


def test_reconciliacion_detecta_filas_perdidas():
    assert calidad.reconciliacion_cierra(10, 7, 3)
    assert not calidad.reconciliacion_cierra(10, 7, 2)
    assert not calidad.reconciliacion_cierra(10, 8, 3)


def test_reconciliacion_cierra_en_una_corrida(base_sintetica):
    filas = []
    for dia in range(1, 6):
        fila = fila_valida()
        fila["tpep_pickup_datetime"] = f"2025-03-0{dia} 10:00:00"
        fila["tpep_dropoff_datetime"] = f"2025-03-0{dia} 10:20:00"
        filas.append(fila)
    filas[0]["trip_distance"] = 500.0
    filas[1]["tpep_dropoff_datetime"] = filas[1]["tpep_pickup_datetime"]

    ruta_db = base_sintetica(filas)
    assert calidad.validar_mes(MES)

    con = duckdb.connect(str(ruta_db))
    leidas, aceptadas, en_cuarentena = con.execute(
        "SELECT filas_leidas, filas_aceptadas, filas_cuarentena FROM reporte_calidad"
    ).fetchall()[0]
    con.close()

    assert (leidas, aceptadas, en_cuarentena) == (5, 3, 2)