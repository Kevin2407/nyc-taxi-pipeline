"""Etapa de transformación del pipeline."""
import argparse
import sys
from pathlib import Path

import duckdb

from src.ingesta import RUTA_DB

RAIZ_CURADA = Path("data/curated/yellow")

CONSULTA = """
    SELECT
        v.*,
        date_diff('second', v.tpep_pickup_datetime, v.tpep_dropoff_datetime) / 60.0 AS duracion_min,
        CASE WHEN v.trip_distance > 0
             THEN v.trip_distance / (date_diff('second', v.tpep_pickup_datetime, v.tpep_dropoff_datetime) / 3600.0)
        END AS velocidad_mph,
        CAST(v.tpep_pickup_datetime AS DATE) AS fecha_subida,
        hour(v.tpep_pickup_datetime) AS hora_subida,
        isodow(v.tpep_pickup_datetime) AS dia_semana,
        CASE WHEN v.fare_amount > 0 THEN v.tip_amount / v.fare_amount * 100 END AS propina_pct,
        zo.borough AS pu_borough,
        zo.zone AS pu_zone,
        zd.borough AS do_borough,
        zd.zone AS do_zone
    FROM trips_validos v
    LEFT JOIN zonas zo ON v.pu_location_id = zo.location_id
    LEFT JOIN zonas zd ON v.do_location_id = zd.location_id
    WHERE v.mes_archivo = '{mes}'
"""


def ruta_particion(mes):
    anio, numero_mes = mes.split("-")
    return RAIZ_CURADA / f"year={anio}" / f"month={numero_mes}" / "trips.parquet"


def mostrar_particiones():
    duckdb.sql(f"""
        SELECT year, month, count(*) AS filas
        FROM read_parquet('{RAIZ_CURADA}/*/*/*.parquet', hive_partitioning = true)
        GROUP BY ALL
        ORDER BY year, month
    """).show()


def transformar_mes(mes):
    """Escribe la partición curada del mes. Devuelve True si quedó con todas las filas."""
    destino = ruta_particion(mes)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(".tmp")

    con = duckdb.connect(str(RUTA_DB))
    con.execute(f"COPY ({CONSULTA.format(mes=mes)}) TO '{temporal}' (FORMAT parquet)")
    esperadas = con.execute(
        "SELECT count(*) FROM trips_validos WHERE mes_archivo = ?", [mes]
    ).fetchall()[0][0]
    con.close()

    temporal.replace(destino)

    escritas = duckdb.sql(f"SELECT count(*) FROM read_parquet('{destino}')").fetchall()[0][0]
    if escritas != esperadas:
        print(f"ERROR: se esperaban {esperadas} filas y se escribieron {escritas}.")
        return False

    print(f"OK: {escritas} filas escritas en {destino}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Escribe la capa curada de un mes.")
    parser.add_argument("--mes", required=True, help="Mes a transformar, formato AAAA-MM")
    args = parser.parse_args()

    if not transformar_mes(args.mes):
        sys.exit(1)
    mostrar_particiones()


if __name__ == "__main__":
    main()