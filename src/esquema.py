"""Etapa de esquema del pipeline."""
import argparse
import re
import sys
from pathlib import Path

import duckdb
import yaml

from src.ingesta import RUTA_DB, armar_rutas

RUTA_CONTRATO = Path("contracts/yellow_schema.yaml")


def cargar_contrato():
    with open(RUTA_CONTRATO, encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)


def a_snake_case(nombre):
    nombre = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", nombre)
    nombre = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", nombre)
    return nombre.lower()


def leer_esquema_real(ruta):
    """Devuelve una lista de (nombre original, nombre normalizado, tipo)."""
    filas = duckdb.sql(f"""
        SELECT column_name, column_type
        FROM (DESCRIBE SELECT * FROM read_parquet('{ruta}', hive_partitioning = false))
    """).fetchall()

    esquema = []
    for nombre, tipo in filas:
        esquema.append((nombre, a_snake_case(nombre), tipo))
    return esquema


def comparar(esquema_real, contrato):
    reales = {}
    for original, normalizado, tipo in esquema_real:
        reales[normalizado] = tipo

    esperadas = {}
    for columna in contrato["columns"]:
        esperadas[columna["name"]] = columna

    reporte = {
        "faltantes_obligatorias": [],
        "faltantes_opcionales": [],
        "nuevas": [],
        "tipos_distintos": [],
    }

    for nombre, columna in esperadas.items():
        if nombre not in reales:
            if columna.get("opcional"):
                reporte["faltantes_opcionales"].append(nombre)
            else:
                reporte["faltantes_obligatorias"].append(nombre)
        elif reales[nombre] != columna["type"]:
            reporte["tipos_distintos"].append(
                f"{nombre} (contrato {columna['type']}, archivo {reales[nombre]})"
            )

    for nombre in reales:
        if nombre not in esperadas:
            reporte["nuevas"].append(nombre)

    return reporte


def cargar_mes(mes):
    """Valida el archivo del mes y lo carga en la tabla unificada. Devuelve True si quedó bien."""
    url, ruta = armar_rutas(mes)
    contrato = cargar_contrato()
    tabla = contrato["tabla"]
    esquema_real = leer_esquema_real(ruta)
    reporte = comparar(esquema_real, contrato)

    print(f"Esquema de {ruta.name} contra el contrato v{contrato['version']}:")
    for tipo_diferencia, columnas in reporte.items():
        print(f"  {tipo_diferencia:24} {columnas if columnas else 'ninguna'}")

    if reporte["faltantes_obligatorias"] or reporte["tipos_distintos"]:
        print("ERROR: el archivo no cumple el contrato. No se carga.")
        return False

    originales = {}
    for original, normalizado, tipo in esquema_real:
        originales[normalizado] = original

    definiciones = []
    selecciones = []
    for columna in contrato["columns"]:
        nombre = columna["name"]
        tipo = columna["type"]
        definiciones.append(f"{nombre} {tipo}")
        if nombre in originales:
            selecciones.append(f'"{originales[nombre]}" AS {nombre}')
        else:
            selecciones.append(f"CAST(NULL AS {tipo}) AS {nombre}")

    con = duckdb.connect(str(RUTA_DB))
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {tabla} (
            {", ".join(definiciones)},
            archivo_origen VARCHAR,
            mes_archivo VARCHAR
        )
    """)
    con.execute(f"DELETE FROM {tabla} WHERE mes_archivo = ?", [mes])
    con.execute(f"""
        INSERT INTO {tabla}
        SELECT
            {", ".join(selecciones)},
            '{ruta.name}' AS archivo_origen,
            '{mes}' AS mes_archivo
        FROM read_parquet('{ruta}', hive_partitioning = false)
    """)
    filas = con.execute(
        f"SELECT count(*) FROM {tabla} WHERE mes_archivo = ?", [mes]
    ).fetchall()[0][0]
    con.close()

    print(f"OK: {filas} filas de {mes} cargadas en la tabla {tabla}.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Valida el esquema de un mes y lo carga.")
    parser.add_argument("--mes", required=True, help="Mes a cargar, formato AAAA-MM")
    args = parser.parse_args()

    if not cargar_mes(args.mes):
        sys.exit(1)


if __name__ == "__main__":
    main()