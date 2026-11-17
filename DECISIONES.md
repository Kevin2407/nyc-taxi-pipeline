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
| 2026-11-16 | El contrato (`contracts/yellow_schema.yaml`) describe el destino: nombres en snake_case y los mismos tipos que traen los archivos | No inventamos conversiones de tipo que haya que defender. El contrato tiene número de versión y su historial queda en Git |
| 2026-11-16 | snake_case con una función general (`a_snake_case`) y no con una tabla fija de equivalencias | Normaliza también una columna que aparezca mañana. Verificado con `VendorID`, `RatecodeID`, `PULocationID`, `DOLocationID` y `Airport_fee` |
| 2026-11-16 | `cbd_congestion_fee` está marcada `opcional: true` en el contrato | Distingue "falta una columna prevista" (2024, se sigue) de "el archivo está roto" (falta una obligatoria, se frena) |
| 2026-11-16 | `cbd_congestion_fee` vale nulo en 2024, no 0 | El cargo no existía: 0 significaría "se cobró cero". Además los promedios ignoran los nulos y un 0 los bajaría |
| 2026-11-16 | Columna nueva que no está en el contrato: se reporta, no se carga y el pipeline sigue | Lo conocido sigue siendo válido. Incorporarla es una decisión humana: editar el contrato y subir la versión |
| 2026-11-16 | Columna obligatoria faltante o tipo distinto al contrato: el pipeline frena con código de salida 1 | Convertir tipos en silencio puede perder datos. Probado cambiando `trip_distance` a INTEGER en el contrato |
| 2026-11-16 | Los dos meses se unen en la tabla `yellow_trips` de `data/taxi.duckdb`, con `archivo_origen` y `mes_archivo` | La cuarentena pide el archivo de origen y la regla de "subida fuera del mes" necesita saber el mes del archivo |
| 2026-11-16 | Cargar un mes borra antes sus filas (`DELETE ... WHERE mes_archivo`) | Idempotencia: cargamos 2025-03 dos veces y quedó en 4.145.257 filas; 2024-03 no se tocó |
| 2026-11-16 | El SQL de carga se genera recorriendo el contrato | Las columnas están escritas en un solo lugar; si cambia el contrato no hay que tocar código |
| 2026-11-16 | Criterio de severidad: rechazo si la fila describe algo imposible o no se puede asignar a un mes o zona; advertencia si un dato es dudoso o falta pero el viaje existió y se cobró | Un criterio único evita decidir regla por regla "a ojo" y se puede explicar en una frase. Con él se rechaza el 1,30 % de 2024-03 y el 2,22 % de 2025-03 |
| 2026-11-16 | R03 distancia <= 0 es advertencia, no rechazo | Lo medimos: el 95 % de esos viajes tiene cobro positivo, con total mediano de unos 20 dólares. Falta la distancia, no el viaje. Antes de medir pensábamos rechazarla |
| 2026-11-16 | Máximo de distancia: 100 millas (R04, rechazo) | El 99,99 % de los viajes mide menos de 58 millas. Sobre 100 quedan 122 y 214 filas, casi todas de más de 1.000 millas |
| 2026-11-16 | R06 pasajeros nulo o 0 es advertencia | Afecta al 13 % y al 22,7 %; los nulos son todo el tipo de pago 0. Rechazar distorsionaría la comparación entre años, y el dato no se usa en ningún cálculo |
| 2026-11-16 | La regla de distancia de la consigna se parte en dos (R03 y R04) | Las dos mitades tienen causas y severidades distintas: sin distancia registrada contra distancia absurda |
| 2026-11-16 | Regla propia R09: tarifa base <= 0, advertencia | En 2025-03 hay 140.469 viajes de tipo de pago 0 con tarifa negativa y total positivo. El viaje se cobró, pero la tarifa no sirve: la propina porcentual queda nula y la tarifa media se calcula sin ellos |
| 2026-11-16 | Regla propia R10: velocidad promedio > 80 mph, rechazo | El 99,9 % promedia menos de 49 mph y el límite máximo del estado es 65. Más de 80 significa distancia u horarios mal cargados |
| 2026-11-16 | Regla propia R11: zona 264 o 265, advertencia | Existen en la tabla (pasan R07) pero no son un lugar real. El flag permite sacarlas de los rankings por zona |
| 2026-11-16 | R08 duplicados: se conserva una copia y se rechazan las demás | Rechazar todas las copias borraría el viaje; conservar una lo cuenta una sola vez |
| 2026-11-16 | Severidades, umbrales y reglas propias los propuso Claude a pedido nuestro, a partir de las mediciones de `exploracion/` | Queda declarado; las justificaciones están en `contracts/reglas_calidad.yaml` y las revisamos para poder defenderlas |
