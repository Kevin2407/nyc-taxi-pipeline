"""Orquestación con Dagster.

Arma el pipeline completo como "assets" (los datos que produce cada paso) y define:
  - el job pipeline_completo: ingesta -> dbt (calidad, curado, modelo, preguntas) -> Parquet,
    para el mes asignado (variable MES) y el mismo mes del año anterior;
  - el sensor nuevo_mes_publicado: cada 6 horas se fija si la TLC publicó el mes
    siguiente y, si apareció, lanza el job para ese mes.

Dagster carga este archivo desde dagster/workspace.yaml.
"""
import json
import os
from pathlib import Path

import dagster as dg
import requests
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, DbtProject, dbt_assets, get_asset_key_for_model

import pyarrow.parquet as pq

from pipeline import exportar, ingesta, metricas
from pipeline.meses import es_mes_valido, mes_anterior, mes_siguiente

MES_POR_DEFECTO = os.environ.get("MES", "2025-03")
DIRECTORIO_DBT = Path(__file__).resolve().parent.parent / "dbt"

# El proyecto dbt. Dagster lee su manifest (dbt/target/manifest.json, lo genera "dbt parse")
# y crea un asset por cada modelo, seed y test.
proyecto_dbt = DbtProject(project_dir=DIRECTORIO_DBT)


class ConfigMes(dg.Config):
    """Configuración de cada corrida: el mes asignado. El de comparación se calcula."""

    mes: str = MES_POR_DEFECTO


def meses_de_la_corrida(mes):
    if not es_mes_valido(mes):
        raise dg.Failure(f"El mes '{mes}' no tiene formato AAAA-MM.")
    return [mes, mes_anterior(mes)]


# ---------- Paso 1: ingesta (dlt) ----------

@dg.multi_asset(
    specs=[
        dg.AssetSpec(["raw", "yellow_trips"], description="Viajes cargados por dlt, ajustados al contrato de esquema."),
        dg.AssetSpec(["raw", "zonas"], description="Tabla de zonas de la TLC."),
    ],
    group_name="ingesta",
)
def ingesta_dlt(context: dg.AssetExecutionContext, config: ConfigMes):
    """Descarga y carga el mes asignado y el del año anterior (pipeline/ingesta.py)."""
    for mes in meses_de_la_corrida(config.mes):
        context.log.info(f"Ingesta de {mes}")
        with metricas.medir("ingesta", mes, context.log.info) as medicion:
            if not ingesta.ingestar_mes(mes):
                raise dg.Failure(f"Falló la ingesta de {mes}. Ver raw.ingestion_log y el log de esta corrida.")
            _, archivo = ingesta.armar_rutas(mes)
            medicion.filas = ingesta.contar_filas(archivo)
    yield dg.MaterializeResult(asset_key=["raw", "yellow_trips"], metadata={"meses": ", ".join(meses_de_la_corrida(config.mes))})
    yield dg.MaterializeResult(asset_key=["raw", "zonas"])


# ---------- Pasos 2 a 5: dbt ----------

class TraductorDbt(DagsterDbtTranslator):
    """Agrupa cada modelo de dbt según su carpeta (staging, calidad, curado, marts, preguntas),
    así el grafo de Dagster muestra las etapas del pipeline. El seed de reglas va con calidad."""

    def get_group_name(self, dbt_resource_props):
        if dbt_resource_props["resource_type"] == "seed":
            return "calidad"
        return dbt_resource_props["fqn"][1]  # ['taxi', '<carpeta>', '<modelo>']


@dbt_assets(manifest=proyecto_dbt.manifest_path, dagster_dbt_translator=TraductorDbt())
def modelos_dbt(context: dg.AssetExecutionContext, dbt: DbtCliResource, config: ConfigMes):
    """dbt build: staging, calidad, curado, modelo estrella y preguntas, con todos sus tests.
    Si un test falla (por ejemplo, la reconciliación), el paso falla y el pipeline se corta."""
    variables = json.dumps({"mes": config.mes})
    with metricas.medir("dbt", config.mes, context.log.info) as medicion:
        invocacion = dbt.cli(["build", "--vars", variables], context=context)
        yield from invocacion.stream()
        resultados = invocacion.get_artifact("run_results.json")
        medicion.filas = metricas.filas_escritas_por_dbt(resultados)
    metricas.publicar_modelos_dbt(config.mes, resultados, context.log.info)


# ---------- Paso 6: capa curada en Parquet ----------

@dg.asset(
    deps=[get_asset_key_for_model([modelos_dbt], "trips_curados")],
    group_name="curado",
    description="data/curated/yellow/year=AAAA/month=MM/trips.parquet (pipeline/exportar.py).",
)
def capa_curada_parquet(context: dg.AssetExecutionContext, config: ConfigMes):
    for mes in meses_de_la_corrida(config.mes):
        context.log.info(f"Exportación de {mes}")
        with metricas.medir("exportacion", mes, context.log.info) as medicion:
            if not exportar.exportar_mes(mes):
                raise dg.Failure(f"Falló la exportación de {mes}.")
            medicion.filas = pq.ParquetFile(exportar.ruta_particion(mes)).metadata.num_rows


# ---------- Job y sensor ----------

pipeline_completo = dg.define_asset_job(
    "pipeline_completo",
    selection=dg.AssetSelection.all(),
    description="Ingesta, calidad, curado, modelo y preguntas para el mes asignado y el del año anterior.",
)


def config_para(mes):
    """Configuración de una corrida para un mes: el mismo valor para los tres pasos."""
    return {"ops": {nombre: {"config": {"mes": mes}} for nombre in ["ingesta_dlt", "modelos_dbt", "capa_curada_parquet"]}}


@dg.sensor(
    job=pipeline_completo,
    minimum_interval_seconds=6 * 60 * 60,
    default_status=dg.DefaultSensorStatus.STOPPED,
    description="Cada 6 horas se fija si la TLC publicó el mes siguiente; si apareció, lo procesa.",
)
def nuevo_mes_publicado(context: dg.SensorEvaluationContext):
    # El cursor guarda el último mes que lanzó el sensor; la primera vez parte del mes asignado.
    ultimo = context.cursor or MES_POR_DEFECTO
    candidato = mes_siguiente(ultimo)
    url, _ = ingesta.armar_rutas(candidato)

    respuesta = requests.head(url, timeout=30)
    if respuesta.status_code != 200:
        return dg.SkipReason(f"{candidato} todavía no está publicado (HTTP {respuesta.status_code}).")

    context.update_cursor(candidato)
    return dg.RunRequest(run_key=candidato, run_config=config_para(candidato))


defs = dg.Definitions(
    assets=[ingesta_dlt, modelos_dbt, capa_curada_parquet],
    jobs=[pipeline_completo],
    sensors=[nuevo_mes_publicado],
    resources={"dbt": DbtCliResource(project_dir=proyecto_dbt)},
)
