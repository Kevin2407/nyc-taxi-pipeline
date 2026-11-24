"""Métricas de cada etapa del pipeline, para Prometheus y Grafana.

Uso dentro de una etapa:
    with medir("ingesta", "2025-03", log) as medicion:
        ... el trabajo ...
        medicion.filas = 4145257

Mientras la etapa corre, un hilo mide cada medio segundo la RAM del proceso y de sus
subprocesos (por ejemplo, dbt) con psutil y se queda con el pico. Al terminar, bien o
mal, publica en el Pushgateway:
    pipeline_etapa_duracion_segundos      cuánto tardó
    pipeline_etapa_ram_pico_bytes         pico de memoria
    pipeline_etapa_cpu_segundos           tiempo de CPU usado
    pipeline_etapa_filas                  filas procesadas (si la etapa lo informa)
    pipeline_etapa_exito                  1 si terminó bien, 0 si falló
    pipeline_etapa_fin_timestamp_segundos cuándo terminó
con las etiquetas etapa y mes. Prometheus lee el Pushgateway cada 5 s y Grafana lo dibuja.

¿Por qué Pushgateway? Prometheus "sale a buscar" las métricas cada tantos segundos, y una
etapa que dura poco puede terminar antes de que pase. La etapa deja sus números en el
Pushgateway y Prometheus los encuentra ahí.
"""
import os
import threading
import time
from contextlib import contextmanager

import psutil
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

URL_PUSHGATEWAY = os.environ.get("PUSHGATEWAY_URL")
NOMBRE_JOB = "pipeline_nyc_taxi"
INTERVALO_MUESTREO = 0.5  # segundos entre mediciones de RAM


class Medicion:
    """Lo que la etapa puede completar mientras corre."""

    def __init__(self):
        self.filas = None
        self.ram_pico = 0


def ram_del_proceso_y_sus_hijos(proceso):
    total = proceso.memory_info().rss
    for hijo in proceso.children(recursive=True):
        try:
            total += hijo.memory_info().rss
        except psutil.Error:
            pass  # el subproceso terminó justo mientras lo medíamos
    return total


def cpu_acumulada(proceso):
    """CPU del proceso más la de los subprocesos que ya terminaron (como dbt)."""
    tiempos = proceso.cpu_times()
    return tiempos.user + tiempos.system + tiempos.children_user + tiempos.children_system


@contextmanager
def medir(etapa, mes, log=print):
    proceso = psutil.Process()
    medicion = Medicion()
    terminar = threading.Event()

    def muestrear():
        while not terminar.is_set():
            try:
                medicion.ram_pico = max(medicion.ram_pico, ram_del_proceso_y_sus_hijos(proceso))
            except psutil.Error:
                pass
            terminar.wait(INTERVALO_MUESTREO)

    hilo = threading.Thread(target=muestrear, daemon=True)
    hilo.start()
    inicio = time.time()
    cpu_inicio = cpu_acumulada(proceso)
    exito = False
    try:
        yield medicion
        exito = True
    finally:
        terminar.set()
        hilo.join()
        duracion = time.time() - inicio
        cpu = cpu_acumulada(proceso) - cpu_inicio
        log(
            f"Métricas de {etapa} ({mes}): {duracion:.1f} s, RAM pico {medicion.ram_pico / 1e6:.0f} MB, "
            f"CPU {cpu:.1f} s, filas {medicion.filas}, {'ok' if exito else 'FALLÓ'}"
        )
        publicar(etapa, mes, duracion, medicion.ram_pico, cpu, medicion.filas, exito, log)


def publicar(etapa, mes, duracion, ram_pico, cpu, filas, exito, log=print):
    if not URL_PUSHGATEWAY:
        log("PUSHGATEWAY_URL no está definida: las métricas no se publican.")
        return
    registro = CollectorRegistry()
    Gauge("pipeline_etapa_duracion_segundos", "Duración de la etapa", registry=registro).set(duracion)
    Gauge("pipeline_etapa_ram_pico_bytes", "Pico de RAM de la etapa y sus subprocesos", registry=registro).set(ram_pico)
    Gauge("pipeline_etapa_cpu_segundos", "Tiempo de CPU de la etapa", registry=registro).set(cpu)
    if filas is not None:
        Gauge("pipeline_etapa_filas", "Filas procesadas por la etapa", registry=registro).set(filas)
    Gauge("pipeline_etapa_exito", "1 si la etapa terminó bien, 0 si falló", registry=registro).set(1 if exito else 0)
    Gauge("pipeline_etapa_fin_timestamp_segundos", "Momento en que terminó la etapa", registry=registro).set_to_current_time()
    enviar(registro, {"etapa": etapa, "mes": mes}, log)


def filas_escritas_por_dbt(resultados):
    """Suma las filas que escribieron los modelos de dbt (run_results.json)."""
    total = 0
    for resultado in resultados["results"]:
        if resultado["unique_id"].startswith("model."):
            total += resultado.get("adapter_response", {}).get("rows_affected") or 0
    return total


def publicar_modelos_dbt(mes, resultados, log=print):
    """Duración de cada modelo y test de dbt, para ver cuál es el más pesado."""
    if not URL_PUSHGATEWAY:
        return
    registro = CollectorRegistry()
    duracion = Gauge(
        "pipeline_dbt_modelo_duracion_segundos", "Duración de cada modelo o test de dbt",
        ["modelo", "tipo"], registry=registro,
    )
    for resultado in resultados["results"]:
        tipo, _, nombre = resultado["unique_id"].split(".", 2)
        duracion.labels(modelo=nombre.split(".")[-1], tipo=tipo).set(resultado["execution_time"])
    enviar(registro, {"etapa": "dbt_modelos", "mes": mes}, log)


def enviar(registro, agrupacion, log):
    # Si el Pushgateway no responde, el pipeline sigue: las métricas no pueden romper los datos.
    try:
        push_to_gateway(URL_PUSHGATEWAY, job=NOMBRE_JOB, grouping_key=agrupacion, registry=registro)
    except Exception as error:
        log(f"No se pudieron publicar las métricas en {URL_PUSHGATEWAY}: {error}")
