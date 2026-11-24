"""Parte 3 de la consigna: calidad de datos y cuarentena.

Las reglas viven en dos lugares, a propósito:
    contracts/reglas_calidad.csv      id, descripción, severidad, umbral y justificación de cada regla
    sql/calidad/trips_evaluados.sql   la condición SQL de cada regla
dbt arma, a partir de raw.yellow_trips (pasando por sql/staging):
    calidad.trips_validos            filas aceptadas, con las advertencias en la columna flags
    calidad.cuarentena               filas rechazadas: fila original, archivo de origen y reglas violadas
    calidad.reporte_calidad          por mes: leídas, aceptadas y en cuarentena
    calidad.reporte_calidad_reglas   por mes y regla: cuántas filas la violan
y corre el test de reconciliación (tests/dbt/reconciliacion.sql): si leídas no es igual a
aceptadas + cuarentena, el test falla y la etapa termina con error.

Uso (desde el contenedor):
    python -m src.calidad --mes 2025-03                   corre la etapa y muestra el reporte
    python -m src.calidad --mes 2025-03 --solo-reporte    solo muestra el reporte (para la demo)
"""
import argparse
import sys

from src.base import imprimir_tabla
from src.correr_dbt import correr_dbt
from src.meses import es_mes_valido, mes_anterior


def validar(mes):
    """Corre staging y calidad con dbt (con todos sus tests). Devuelve True si todo pasó."""
    return correr_dbt("build", ["+calidad"], mes)


def mostrar_reporte(mes):
    meses = (mes, mes_anterior(mes))
    imprimir_tabla(
        "Reporte de calidad por mes (calidad.reporte_calidad)",
        "SELECT mes_archivo, filas_leidas, filas_aceptadas, filas_cuarentena, pct_cuarentena, "
        "filas_leidas = filas_aceptadas + filas_cuarentena AS reconciliacion_cierra "
        "FROM calidad.reporte_calidad WHERE mes_archivo IN %s ORDER BY mes_archivo",
        (meses,),
    )
    imprimir_tabla(
        "Filas por regla (calidad.reporte_calidad_reglas)",
        "SELECT regla, nombre, severidad, "
        "sum(filas) FILTER (WHERE mes_archivo = %s) AS mes_anterior, "
        "sum(filas) FILTER (WHERE mes_archivo = %s) AS mes_asignado "
        "FROM calidad.reporte_calidad_reglas GROUP BY regla, nombre, severidad ORDER BY regla",
        (meses[1], meses[0]),
    )
    imprimir_tabla(
        f"Una fila en cuarentena por cada combinación de reglas violadas ({mes})",
        "SELECT DISTINCT ON (reglas_violadas) reglas_violadas, archivo_origen, tpep_pickup_datetime, "
        "tpep_dropoff_datetime, trip_distance, total_amount, pu_location_id, do_location_id "
        "FROM calidad.cuarentena WHERE mes_archivo = %s ORDER BY reglas_violadas, trip_distance DESC",
        (mes,),
    )


def main():
    parser = argparse.ArgumentParser(description="Reglas de calidad, cuarentena, reporte y reconciliación.")
    parser.add_argument("--mes", required=True, help="Mes asignado, formato AAAA-MM")
    parser.add_argument("--solo-reporte", action="store_true", help="No corre dbt; solo muestra el reporte")
    args = parser.parse_args()
    if not es_mes_valido(args.mes):
        parser.error("--mes tiene que tener formato AAAA-MM, por ejemplo 2025-03")

    if not args.solo_reporte and not validar(args.mes):
        print("ERROR: la etapa de calidad falló (ver el test que no pasó, por ejemplo la reconciliación).")
        sys.exit(1)
    mostrar_reporte(args.mes)


if __name__ == "__main__":
    main()
