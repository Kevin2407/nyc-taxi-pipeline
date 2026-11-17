"""Etapa de modelo del pipeline."""
import argparse
from pathlib import Path

import duckdb

from src.ingesta import RUTA_DB
from src.transformacion import RAIZ_CURADA

CARPETA_MODELO = Path("sql/modelo")
CARPETA_PREGUNTAS = Path("sql/preguntas")
TABLAS_MODELO = ["dim_zone", "dim_date", "fact_trips", "agg_zone_hour"]


def mes_anterior(mes):
    anio, numero_mes = mes.split("-")
    return f"{int(anio) - 1}-{numero_mes}"


def construir_modelo(con):
    curada = f"{RAIZ_CURADA}/*/*/*.parquet"
    for archivo in sorted(CARPETA_MODELO.glob("*.sql")):
        print("Ejecutando", archivo)
        con.execute(archivo.read_text(encoding="utf-8").format(curada=curada))

    for tabla in TABLAS_MODELO:
        filas = con.execute(f"SELECT count(*) FROM {tabla}").fetchall()[0][0]
        print(f"  {tabla:15} {filas:>9} filas")


def responder_preguntas(con, mes):
    anterior = mes_anterior(mes)
    for archivo in sorted(CARPETA_PREGUNTAS.glob("*.sql")):
        print()
        print(f"===== {archivo.name}  ({mes} contra {anterior}) =====")
        consulta = archivo.read_text(encoding="utf-8").format(mes=mes, mes_anterior=anterior)
        con.sql(consulta).show(max_width=200)


def main():
    parser = argparse.ArgumentParser(description="Construye el modelo estrella y responde las preguntas.")
    parser.add_argument("--mes", required=True, help="Mes asignado, formato AAAA-MM")
    args = parser.parse_args()

    con = duckdb.connect(str(RUTA_DB))
    construir_modelo(con)
    responder_preguntas(con, args.mes)
    con.close()


if __name__ == "__main__":
    main()