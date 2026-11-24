"""Parte 5 de la consigna: modelo estrella y preguntas de negocio.

dbt arma, a partir de curado.trips_curados:
    sql/modelo/    dim_zone, dim_date, fact_trips y agg_zone_hour (esquema modelo)
    sql/preguntas/ una tabla por pregunta, de pregunta_a_... a pregunta_f_... (esquema preguntas)
con tests de claves, de relaciones entre la tabla de hechos y las dimensiones y de que la
tabla agregada cuadre con la de hechos. Después este módulo muestra las 6 respuestas.

Uso (desde el contenedor):
    python -m src.modelo --mes 2025-03                     corre la etapa y muestra las respuestas
    python -m src.modelo --mes 2025-03 --solo-respuestas   solo muestra las respuestas
"""
import argparse
import sys

from src.base import imprimir_tabla
from src.correr_dbt import correr_dbt
from src.meses import es_mes_valido

PREGUNTAS = [
    ("a", "pregunta_a_top10_zonas_origen", "Las 10 zonas de origen con más viajes y su variación"),
    ("b", "pregunta_b_hora_mayor_ingreso", "La hora del día con mayor ingreso promedio por viaje"),
    ("c", "pregunta_c_cbd_congestion", "Viajes con cbd_congestion_fee > 0 y las 5 zonas con mayor proporción"),
    ("d", "pregunta_d_propina_por_pago", "Propina promedio (% de la tarifa) por tipo de pago"),
    ("e", "pregunta_e_aeropuertos", "Viajes y tarifa media desde o hacia JFK y LaGuardia"),
    ("f", "pregunta_f_variacion_meses", "Variación de viajes y de tarifa media entre los dos meses"),
]


def construir(mes):
    return correr_dbt("build", ["modelo", "preguntas"], mes)


def mostrar_respuestas():
    for letra, tabla, titulo in PREGUNTAS:
        imprimir_tabla(f"({letra}) {titulo}  [sql/preguntas/{tabla}.sql]", f"SELECT * FROM preguntas.{tabla}")


def main():
    parser = argparse.ArgumentParser(description="Modelo estrella y preguntas de negocio.")
    parser.add_argument("--mes", required=True, help="Mes asignado, formato AAAA-MM")
    parser.add_argument("--solo-respuestas", action="store_true", help="No corre dbt; solo muestra las respuestas")
    args = parser.parse_args()
    if not es_mes_valido(args.mes):
        parser.error("--mes tiene que tener formato AAAA-MM, por ejemplo 2025-03")

    if not args.solo_respuestas and not construir(args.mes):
        print("ERROR: dbt no pudo construir el modelo o las preguntas.")
        sys.exit(1)
    mostrar_respuestas()


if __name__ == "__main__":
    main()
