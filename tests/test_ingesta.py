"""Parte 1: idempotencia de la ingesta (lo pide la consigna) y reintentos ante fallas de red.
La descarga se reemplaza por una falsa: no se usa internet."""
import dlt
import pyarrow.parquet as pq
import pytest
import requests

from src import ingesta
from src.base import consultar
from tests.conftest import MES, parquet_sintetico


@pytest.fixture
def ingesta_aislada(base_de_prueba, tmp_path, monkeypatch):
    """La ingesta escribe en una carpeta temporal y lleva la cuenta de cuántas veces descargó."""
    from src.base import conectar
    with conectar() as conexion, conexion.cursor() as cursor:  # raw vacío, como en una instalación nueva
        cursor.execute("DROP SCHEMA IF EXISTS raw CASCADE; DROP SCHEMA IF EXISTS raw_staging CASCADE;")
    monkeypatch.setattr(ingesta, "RAIZ_RAW", tmp_path / "raw" / "yellow")
    monkeypatch.setattr(ingesta, "RUTA_ZONAS", tmp_path / "raw" / "zones" / "taxi_zone_lookup.csv")
    monkeypatch.setattr(ingesta, "crear_pipeline", lambda: dlt.pipeline(
        pipeline_name="nyc_taxi_test", destination="postgres", dataset_name="raw",
        pipelines_dir=str(tmp_path / "dlt")))
    monkeypatch.setattr(ingesta.time, "sleep", lambda segundos: None)  # sin esperas reales
    descargas = []

    def descarga_falsa(url, destino):
        descargas.append(url)
        destino.parent.mkdir(parents=True, exist_ok=True)
        if url.endswith(".csv"):
            destino.write_text("LocationID,Borough,Zone,service_zone\n161,Manhattan,Midtown Center,Yellow Zone\n")
        else:
            pq.write_table(parquet_sintetico(3), destino)

    monkeypatch.setattr(ingesta, "descargar", descarga_falsa)
    return descargas


def contar(sql):
    return consultar(sql)[1][0][0]


def test_ingesta_es_idempotente(ingesta_aislada):
    descargas = ingesta_aislada

    # Primera corrida: descarga la tabla de zonas y el mes, carga 3 filas y registra 2 "ok".
    assert ingesta.ingestar_mes(MES)
    assert len(descargas) == 2
    assert contar("SELECT count(*) FROM raw.yellow_trips") == 3
    assert contar("SELECT count(*) FROM raw.ingestion_log WHERE estado = 'ok'") == 2

    # Segunda corrida: los hashes coinciden; no descarga, no carga y no agrega filas al log.
    assert ingesta.ingestar_mes(MES)
    assert len(descargas) == 2
    assert contar("SELECT count(*) FROM raw.yellow_trips") == 3
    assert contar("SELECT count(*) FROM raw.ingestion_log") == 2

    # Si el archivo se corrompe, el hash ya no coincide: lo vuelve a bajar y reemplaza el mes sin duplicar.
    _, archivo = ingesta.armar_rutas(MES)
    with open(archivo, "ab") as f:
        f.write(b"basura")
    assert ingesta.ingestar_mes(MES)
    assert len(descargas) == 3
    assert contar("SELECT count(*) FROM raw.yellow_trips") == 3


def test_falla_de_red_reintenta_3_veces_y_registra_el_error(ingesta_aislada, monkeypatch, tmp_path):
    intentos = []

    def descarga_que_falla(url, destino):
        intentos.append(url)
        raise requests.ConnectionError("sin red (simulado)")

    monkeypatch.setattr(ingesta, "descargar", descarga_que_falla)
    monkeypatch.setattr(ingesta, "RAIZ_RAW", tmp_path / "otra")
    monkeypatch.setattr(ingesta, "RUTA_ZONAS", tmp_path / "otra" / "zonas.csv")

    assert ingesta.ingestar_mes("2025-04") is False
    assert len(intentos) == 2 * (1 + 3)   # zonas y mes: 1 intento + 3 reintentos cada uno
    assert contar("SELECT count(*) FROM raw.ingestion_log WHERE estado = 'error'") >= 1
