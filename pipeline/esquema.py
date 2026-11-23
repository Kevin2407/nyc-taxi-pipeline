"""Parte 2 de la consigna: contrato de esquema.

Antes de cargar un archivo, compara su esquema real contra contracts/yellow_schema.yaml
y reporta columnas faltantes, nuevas y con tipo distinto. Después, durante la carga,
deja cada lote con exactamente las columnas del contrato, en snake_case y en su orden.
"""
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from dlt.common.normalizers.naming.snake_case import NamingConvention

RUTA_CONTRATO = Path("contracts/yellow_schema.yaml")
NOMBRES_DLT = NamingConvention()

COLUMNAS_REPORTE = {
    "archivo": {"data_type": "text"},
    "version_contrato": {"data_type": "bigint"},
    "faltantes_obligatorias": {"data_type": "text"},
    "faltantes_opcionales": {"data_type": "text"},
    "nuevas": {"data_type": "text"},
    "tipos_distintos": {"data_type": "text"},
    "resultado": {"data_type": "text"},
    "fecha_hora": {"data_type": "timestamp"},
}


def cargar_contrato():
    with open(RUTA_CONTRATO, encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)


def a_snake_case(nombre):
    """La misma regla que usa dlt para nombrar columnas: PULocationID -> pu_location_id."""
    return NOMBRES_DLT.normalize_identifier(nombre)


def comparar(esquema_arrow, contrato):
    """Compara el esquema del archivo contra el contrato. Devuelve las cuatro listas de diferencias."""
    reales = {}
    for campo in esquema_arrow:
        reales[a_snake_case(campo.name)] = str(campo.type)

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


def cumple(reporte):
    """Se frena solo si falta una columna obligatoria o cambió un tipo.
    Una opcional faltante se carga nula; una columna nueva se reporta y se ignora."""
    return not reporte["faltantes_obligatorias"] and not reporte["tipos_distintos"]


def validar_archivo(pipeline, ruta, contrato):
    """Compara el archivo contra el contrato, lo muestra, lo guarda en raw.reporte_esquema
    y devuelve True si se puede cargar."""
    reporte = comparar(pq.read_schema(ruta), contrato)
    ok = cumple(reporte)

    print(f"Esquema de {ruta.name} contra el contrato v{contrato['version']}:")
    for tipo_diferencia, columnas in reporte.items():
        print(f"  {tipo_diferencia:24} {', '.join(columnas) if columnas else 'ninguna'}")
    print("  resultado:", "cumple, se carga" if ok else "NO CUMPLE, no se carga")

    fila = {
        "archivo": ruta.name,
        "version_contrato": contrato["version"],
        "faltantes_obligatorias": ", ".join(reporte["faltantes_obligatorias"]),
        "faltantes_opcionales": ", ".join(reporte["faltantes_opcionales"]),
        "nuevas": ", ".join(reporte["nuevas"]),
        "tipos_distintos": ", ".join(reporte["tipos_distintos"]),
        "resultado": "ok" if ok else "rechazado",
        "fecha_hora": datetime.now(),
    }
    pipeline.run([fila], table_name="reporte_esquema", write_disposition="append", columns=COLUMNAS_REPORTE)
    return ok


def ajustar_al_contrato(tabla, contrato):
    """Deja un lote con las columnas del contrato, en snake_case y en su orden.
    - Una columna opcional que falta (cbd_congestion_fee en 2024) se agrega nula, con su tipo.
    - Una columna que no está en el contrato queda afuera.
    """
    tabla = tabla.rename_columns([a_snake_case(nombre) for nombre in tabla.column_names])

    columnas = []
    nombres = []
    for columna in contrato["columns"]:
        nombre = columna["name"]
        if nombre in tabla.column_names:
            columnas.append(tabla[nombre])
        else:
            columnas.append(pa.nulls(tabla.num_rows, pa.type_for_alias(columna["type"])))
        nombres.append(nombre)

    return pa.table(columnas, names=nombres)
