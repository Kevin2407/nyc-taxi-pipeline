"""Parte 1 de la consigna: ingesta.

Descarga el archivo del mes a data/raw sin modificarlo (con hash, reintentos y log)
y lo carga a Postgres con dlt, en la tabla raw.yellow_trips.

Uso (desde el contenedor):  python -m pipeline.ingesta --mes 2025-03
                            python -m pipeline.ingesta --mes 2025-03 --forzar
"""
import argparse
import hashlib
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import dlt
import pyarrow as pa
import pyarrow.csv as pv
import pyarrow.parquet as pq
import requests
from dlt.destinations.exceptions import DatabaseUndefinedRelation
from dlt.pipeline.exceptions import PipelineStepFailed

from pipeline.esquema import ajustar_al_contrato, cargar_contrato, validar_archivo

URL_BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data"
URL_ZONAS = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
RAIZ_RAW = Path("data/raw/yellow")
RUTA_ZONAS = Path("data/raw/zones/taxi_zone_lookup.csv")
TAMANIO_BLOQUE = 1024 * 1024  # 1 MB, para descargar y calcular el hash
FILAS_POR_LOTE = 100_000      # filas que dlt recibe por vez
MAX_REINTENTOS = 3
ESPERA_INICIAL = 2            # segundos; se duplica en cada reintento


# ---------- 1. Descarga del archivo crudo ----------

def armar_rutas(mes):
    """Devuelve la URL del mes y dónde se guarda: data/raw/yellow/year=AAAA/month=MM/."""
    anio, numero_mes = mes.split("-")
    nombre = f"yellow_tripdata_{mes}.parquet"
    url = f"{URL_BASE}/{nombre}"
    destino = RAIZ_RAW / f"year={anio}" / f"month={numero_mes}" / nombre
    return url, destino


def descargar(url, destino):
    """Baja el archivo en bloques de 1 MB a un .tmp y lo renombra al terminar."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(".tmp")

    respuesta = requests.get(url, stream=True, timeout=60)
    respuesta.raise_for_status()

    with open(temporal, "wb") as archivo:
        for bloque in respuesta.iter_content(chunk_size=TAMANIO_BLOQUE):
            archivo.write(bloque)

    temporal.replace(destino)


def descargar_con_reintentos(url, destino):
    """Hasta 3 reintentos, esperando 2, 4 y 8 segundos. Si sigue fallando, levanta el error."""
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
    """SHA-256 del archivo, leído en bloques de 1 MB."""
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
        return pq.ParquetFile(ruta).metadata.num_rows  # lo dice el archivo, sin leerlo entero
    return pv.read_csv(ruta).num_rows


# ---------- 2. dlt: qué se carga y cómo ----------

def sin_zona_horaria():
    """Aclaración para dlt: la columna es una fecha y hora SIN zona horaria.
    Los horarios del archivo son hora local de Nueva York; sin esto dlt los guarda
    como UTC y en DBeaver aparecen corridos.
    Es una función y no una constante porque dlt le escribe adentro el nombre de la
    columna: si las dos columnas compartieran el mismo diccionario, la segunda
    quedaría pisada (nos pasó: tpep_dropoff_datetime se cargó con zona horaria)."""
    return {"data_type": "timestamp", "timezone": False}


def crear_pipeline():
    """El pipeline de dlt: carga a Postgres (credenciales en DESTINATION__POSTGRES__CREDENTIALS)
    dentro del esquema raw."""
    return dlt.pipeline(
        pipeline_name="nyc_taxi",
        destination="postgres",
        dataset_name="raw",
    )


@dlt.resource(
    name="yellow_trips",
    # merge + delete-insert por mes_archivo: antes de insertar un mes, dlt borra
    # las filas que ya tenía de ese mes. Recargar un mes no duplica ni toca los demás.
    write_disposition={"disposition": "merge", "strategy": "delete-insert"},
    merge_key="mes_archivo",
    columns={
        "tpep_pickup_datetime": sin_zona_horaria(),
        "tpep_dropoff_datetime": sin_zona_horaria(),
    },
)
def viajes(ruta, mes, contrato):
    """Lee el Parquet de a lotes, deja cada lote con las columnas del contrato
    (snake_case, cbd_congestion_fee nula si falta, columnas nuevas afuera) y agrega
    de qué archivo y de qué mes viene cada fila."""
    archivo = pq.ParquetFile(ruta)
    for lote in archivo.iter_batches(batch_size=FILAS_POR_LOTE):
        tabla = ajustar_al_contrato(pa.Table.from_batches([lote]), contrato)
        filas = tabla.num_rows
        tabla = tabla.append_column("archivo_origen", pa.array([ruta.name] * filas))
        tabla = tabla.append_column("mes_archivo", pa.array([mes] * filas))
        yield tabla


@dlt.resource(name="zonas", write_disposition="replace")
def zonas(ruta):
    """La tabla de zonas es chica (265 filas): se lee entera y reemplaza a la anterior."""
    yield pv.read_csv(ruta)


# ---------- 3. ingestion_log ----------

# Tipos declarados: en una fila de error, filas/bytes/hash vienen vacíos y dlt
# no podría adivinar su tipo.
COLUMNAS_LOG = {
    "archivo": {"data_type": "text"},
    "url": {"data_type": "text"},
    "filas": {"data_type": "bigint"},
    "bytes": {"data_type": "bigint"},
    "hash": {"data_type": "text"},
    "fecha_hora": {"data_type": "timestamp"},
    "estado": {"data_type": "text"},
    "detalle": {"data_type": "text"},
}


def registrar(pipeline, archivo, url, filas, tamanio, hash_archivo, estado, detalle=None):
    """Agrega una fila a raw.ingestion_log."""
    fila = {
        "archivo": archivo,
        "url": url,
        "filas": filas,
        "bytes": tamanio,
        "hash": hash_archivo,
        "fecha_hora": datetime.now(),
        "estado": estado,
        "detalle": detalle,
    }
    pipeline.run([fila], table_name="ingestion_log", write_disposition="append", columns=COLUMNAS_LOG)


def ultimo_hash_ok(pipeline, archivo):
    """Hash de la última ingesta correcta de ese archivo, o None si nunca se ingestó."""
    try:
        with pipeline.sql_client() as cliente:
            tabla = cliente.make_qualified_table_name("ingestion_log")
            filas = cliente.execute_sql(
                f"SELECT hash FROM {tabla} WHERE archivo = %s AND estado = 'ok' "
                "ORDER BY fecha_hora DESC LIMIT 1",
                archivo,
            )
    except DatabaseUndefinedRelation:
        return None  # primera corrida: la tabla todavía no existe
    return filas[0][0] if filas else None


# ---------- 4. Ingesta de punta a punta ----------

def ingestar(pipeline, url, destino, recurso, validar=None, forzar=False):
    """Descarga, valida y carga un archivo. Devuelve True si quedó bien, False si falló.
    validar: función que se llama antes de cargar; si devuelve False, no se carga.
    forzar: vuelve a validar y cargar aunque el archivo ya esté ingestado."""
    nombre = destino.name

    # Idempotencia: si el archivo está y su hash es el de la última ingesta ok, no se hace nada.
    ya_ingestado = destino.exists() and calcular_hash(destino) == ultimo_hash_ok(pipeline, nombre)
    if ya_ingestado and not forzar:
        print(f"Sin cambios: {nombre} ya está descargado y cargado. No se hace nada.")
        return True

    if ya_ingestado:
        print(f"--forzar: {nombre} ya está descargado; se vuelve a validar y cargar sin bajarlo.")
    else:
        print("Descargando", url)
        try:
            descargar_con_reintentos(url, destino)
        except requests.RequestException as error:
            registrar(pipeline, nombre, url, None, None, None, "error", str(error))
            print(f"ERROR: no se pudo descargar {nombre}.")
            return False

    # Contrato de esquema: se compara ANTES de cargar.
    if validar is not None and not validar():
        registrar(pipeline, nombre, url, None, None, None, "error", "no cumple el contrato de esquema")
        print(f"ERROR: {nombre} no cumple el contrato de esquema. No se carga.")
        return False

    print(f"Cargando {nombre} a Postgres con dlt...")
    inicio = time.time()
    try:
        # csv: dlt carga con COPY, mucho más rápido que un INSERT por fila.
        info = pipeline.run(recurso, loader_file_format="csv")
    except PipelineStepFailed as error:
        registrar(pipeline, nombre, url, None, None, None, "error", str(error))
        print(f"ERROR: dlt no pudo cargar {nombre}.")
        return False
    print(info)
    print(f"  Carga terminada en {time.time() - inicio:.1f} s.")

    filas = contar_filas(destino)
    tamanio = destino.stat().st_size
    hash_archivo = calcular_hash(destino)
    registrar(pipeline, nombre, url, filas, tamanio, hash_archivo, "ok")
    print(f"OK: {nombre} | {filas} filas | {tamanio} bytes | hash {hash_archivo[:12]}...")
    return True


def ingestar_mes(mes, forzar=False):
    """Ingesta la tabla de zonas y el archivo del mes. Devuelve True si los dos quedaron bien.
    La usan main() (línea de comandos) y Dagster (pipeline/definitions.py)."""
    pipeline = crear_pipeline()
    contrato = cargar_contrato()
    url, destino = armar_rutas(mes)

    # viajes(...) y zonas(...) no leen nada todavía: preparan el resource.
    # El archivo se lee recién cuando pipeline.run lo consume, después de la descarga.
    zonas_ok = ingestar(pipeline, URL_ZONAS, RUTA_ZONAS, zonas(RUTA_ZONAS))
    mes_ok = ingestar(
        pipeline, url, destino, viajes(destino, mes, contrato),
        validar=lambda: validar_archivo(pipeline, destino, contrato),
        forzar=forzar,
    )
    return zonas_ok and mes_ok


def main():
    parser = argparse.ArgumentParser(description="Descarga un mes de taxis amarillos y lo carga a Postgres.")
    parser.add_argument("--mes", required=True, help="Mes a ingestar, formato AAAA-MM")
    parser.add_argument("--forzar", action="store_true",
                        help="Vuelve a validar y cargar el mes aunque ya esté ingestado")
    args = parser.parse_args()

    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", args.mes):
        parser.error("--mes tiene que tener formato AAAA-MM, por ejemplo 2025-03")

    if not ingestar_mes(args.mes, forzar=args.forzar):
        sys.exit(1)


if __name__ == "__main__":
    main()
