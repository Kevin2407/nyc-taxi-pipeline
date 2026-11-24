"""Parte 3.4: el pipeline falla si las filas leídas no son iguales a aceptadas + cuarentena."""
from src import calidad
from src.base import conectar
from src.correr_dbt import correr_dbt
from tests.conftest import MES, cargar_raw, viaje_valido


def test_la_reconciliacion_detecta_una_fila_perdida(base_de_prueba):
    cargar_raw([viaje_valido(), viaje_valido(total_amount=-1.0, trip_distance=3.0), viaje_valido(trip_distance=4.0)])
    assert calidad.validar(MES)                              # 3 leídas = 2 aceptadas + 1 en cuarentena
    assert correr_dbt("test", ["reconciliacion"], MES)       # el test pasa

    # Simulamos un error del pipeline: se pierde una fila aceptada y se rehace el reporte.
    with conectar() as conexion, conexion.cursor() as cursor:
        cursor.execute("DELETE FROM calidad.trips_validos WHERE ctid = (SELECT min(ctid) FROM calidad.trips_validos)")
    assert correr_dbt("build", ["reporte_calidad"], MES) is False  # el test de reconciliación falla
