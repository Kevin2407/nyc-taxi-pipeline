"""Pipeline NYC Taxi: un módulo por etapa de la consigna.

    ingesta.py         Parte 1  descarga con hash, reintentos y log; carga a Postgres con dlt
    esquema.py         Parte 2  contrato de esquema: comparación antes de cargar y ajuste de columnas
    calidad.py         Parte 3  reglas, cuarentena, reporte y reconciliación (modelos dbt de sql/calidad)
    transformacion.py  Parte 4  capa curada (dbt, sql/curado) y Parquet particionado (Polars)
    modelo.py          Parte 5  modelo estrella y preguntas (dbt, sql/modelo y sql/preguntas)

    definitions.py     orquestación con Dagster (job pipeline_completo y sensor)
    metricas.py        métricas de cada etapa para Prometheus/Grafana
    base.py, correr_dbt.py, meses.py, preparar.py   utilidades
"""
