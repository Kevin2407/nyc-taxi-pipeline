"""Corre dbt desde Python. Lo usan calidad.py, transformacion.py y modelo.py para correr
solo los modelos de su etapa. (Dagster corre dbt por su cuenta, con dagster-dbt.)"""
import json

from dbt.cli.main import dbtRunner


def correr_dbt(comando, seleccion, mes):
    """comando: "build" (modelos + tests) o "test". seleccion: lista de selectores de dbt,
    por ejemplo ["+calidad"] (los modelos de sql/calidad y todo lo que necesitan antes)."""
    # cautious: corre solo los tests cuyas tablas están todas en la selección. Sin esto, al correr
    # calidad dbt también intentaría un test que compara con curado, que todavía no existe.
    argumentos = [comando, "--select", *seleccion, "--indirect-selection", "cautious",
                  "--vars", json.dumps({"mes": mes})]
    print("dbt " + " ".join(argumentos))
    return dbtRunner().invoke(argumentos).success
