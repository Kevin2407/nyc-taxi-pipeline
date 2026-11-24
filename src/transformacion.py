"""Parte 4 de la consigna: transformación y almacenamiento.

Dos pasos:
1. dbt arma curado.trips_curados (sql/curado/trips_curados.sql): los viajes aceptados con
   duración, velocidad, fecha, hora y día de la subida, propina % y barrio y zona de origen
   y destino.
2. Este módulo escribe cada mes en Parquet particionado por year y month (estilo Hive):
       data/curated/yellow/year=AAAA/month=MM/trips.parquet
   Postgres saca las filas del mes con COPY a un CSV temporal y Polars lo convierte a Parquet
   en modo streaming (no carga el mes entero en memoria). Reprocesar un mes reemplaza solo su
   archivo: los demás quedan intactos, y el script muestra las particiones antes y después.

Uso (desde el contenedor):
    python -m src.transformacion --mes 2025-03                 dbt (curado) + Parquet de ese mes
    python -m src.transformacion --mes 2025-03 --solo-parquet  solo el Parquet
"""
import argparse
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import polars as pl

from src.base import conectar
from src.correr_dbt import correr_dbt
from src.meses import es_mes_valido

RAIZ_CURADA = Path("data/curated/yellow")
ESQUEMA_PG = "curado"
TABLA_PG = "trips_curados"

# Tipo de Postgres -> tipo de Polars (el que se escribe en el Parquet).
TIPOS = {
    "integer": pl.Int32,
    "bigint": pl.Int64,
    "double precision": pl.Float64,
    "date": pl.Date,
    "timestamp without time zone": pl.Datetime("us"),
    "text": pl.String,
    "character varying": pl.String,
}


def ruta_particion(mes):
    anio, numero_mes = mes.split("-")
    return RAIZ_CURADA / f"year={anio}" / f"month={numero_mes}" / "trips.parquet"


def filas_de_la_particion(ruta):
    return pl.scan_parquet(ruta).select(pl.len()).collect().item()


def esquema_de_la_tabla(cursor):
    """Columnas de curado.trips_curados con su tipo de Polars, en orden."""
    cursor.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
        (ESQUEMA_PG, TABLA_PG),
    )
    esquema = {}
    for nombre, tipo in cursor.fetchall():
        if tipo not in TIPOS:
            raise ValueError(f"La columna {nombre} es de tipo '{tipo}', que la exportación no espera.")
        esquema[nombre] = TIPOS[tipo]
    return esquema


def mostrar_particiones(titulo):
    """Lista cada partición con sus filas, tamaño y hora de escritura (el antes/después de la consigna 4.4)."""
    print(titulo)
    archivos = sorted(RAIZ_CURADA.glob("year=*/month=*/trips.parquet"))
    if not archivos:
        print("  (no hay particiones)")
    for archivo in archivos:
        datos = archivo.stat()
        hora = datetime.fromtimestamp(datos.st_mtime).strftime("%H:%M:%S")
        print(f"  {archivo.parent.relative_to(RAIZ_CURADA)}  {filas_de_la_particion(archivo):>9} filas"
              f"  {datos.st_size:>11} bytes  escrito {hora}")


def exportar_mes(mes):
    """Escribe la partición del mes. Devuelve True si quedó con todas las filas."""
    destino = ruta_particion(mes)
    destino.parent.mkdir(parents=True, exist_ok=True)
    parquet_temporal = destino.with_suffix(".tmp")
    # El CSV temporal va al disco propio del contenedor y no a data/: en Mac y Windows,
    # data/ es una carpeta compartida con la máquina y escribir ahí 600 MB es lento.
    csv_temporal = Path(tempfile.gettempdir()) / f"trips_{mes}.csv.tmp"

    tabla = f"{ESQUEMA_PG}.{TABLA_PG}"
    with conectar() as conexion, conexion.cursor() as cursor:
        esquema = esquema_de_la_tabla(cursor)
        cursor.execute(f"SELECT count(*) FROM {tabla} WHERE mes_archivo = %s", (mes,))
        esperadas = cursor.fetchone()[0]
        if esperadas == 0:
            print(f"ERROR: {tabla} no tiene filas de {mes}. ¿Corrió dbt?")
            return False

        # 1) Postgres vuelca las filas del mes a un CSV (COPY es la forma más rápida de sacarlas).
        consulta = cursor.mogrify(
            f"COPY (SELECT * FROM {tabla} WHERE mes_archivo = %s) TO STDOUT WITH (FORMAT csv)", (mes,)
        ).decode()
        with open(csv_temporal, "w", encoding="utf-8") as archivo:
            cursor.copy_expert(consulta, archivo)

    try:
        # 2) Polars lee el CSV con los tipos de la tabla y escribe el Parquet en streaming.
        #    En el CSV de Postgres, NULL es un campo vacío y el texto vacío es "" (entre comillas):
        #    Polars los distingue igual (vacío -> nulo, "" -> texto vacío).
        (
            pl.scan_csv(csv_temporal, has_header=False, new_columns=list(esquema), schema=esquema)
            .sink_parquet(parquet_temporal)
        )
    finally:
        csv_temporal.unlink(missing_ok=True)

    # 3) Se reemplaza la partición de una sola vez: si algo se cortó antes, la anterior queda intacta.
    parquet_temporal.replace(destino)

    escritas = filas_de_la_particion(destino)
    if escritas != esperadas:
        print(f"ERROR: se esperaban {esperadas} filas y se escribieron {escritas}.")
        return False
    print(f"OK: {escritas} filas escritas en {destino}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Capa curada (dbt) y Parquet particionado de un mes.")
    parser.add_argument("--mes", required=True, help="Mes a transformar, formato AAAA-MM")
    parser.add_argument("--solo-parquet", action="store_true", help="No corre dbt; solo escribe el Parquet")
    args = parser.parse_args()
    if not es_mes_valido(args.mes):
        parser.error("--mes tiene que tener formato AAAA-MM, por ejemplo 2025-03")

    if not args.solo_parquet and not correr_dbt("build", ["curado"], args.mes):
        print("ERROR: dbt no pudo construir la capa curada.")
        sys.exit(1)
    mostrar_particiones("Particiones antes:")
    ok = exportar_mes(args.mes)
    mostrar_particiones("Particiones después:")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
