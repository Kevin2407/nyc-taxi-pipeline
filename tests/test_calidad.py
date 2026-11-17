"""Test de reglas de calidad sobre datos sintéticos."""
import duckdb

from src import calidad
from tests.conftest import MES, fila_valida


def test_reglas_de_rechazo_y_advertencia(base_sintetica):
    valida = fila_valida()

    total_negativo = fila_valida()
    total_negativo["total_amount"] = -22.0
    total_negativo["tpep_pickup_datetime"] = "2025-03-11 10:00:00"
    total_negativo["tpep_dropoff_datetime"] = "2025-03-11 10:15:00"

    sin_pasajeros = fila_valida()
    sin_pasajeros["passenger_count"] = 0
    sin_pasajeros["tpep_pickup_datetime"] = "2025-03-12 10:00:00"
    sin_pasajeros["tpep_dropoff_datetime"] = "2025-03-12 10:15:00"

    copia_de_la_valida = fila_valida()

    ruta_db = base_sintetica([valida, total_negativo, sin_pasajeros, copia_de_la_valida])

    assert calidad.validar_mes(MES)

    con = duckdb.connect(str(ruta_db))
    cuarentena = con.execute(
        "SELECT reglas_violadas FROM cuarentena ORDER BY reglas_violadas"
    ).fetchall()
    validos = con.execute(
        "SELECT passenger_count, flags FROM trips_validos ORDER BY passenger_count"
    ).fetchall()
    con.close()

    # R05 (total negativo) y R08 (duplicado) son de rechazo: van a cuarentena.
    assert cuarentena == [("R05",), ("R08",)]
    # R06 (pasajeros 0) es advertencia: la fila sigue, marcada. La válida no tiene flags.
    assert validos == [(0, "R06"), (1, "")]