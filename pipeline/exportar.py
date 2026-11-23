"""Parte 4 de la consigna: capa curada en Parquet particionado por year y month (estilo Hive).

Lee curado.trips_curados de Postgres (la arma dbt) para un mes y la escribe en
    data/curated/yellow/year=AAAA/month=MM/trips.parquet
Reprocesar un mes reemplaza solo su archivo: los demás meses quedan intactos.

Uso (desde el contenedor):  python -m pipeline.exportar --mes 2025-03
"""
import argparse
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import psycopg2
import pyarrow as pa
import pyarrow.csv as pv
import pyarrow.parquet as pq

RAIZ_CURADA = Path("data/curated/yellow")
ESQUEMA_PG = "curado"
TABLA_PG = "trips_curados"
TAMANIO_BLOQUE = 16 * 1024 * 1024  # 16 MB de CSV por lote: la memoria no depende del tamaño del mes

# Tipo de Postgres -> tipo de Arrow (el que se escribe en el Parquet).
TIPOS = {
    "integer": pa.int32(),
    "bigint": pa.int64(),
    "double precision": pa.float64(),
    "date": pa.date32(),
    "timestamp without time zone": pa.timestamp("us"),
    "text": pa.string(),
    "character varying": pa.string(),
}


def conectar():
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )


def esquema_de_la_tabla(cursor):
    """Arma el esquema de Arrow a partir de las columnas de la tabla en Postgres."""
    cursor.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
        (ESQUEMA_PG, TABLA_PG),
    )
    campos = []
    for nombre, tipo in cursor.fetchall():
        if tipo not in TIPOS:
            raise ValueError(f"La columna {nombre} es de tipo '{tipo}', que la exportación no espera.")
        campos.append((nombre, TIPOS[tipo]))
    return pa.schema(campos)


def ruta_particion(mes):
    anio, numero_mes = mes.split("-")
    return RAIZ_CURADA / f"year={anio}" / f"month={numero_mes}" / "trips.parquet"


def mostrar_particiones(titulo):
    """Lista cada partición con sus filas, tamaño y hora de escritura (para el antes/después)."""
    print(titulo)
    archivos = sorted(RAIZ_CURADA.glob("year=*/month=*/trips.parquet"))
    if not archivos:
        print("  (no hay particiones)")
    for archivo in archivos:
        filas = pq.ParquetFile(archivo).metadata.num_rows
        datos = archivo.stat()
        hora = datetime.fromtimestamp(datos.st_mtime).strftime("%H:%M:%S")
        print(f"  {archivo.parent.relative_to(RAIZ_CURADA)}  {filas:>9} filas  {datos.st_size:>11} bytes  escrito {hora}")


def exportar_mes(mes):
    """Escribe la partición del mes. Devuelve True si quedó con todas las filas."""
    destino = ruta_particion(mes)
    destino.parent.mkdir(parents=True, exist_ok=True)
    # El CSV temporal va al disco propio del contenedor y no a data/: en Mac y Windows,
    # data/ es una carpeta compartida con la máquina y escribir ahí 600 MB es lento.
    csv_temporal = Path(tempfile.gettempdir()) / f"trips_{mes}.csv.tmp"
    parquet_temporal = destino.with_suffix(".tmp")

    tabla = f"{ESQUEMA_PG}.{TABLA_PG}"
    with conectar() as conexion, conexion.cursor() as cursor:
        esquema = esquema_de_la_tabla(cursor)
        cursor.execute(f"SELECT count(*) FROM {tabla} WHERE mes_archivo = %s", (mes,))
        esperadas = cursor.fetchone()[0]
        if esperadas == 0:
            print(f"ERROR: {tabla} no tiene filas de {mes}. ¿Corrió dbt?")
            return False

        # 1) Postgres vuelca las filas del mes a un CSV temporal (COPY es la forma más rápida de sacarlas).
        consulta = cursor.mogrify(
            f"COPY (SELECT * FROM {tabla} WHERE mes_archivo = %s) TO STDOUT WITH (FORMAT csv)", (mes,)
        ).decode()
        with open(csv_temporal, "w", encoding="utf-8") as archivo:
            cursor.copy_expert(consulta, archivo)

    # 2) pyarrow lee ese CSV de a bloques, con los tipos de la tabla, y escribe el Parquet.
    #    En el CSV de Postgres, NULL es un campo vacío y el texto vacío es "" (entre comillas).
    lector = pv.open_csv(
        csv_temporal,
        read_options=pv.ReadOptions(column_names=esquema.names, block_size=TAMANIO_BLOQUE),
        convert_options=pv.ConvertOptions(
            column_types=esquema,
            null_values=[""],
            strings_can_be_null=True,
            quoted_strings_can_be_null=False,
        ),
    )
    try:
        with pq.ParquetWriter(parquet_temporal, esquema) as escritor:
            for lote in lector:
                escritor.write_batch(lote)
    finally:
        csv_temporal.unlink(missing_ok=True)

    # 3) Se reemplaza la partición de una sola vez: si algo se corta antes, la anterior queda intacta.
    parquet_temporal.replace(destino)

    escritas = pq.ParquetFile(destino).metadata.num_rows
    if escritas != esperadas:
        print(f"ERROR: se esperaban {esperadas} filas y se escribieron {escritas}.")
        return False

    print(f"OK: {escritas} filas escritas en {destino}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Escribe la capa curada de un mes en Parquet particionado.")
    parser.add_argument("--mes", required=True, help="Mes a exportar, formato AAAA-MM")
    args = parser.parse_args()

    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", args.mes):
        parser.error("--mes tiene que tener formato AAAA-MM, por ejemplo 2025-03")

    mostrar_particiones("Particiones antes:")
    ok = exportar_mes(args.mes)
    mostrar_particiones("Particiones después:")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
