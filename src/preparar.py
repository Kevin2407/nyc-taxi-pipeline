"""Prepara lo que Dagster necesita antes de arrancar. Lo corre el servicio "preparar" del compose.

1. Crea la base de datos "dagster" en Postgres, si no existe: ahí Dagster guarda el historial
   de corridas, sus logs y el estado del sensor. Va separada de la base "taxi" de los datos.
2. Genera el manifest de dbt (target/manifest.json) con "dbt parse": es el mapa de modelos,
   tests y dependencias que Dagster lee para dibujar el grafo de assets.
"""
import os
import subprocess

import psycopg2

BASE_DAGSTER = "dagster"


def crear_base_dagster():
    conexion = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )
    conexion.autocommit = True  # CREATE DATABASE no puede ir dentro de una transacción
    with conexion.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (BASE_DAGSTER,))
        if cursor.fetchone():
            print(f"La base '{BASE_DAGSTER}' ya existe.")
        else:
            cursor.execute(f"CREATE DATABASE {BASE_DAGSTER}")
            print(f"Base '{BASE_DAGSTER}' creada.")
    conexion.close()


def generar_manifest_dbt():
    subprocess.run(["dbt", "parse", "--quiet"], check=True)
    print("Manifest de dbt generado.")


if __name__ == "__main__":
    crear_base_dagster()
    generar_manifest_dbt()
