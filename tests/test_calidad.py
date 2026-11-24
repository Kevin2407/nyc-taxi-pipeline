"""Parte 3: reglas de calidad sobre datos sintéticos (lo pide la consigna)."""
from datetime import datetime

from src import calidad
from src.base import consultar
from tests.conftest import MES, cargar_raw, viaje_valido


def test_reglas_de_rechazo_y_advertencia(base_de_prueba):
    viajes = [
        viaje_valido(),                                                    # válido
        viaje_valido(),                                                    # R08: copia exacta del anterior
        viaje_valido(total_amount=-22.0, trip_distance=2.6),               # R05: importe negativo
        viaje_valido(passenger_count=0, trip_distance=2.7),                # R06: advertencia, sigue
        viaje_valido(pu_location_id=999, trip_distance=2.8),               # R07: zona inexistente
        viaje_valido(do_location_id=None, trip_distance=2.9),              # R07: zona nula
        viaje_valido(trip_distance=500.0),                                 # R04 y R10: 500 millas en 15 minutos
        viaje_valido(tpep_pickup_datetime=datetime(2025, 2, 28, 23, 50),   # R01: subida fuera del mes
                     tpep_dropoff_datetime=datetime(2025, 3, 1, 0, 5), trip_distance=3.1),
    ]
    cargar_raw(viajes)

    assert calidad.validar(MES)  # dbt build de staging y calidad, con la reconciliación

    _, cuarentena = consultar("SELECT reglas_violadas FROM calidad.cuarentena ORDER BY reglas_violadas")
    assert [fila[0] for fila in cuarentena] == ["R01", "R04,R10", "R05", "R07", "R07", "R08"]

    _, validos = consultar("SELECT passenger_count, flags FROM calidad.trips_validos ORDER BY passenger_count")
    assert validos == [(0, "R06"), (1, "")]  # la advertencia no descarta la fila: la marca

    _, reporte = consultar("SELECT filas_leidas, filas_aceptadas, filas_cuarentena FROM calidad.reporte_calidad")
    assert reporte == [(8, 2, 6)]
