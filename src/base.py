"""Conexión a Postgres y salida de consultas como tabla de texto."""
import os

import psycopg2


def conectar():
    """Conexión a la base de datos de los datos (variables POSTGRES_* del docker-compose)."""
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )


def consultar(sql, parametros=None):
    """Devuelve (columnas, filas) de una consulta."""
    with conectar() as conexion, conexion.cursor() as cursor:
        cursor.execute(sql, parametros)
        columnas = [columna.name for columna in cursor.description]
        return columnas, cursor.fetchall()


def imprimir_tabla(titulo, sql, parametros=None):
    """Imprime el resultado de una consulta como tabla de texto alineada."""
    columnas, filas = consultar(sql, parametros)
    textos = [[("" if valor is None else str(valor)) for valor in fila] for fila in filas]
    anchos = [max([len(c)] + [len(f[i]) for f in textos]) for i, c in enumerate(columnas)]
    print(f"\n{titulo}")
    print("  " + "  ".join(c.ljust(a) for c, a in zip(columnas, anchos)))
    print("  " + "  ".join("-" * a for a in anchos))
    for fila in textos:
        print("  " + "  ".join(v.ljust(a) for v, a in zip(fila, anchos)))
    if not filas:
        print("  (sin filas)")
