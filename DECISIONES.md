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
