# Decisiones

| Fecha | Decisión | Por qué |
| --- | --- | --- |
| 2026-11-15 | Comparar marzo 2025 contra marzo 2024 | La consigna gira alrededor de `cbd_congestion_fee`, que existe en 2025 y no en 2024. Evitamos enero porque el cargo empezó el 5/1/2025 y el mes queda partido |
| 2026-11-15 | Python + DuckDB como motor | DuckDB consulta Parquet directo desde el disco sin cargarlo entero en memoria, así que entra en 8 GB. No necesita servidor ni Docker |
| 2026-11-15 | La estructura de carpetas la generó GitHub Copilot (PR #1) | Solo el esqueleto, sin lógica. Se declara en el README |
| 2026-11-16 | Entorno virtual `venv` con Python 3.11 | Se reproduce igual en cualquier máquina con `python3 -m venv .venv`, sin depender de Anaconda. Evitamos Python 3.14 por ser muy nuevo |
| 2026-11-16 | Leer la capa cruda con `hive_partitioning = false` | Si no, DuckDB agrega `year` y `month` desde el nombre de la carpeta y el esquema que vemos no es el real del archivo |
| 2026-11-16 | Las reglas de calidad se definen en `contracts/reglas_calidad.yaml` y se aplican en `src/calidad.py` | Las decisiones (severidad, condición, justificación) quedan explícitas y versionadas, separadas del código. Cambiar una severidad no requiere tocar código |
| 2026-11-16 | Los scripts de exploración viven en `exploracion/` y no forman parte del pipeline | Sirven para medir antes de decidir umbrales. Los resultados están en `exploracion/HALLAZGOS.md` |
| 2026-11-16 | El `ingestion_log` es una tabla dentro de `data/taxi.duckdb` | Se consulta con SQL y vive en el mismo archivo donde después va el modelo. Al estar en `data/` no se sube al repo |
| 2026-11-16 | Idempotencia de la ingesta: no se descarga si el archivo existe y su SHA-256 coincide con el de la última descarga `ok` del log | Mirar solo si el archivo existe no alcanza: puede existir y estar corrupto. Lo probamos agregando bytes a un archivo y el script lo volvió a bajar con el hash original |
| 2026-11-16 | Cuando la ingesta saltea una descarga no agrega fila al log | El log registra descargas. Así una segunda corrida no cambia ningún conteo, que es lo que hay que mostrar en la demo |
| 2026-11-16 | Descarga en bloques de 1 MB a un archivo `.tmp` que se renombra al terminar | Nunca hay más de 1 MB en memoria, y un corte a mitad de descarga no deja un archivo incompleto con el nombre definitivo |
| 2026-11-16 | 3 reintentos con esperas de 2, 4 y 8 segundos; si falla, fila `error` en el log y código de salida 1 | Lo pide la consigna. La espera creciente evita insistir sobre un servidor saturado, y el código distinto de 0 hace que `make` corte el pipeline |
| 2026-11-16 | La tabla de zonas usa la misma función `ingestar` que los meses | "Una sola vez" es un caso de la misma idempotencia; no hace falta código aparte |
