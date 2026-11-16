"""Etapa de ingesta del pipeline."""
import argparse
import hashlib
import sys
import time
from datetime import datetime
from pathlib import Path

import duckdb
import requests

URL_BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data"
URL_ZONAS = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
RAIZ_RAW = Path("data/raw/yellow")
RUTA_ZONAS = Path("data/raw/zones/taxi_zone_lookup.csv")
RUTA_DB = Path("data/taxi.duckdb")
TAMANIO_BLOQUE = 1024 * 1024  # 1 MB
MAX_REINTENTOS = 3
ESPERA_INICIAL = 2  # segundos; se duplica en cada reintento


def armar_rutas(mes):
    anio, numero_mes = mes.split("-")
    nombre = f"yellow_tripdata_{mes}.parquet"
    url = f"{URL_BASE}/{nombre}"
    destino = RAIZ_RAW / f"year={anio}" / f"month={numero_mes}" / nombre
    return url, destino


def descargar(url, destino):
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(".tmp")

    respuesta = requests.get(url, stream=True, timeout=60)
    respuesta.raise_for_status()

    with open(temporal, "wb") as archivo:
        for bloque in respuesta.iter_content(chunk_size=TAMANIO_BLOQUE):
            archivo.write(bloque)

    temporal.replace(destino)


def descargar_con_reintentos(url, destino):
    intento = 0
    while True:
        try:
            descargar(url, destino)
            return
        except requests.RequestException as error:
            if intento == MAX_REINTENTOS:
                raise
            espera = ESPERA_INICIAL * 2**intento
            intento = intento + 1
            print(f"  Falló la descarga ({error}). Reintento {intento} de {MAX_REINTENTOS} en {espera} s.")
            time.sleep(espera)


def calcular_hash(ruta):
    sha = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        while True:
            bloque = archivo.read(TAMANIO_BLOQUE)
            if not bloque:
                break
            sha.update(bloque)
    return sha.hexdigest()


def contar_filas(ruta):
    if ruta.suffix == ".parquet":
        origen = f"read_parquet('{ruta}', hive_partitioning = false)"
    else:
        origen = f"read_csv('{ruta}')"
    return duckdb.sql(f"SELECT count(*) FROM {origen}").fetchall()[0][0]


def conectar():
    RUTA_DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(RUTA_DB))
    con.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_log (
            archivo    VARCHAR,
            url        VARCHAR,
            filas      BIGINT,
            bytes      BIGINT,
            hash       VARCHAR,
            fecha_hora TIMESTAMP,
            estado     VARCHAR,
            detalle    VARCHAR
        )
    """)
    return con


def registrar(archivo, url, filas, tamanio, hash_archivo, estado, detalle=None):
    con = conectar()
    con.execute(
        "INSERT INTO ingestion_log VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [archivo, url, filas, tamanio, hash_archivo, datetime.now(), estado, detalle],
    )
    con.close()


def ultimo_hash_ok(archivo):
    con = conectar()
    resultado = con.execute(
        """
        SELECT hash
        FROM ingestion_log
        WHERE archivo = ? AND estado = 'ok'
        ORDER BY fecha_hora DESC
        LIMIT 1
        """,
        [archivo],
    ).fetchall()
    con.close()

    if not resultado:
        return None
    return resultado[0][0]


def ingestar(url, destino):
    """Deja el archivo en destino. Devuelve True si quedó bien, False si falló."""
    nombre = destino.name

    if destino.exists() and calcular_hash(destino) == ultimo_hash_ok(nombre):
        print(f"Sin cambios: {nombre} ya está descargado y su hash coincide. No se descarga.")
        return True

    print("Descargando", url)
    try:
        descargar_con_reintentos(url, destino)
    except requests.RequestException as error:
        registrar(nombre, url, None, None, None, "error", str(error))
        print(f"ERROR: no se pudo descargar {nombre}.")
        return False

    filas = contar_filas(destino)
    tamanio = destino.stat().st_size
    hash_archivo = calcular_hash(destino)

    registrar(nombre, url, filas, tamanio, hash_archivo, "ok")
    print(f"OK: {nombre} | {filas} filas | {tamanio} bytes | hash {hash_archivo[:12]}...")
    return True


def main():
    parser = argparse.ArgumentParser(description="Descarga un mes de taxis amarillos.")
    parser.add_argument("--mes", required=True, help="Mes a descargar, formato AAAA-MM")
    args = parser.parse_args()

    try:
        datetime.strptime(args.mes, "%Y-%m")
    except ValueError:
        parser.error("--mes tiene que tener formato AAAA-MM, por ejemplo 2025-03")

    url, destino = armar_rutas(args.mes)

    zonas_ok = ingestar(URL_ZONAS, RUTA_ZONAS)
    mes_ok = ingestar(url, destino)

    if not (zonas_ok and mes_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()