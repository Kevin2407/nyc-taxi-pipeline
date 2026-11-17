"""Etapa de calidad del pipeline."""
import argparse
import sys
from datetime import datetime
from pathlib import Path

import duckdb
import yaml

from src.esquema import cargar_contrato
from src.ingesta import RUTA_DB, RUTA_ZONAS

RUTA_REGLAS = Path("contracts/reglas_calidad.yaml")


def cargar_reglas():
    with open(RUTA_REGLAS, encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)["reglas"]


def cargar_zonas(con):
    con.execute(f"""
        CREATE OR REPLACE TABLE zonas AS
        SELECT
            "LocationID" AS location_id,
            "Borough" AS borough,
            "Zone" AS zone,
            service_zone
        FROM read_csv('{RUTA_ZONAS}')
    """)


def armar_lista(reglas, severidad):
    """Arma el SQL que devuelve, para cada fila, los ids de las reglas violadas de esa severidad."""
    casos = []
    for regla in reglas:
        if regla["severidad"] != severidad:
            continue
        if regla.get("tipo") == "duplicado":
            condicion = "copia > 1"
        else:
            condicion = regla["condicion"]
        casos.append(f"CASE WHEN {condicion} THEN '{regla['id']}' END")
    return "concat_ws(',', " + ", ".join(casos) + ")"


def evaluar(con, mes, reglas, columnas):
    """Crea la tabla temporal evaluadas: las filas del mes con sus reglas violadas."""
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE evaluadas AS
        SELECT
            *,
            {armar_lista(reglas, "rechazo")} AS reglas_violadas,
            {armar_lista(reglas, "advertencia")} AS flags
        FROM (
            SELECT
                *,
                row_number() OVER (PARTITION BY {", ".join(columnas)}) AS copia
            FROM yellow_trips
            WHERE mes_archivo = '{mes}'
        )
    """)


def separar(con, mes, columnas):
    """Reparte las filas evaluadas entre trips_validos y cuarentena."""
    base = ", ".join(columnas) + ", archivo_origen, mes_archivo"

    con.execute(f"CREATE TABLE IF NOT EXISTS trips_validos AS SELECT {base}, flags FROM evaluadas LIMIT 0")
    con.execute(f"CREATE TABLE IF NOT EXISTS cuarentena AS SELECT {base}, reglas_violadas FROM evaluadas LIMIT 0")

    con.execute("DELETE FROM trips_validos WHERE mes_archivo = ?", [mes])
    con.execute("DELETE FROM cuarentena WHERE mes_archivo = ?", [mes])

    con.execute(f"INSERT INTO trips_validos SELECT {base}, flags FROM evaluadas WHERE reglas_violadas = ''")
    con.execute(f"INSERT INTO cuarentena SELECT {base}, reglas_violadas FROM evaluadas WHERE reglas_violadas <> ''")


def contar(con, tabla, mes):
    return con.execute(f"SELECT count(*) FROM {tabla} WHERE mes_archivo = ?", [mes]).fetchall()[0][0]


def reportar(con, mes, reglas):
    """Guarda e imprime el reporte de calidad del mes. Devuelve (leídas, aceptadas, en cuarentena)."""
    leidas = contar(con, "yellow_trips", mes)
    aceptadas = contar(con, "trips_validos", mes)
    en_cuarentena = contar(con, "cuarentena", mes)

    con.execute("""
        CREATE TABLE IF NOT EXISTS reporte_calidad (
            mes_archivo VARCHAR, filas_leidas BIGINT, filas_aceptadas BIGINT,
            filas_cuarentena BIGINT, fecha_hora TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS reporte_calidad_reglas (
            mes_archivo VARCHAR, regla VARCHAR, nombre VARCHAR, severidad VARCHAR, filas BIGINT
        )
    """)
    con.execute("DELETE FROM reporte_calidad WHERE mes_archivo = ?", [mes])
    con.execute("DELETE FROM reporte_calidad_reglas WHERE mes_archivo = ?", [mes])
    con.execute(
        "INSERT INTO reporte_calidad VALUES (?, ?, ?, ?, ?)",
        [mes, leidas, aceptadas, en_cuarentena, datetime.now()],
    )

    print(f"Reporte de calidad {mes}")
    print(f"  leídas        {leidas:>9}")
    print(f"  aceptadas     {aceptadas:>9}")
    print(f"  en cuarentena {en_cuarentena:>9}")

    for regla in reglas:
        if regla["severidad"] == "rechazo":
            columna = "reglas_violadas"
        else:
            columna = "flags"
        filas = con.execute(
            f"SELECT count(*) FROM evaluadas WHERE contains({columna}, ?)", [regla["id"]]
        ).fetchall()[0][0]
        con.execute(
            "INSERT INTO reporte_calidad_reglas VALUES (?, ?, ?, ?, ?)",
            [mes, regla["id"], regla["nombre"], regla["severidad"], filas],
        )
        print(f"  {regla['id']} {regla['nombre']:24} {regla['severidad']:12} {filas:>9}")

    return leidas, aceptadas, en_cuarentena


def validar_mes(mes):
    """Aplica las reglas al mes. Devuelve True si la reconciliación cierra."""
    reglas = cargar_reglas()
    columnas = []
    for columna in cargar_contrato()["columns"]:
        columnas.append(columna["name"])

    con = duckdb.connect(str(RUTA_DB))
    cargar_zonas(con)
    evaluar(con, mes, reglas, columnas)
    separar(con, mes, columnas)
    leidas, aceptadas, en_cuarentena = reportar(con, mes, reglas)
    con.close()

    if not reconciliacion_cierra(leidas, aceptadas, en_cuarentena):
        print(f"ERROR de reconciliación: {leidas} leídas != {aceptadas} aceptadas + {en_cuarentena} en cuarentena.")
        return False

    print("OK: la reconciliación cierra (leídas = aceptadas + cuarentena).")
    return True

def reconciliacion_cierra(leidas, aceptadas, en_cuarentena):
    return leidas == aceptadas + en_cuarentena


def main():
    parser = argparse.ArgumentParser(description="Aplica las reglas de calidad a un mes.")
    parser.add_argument("--mes", required=True, help="Mes a validar, formato AAAA-MM")
    args = parser.parse_args()

    if not validar_mes(args.mes):
        sys.exit(1)


if __name__ == "__main__":
    main()