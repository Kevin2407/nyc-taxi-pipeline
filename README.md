# Pipeline NYC Taxi

## Cómo instalar y ejecutar

## Arquitectura

## Decisiones

## Limitaciones conocidas

- La ingesta reintenta ante cualquier error de descarga, también los que no se arreglan reintentando. Un mes que todavía no está publicado devuelve `403 Forbidden` (probado con `2031-01`) y el script espera 14 segundos en total antes de registrar el error.
- El `ingestion_log` vive en `data/taxi.duckdb`. Si se borra la carpeta `data/`, se pierde el historial y la siguiente corrida descarga todo de nuevo.

## Tiempo de ejecución y pico de RAM

## Declaración de uso de IA

| Herramienta | Para qué se usó |
| --- | --- |
| GitHub Copilot | Generar la estructura inicial de carpetas y archivos vacíos (PR #1) |
| Claude | Guía paso a paso, explicación de conceptos y herramientas, propuesta de código que escribimos y probamos nosotros, y redacción de `exploracion/HALLAZGOS.md` y `DECISIONES.md` a partir de nuestras mediciones |
