# Hallazgos de la exploración

Mediciones hechas el 16/11/2026 sobre los archivos crudos, antes de escribir el pipeline.
Cada número sale de un script de esta carpeta, que se ejecuta desde la raíz del repo
(por ejemplo `python exploracion/explorar_calidad.py`). El pipeline no usa estos scripts.

Archivos: `yellow_tripdata_2024-03.parquet` (57 MB) y `yellow_tripdata_2025-03.parquet` (67 MB).
Entorno: Python 3.11.16, DuckDB 2.0.0.

## 1. Esquema (`explorar.py`)

| | Marzo 2024 | Marzo 2025 |
| --- | --- | --- |
| Filas | 3.582.628 | 4.145.257 |
| Columnas reales | 19 | 20 |

- La única diferencia de esquema es `cbd_congestion_fee` (DOUBLE), que está en 2025 y no en 2024.
- Las 19 columnas compartidas tienen el mismo nombre y el mismo tipo en los dos archivos.
- Los nombres vienen con mayúsculas mezcladas (`VendorID`, `RatecodeID`, `PULocationID`,
  `DOLocationID`, `Airport_fee`): hay que normalizarlos a snake_case.
- Si se lee el archivo desde una carpeta `year=AAAA/month=MM` sin aclarar nada, DuckDB agrega
  dos columnas `year` (BIGINT) y `month` (VARCHAR) sacadas del nombre de la carpeta. No están
  en el archivo. Para ver el esquema real hay que leer con `hive_partitioning = false`.

## 2. Reglas obligatorias (`explorar_calidad.py`)

| Regla | Marzo 2024 | % | Marzo 2025 | % |
| --- | --- | --- | --- | --- |
| Subida fuera del mes del archivo | 23 | 0,00 | 33 | 0,00 |
| Bajada anterior o igual a la subida | 1.128 | 0,03 | 22.280 | 0,54 |
| Distancia menor o igual a 0 | 87.168 | 2,43 | 103.722 | 2,50 |
| Importe total negativo | 44.311 | 1,24 | 68.686 | 1,66 |
| Pasajeros nulo o 0 | 466.562 | 13,02 | 939.378 | 22,66 |
| Zona de origen inexistente | 0 | 0,00 | 0 | 0,00 |
| Zona de destino inexistente | 0 | 0,00 | 0 | 0,00 |
| Duplicados exactos (`explorar_duplicados.py`) | 0 | 0,00 | 0 | 0,00 |

Una misma fila puede violar más de una regla, así que los porcentajes no se suman.

Observaciones:

- **Pasajeros nulo o 0** es por lejos la más frecuente y su peso cambia mucho entre años
  (13 % contra 22,7 %). Rechazar por esta regla eliminaría casi un cuarto de 2025 y
  distorsionaría la comparación entre meses.
- **Bajada <= subida** son pocas filas, pero se multiplicaron por 20 entre 2024 y 2025.
  No sabemos la causa. Va a "Limitaciones conocidas".
- **Zonas inexistentes y duplicados** dan 0 en los dos meses. Las reglas se implementan igual
  (son obligatorias) y se prueban con datos sintéticos en los tests.
- La tabla de zonas tiene 265 filas. Las dos últimas existen pero no son zonas reales:
  264 (`Unknown`) y 265 (`Outside of NYC`). "Existe en la tabla" no es lo mismo que
  "ubicación conocida".

## 3. Suciedad por tipo de pago (`explorar_pagos.py`)

Códigos de `payment_type` según el diccionario de datos: 0 tarifa flexible, 1 tarjeta,
2 efectivo, 3 sin cargo, 4 disputa.

| Tipo | Viajes 2024 | Pasajeros nulo | Pasajeros 0 | Total negativo | Viajes 2025 | Pasajeros nulo | Pasajeros 0 | Total negativo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 426.190 | 426.190 | 0 | 7 | 916.663 | 916.663 | 0 | 14 |
| 1 | 2.597.102 | 0 | 32.302 | 35 | 2.704.166 | 0 | 18.504 | 25 |
| 2 | 477.660 | 0 | 6.873 | 10.476 | 405.847 | 0 | 3.440 | 17.032 |
| 3 | 23.458 | 0 | 970 | 7.074 | 26.924 | 0 | 625 | 8.719 |
| 4 | 58.218 | 0 | 227 | 26.719 | 91.657 | 0 | 146 | 42.896 |

Observaciones:

- **Todos los pasajeros nulos son del tipo 0, y todo el tipo 0 tiene pasajeros nulo.**
  No es un olvido del chofer: es una categoría entera de viajes que llega sin ese dato.
- **Nulo y 0 son cosas distintas.** El nulo es "el sistema no informa"; el 0 es un valor
  cargado, y aparece repartido en los tipos 1 a 4.
- **Los totales negativos se concentran en disputas y viajes sin cargo**: 46 % de las filas
  del tipo 4 y cerca del 30 % del tipo 3, en los dos años. Con tarjeta casi no existen
  (35 y 25 filas). Son ajustes contables, no viajes con un precio real.

## 4. Para la pregunta (f): de dónde sale el crecimiento

| | Marzo 2024 | Marzo 2025 | Diferencia |
| --- | --- | --- | --- |
| Tipo 0 | 426.190 | 916.663 | +490.473 |
| Tipos 1 a 4 | 3.156.438 | 3.228.594 | +72.156 (+2,3 %) |
| Total | 3.582.628 | 4.145.257 | +562.629 (+15,7 %) |

El 87 % del aumento de viajes es del tipo de pago 0. Los demás tipos crecieron 2,3 %.
Hipótesis a confirmar con los datos ya limpios: buena parte del aumento no es más demanda
de taxis, sino más viajes de un tipo que en 2024 se registraba menos.

Estos números son sobre datos crudos. Los definitivos de `RESULTADOS.md` salen del modelo,
después de aplicar las reglas de calidad.

## 5. Umbrales y reglas propias (`explorar_umbrales.py`)

**Distancia (millas)**

| | Marzo 2024 | Marzo 2025 |
| --- | --- | --- |
| Percentil 99 | 19,9 | 19,4 |
| Percentil 99,9 | 29,3 | 28,8 |
| Percentil 99,99 | 56,2 | 58,0 |
| Máximo | 176.836 | 320.136 |
| Más de 50 | 508 | 595 |
| Más de 100 | 122 | 214 |
| Más de 1.000 | 94 | 165 |

"Percentil 99,99 = 58" quiere decir que el 99,99 % de los viajes mide menos de 58 millas.
Por encima de 100 millas quedan muy pocas filas y casi todas son valores absurdos.

**Viajes con distancia 0**

| | Marzo 2024 | Marzo 2025 |
| --- | --- | --- |
| Con distancia <= 0 | 87.168 | 103.722 |
| De esos, con cobro positivo | 83.065 (95 %) | 98.447 (95 %) |
| Total mediano | 20,22 | 19,77 |

Son viajes que se cobraron normalmente. Falta la distancia, no el viaje.

**Tarifa base (`fare_amount`) menor o igual a 0**

| Tipo de pago | 2024: total negativo | 2024: total >= 0 | 2025: total negativo | 2025: total >= 0 |
| --- | --- | --- | --- | --- |
| 0 | 7 | 14.639 | 14 | 140.469 |
| 1 | 35 | 148 | 25 | 81 |
| 2 | 10.476 | 287 | 17.032 | 619 |
| 3 | 7.074 | 138 | 8.719 | 215 |
| 4 | 26.719 | 233 | 42.896 | 308 |

En los tipos 1 a 4, la tarifa no positiva casi siempre viene con total negativo (ya cubierto
por la regla de total negativo). En el tipo 0 es otra cosa: tarifa negativa con total positivo,
y se multiplicó por 10 entre años. En total son 59.756 filas en 2024 (1,67 %) y 210.378 en
2025 (5,08 %).

**Velocidad promedio (mph)**, sobre viajes con duración y distancia positivas

| | Marzo 2024 | Marzo 2025 |
| --- | --- | --- |
| Mediana | 9,6 | 9,8 |
| Percentil 99 | 34,7 | 34,3 |
| Percentil 99,9 | 48,4 | 46,1 |
| Más de 65 | 1.340 | 1.173 |
| Más de 80 | 1.241 | 1.050 |
| Más de 100 | 1.178 | 961 |

Casi todo lo que supera 65 mph supera también 100: no son taxis rápidos, son datos mal cargados.

**Bajada anterior o igual a la subida.** En 2025, 18.744 de las 22.280 filas son pagos con
tarjeta con exactamente la misma hora de subida y de bajada. Eso explica el salto respecto
de 2024 (1.128 filas).

**Zonas 264 y 265.** Aparecen como origen o destino en 35.374 viajes de 2024 (0,99 %) y
28.415 de 2025 (0,69 %).

## 6. Reglas decididas

Están definidas, con su justificación, en `contracts/reglas_calidad.yaml`.

| Id | Regla | Severidad | 2024-03 | 2025-03 |
| --- | --- | --- | --- | --- |
| R01 | Subida fuera del mes | rechazo | 23 | 33 |
| R02 | Bajada <= subida | rechazo | 1.128 | 22.280 |
| R03 | Distancia <= 0 | advertencia | 87.168 | 103.722 |
| R04 | Distancia > 100 millas | rechazo | 122 | 214 |
| R05 | Total negativo | rechazo | 44.311 | 68.686 |
| R06 | Pasajeros nulo o 0 | advertencia | 466.562 | 939.378 |
| R07 | Zona inexistente | rechazo | 0 | 0 |
| R08 | Duplicado exacto | rechazo | 0 | 0 |
| R09 | Tarifa <= 0 (propia) | advertencia | 59.756 | 210.378 |
| R10 | Velocidad > 80 mph (propia) | rechazo | 1.241 | 1.050 |
| R11 | Zona 264 o 265 (propia) | advertencia | 35.374 | 28.415 |

Resultado esperado al aplicarlas (una fila puede violar varias reglas):

| | Marzo 2024 | Marzo 2025 |
| --- | --- | --- |
| Leídas | 3.582.628 | 4.145.257 |
| A cuarentena | 46.704 (1,30 %) | 92.057 (2,22 %) |
| Aceptadas | 3.535.924 | 4.053.200 |
| Aceptadas con algún flag | 529.328 | 997.980 |

Estos números son la referencia para comprobar `src/calidad.py`: el reporte de calidad del
pipeline tiene que dar lo mismo.
