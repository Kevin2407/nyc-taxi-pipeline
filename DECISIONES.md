# Decisiones

Cada decisión de diseño del pipeline, con su porqué. Las mediciones que respaldan las reglas de calidad están en `exploracion/HALLAZGOS.md`.

## Alcance y stack

| Decisión | Por qué |
| --- | --- |
| Comparar marzo 2025 contra marzo 2024 | La consigna gira alrededor de `cbd_congestion_fee`, que existe en 2025 y no en 2024. Evitamos enero porque el cargo empezó el 5/1/2025 y el mes queda partido |
| Stack: dlt (ingesta), PostgreSQL (base), dbt (calidad, transformación y modelo), Polars (Parquet), Dagster (orquestación), Prometheus, Grafana, Loki y Alloy (observabilidad), todo en Docker | Es el stack visto en clase. En la consulta del 17/11 el profe pidió usar un ingestador, hacer el análisis en dbt, observar la base y los procesos, y usar Docker con su red |
| Ingestador: dlt y no Airbyte | El profe propuso dlt y dijo que Airbyte es pesado. Airbyte pide 8 GB solo para él, se instala aparte con `abctl` (su propio Kubernetes) y su configuración queda en su base interna, fuera del repo. dlt es una librería de Python que entra en el mismo contenedor |
| dbt Core 1.x | Es la línea que se vio en clase con dbt-postgres y la que soporta la integración de Dagster |
| Polars para escribir el Parquet | La consigna nombra "DuckDB, Polars o pandas". `scan_csv` + `sink_parquet` escribe en streaming, sin cargar el mes entero en memoria |

## Estructura del repositorio

| Decisión | Por qué |
| --- | --- |
| `src/` con un módulo por etapa (`ingesta`, `esquema`, `calidad`, `transformacion`, `modelo`) y `sql/` con una consulta por archivo (`staging`, `calidad`, `curado`, `modelo`, `preguntas`) | Es la estructura que fija la consigna. dbt se configura desde la raíz (`dbt_project.yml`) para que sus modelos vivan en `sql/` |
| `calidad.py`, `transformacion.py` y `modelo.py` corren con dbt solo los modelos de su etapa (`src/correr_dbt.py`) y muestran su resultado; Dagster corre todo junto | Cada etapa se puede correr y mostrar por separado (`make calidad`, etc.) sin duplicar SQL |
| dbt corre con `--indirect-selection cautious` al seleccionar una etapa | Corre solo los tests cuyas tablas están todas en la selección. Sin esto, al correr calidad intentaba un test que compara con curado |
| El contrato de esquema y el catálogo de reglas viven juntos en `contracts/`; los tests de datos de dbt en `tests/dbt/` | Los contratos del pipeline quedan en un solo lugar, separados del código |
| Makefile como atajo de Docker: `make all MES=...` (comando único), `make reporte`, `make respuestas`, `make test`, `make reprocesar`, `make explorar` y un objetivo por etapa | Respeta el comando de la consigna. En Windows sin make se usa el comando de Docker equivalente, que figura en el README |
| Las consultas de exploración son SQL sobre las tablas `raw` (`exploracion/*.sql`) y no forman parte del pipeline | Sirven para medir antes de decidir umbrales y se pueden volver a correr con `make explorar` o desde DBeaver |

## Plataforma (Docker)

| Decisión | Por qué |
| --- | --- |
| Todo corre en contenedores de una red propia (`pipeline_net`); la máquina solo necesita Docker | Mac, Ubuntu y Windows corren lo mismo, sin depender de la versión de Python. Los servicios se hablan por nombre (`postgres:5432`) |
| Un solo Dockerfile para todo el código nuestro; el servicio `herramientas` es solo para comandos sueltos | Lo que anda en `herramientas` anda igual cuando lo corre Dagster, porque es la misma imagen |
| Imágenes de Docker y librerías de Python con versión fija | `latest` puede cambiar entre hoy y la defensa; así la cátedra baja exactamente lo mismo |
| Postgres con techo de 1,5 GB (`mem_limit`), `shared_buffers=384MB` y `work_mem=32MB`; los contenedores de Python, 2 GB | La máquina de referencia tiene 8 GB que comparte con el resto del stack |
| Postgres manda al log las consultas de más de 1 s, las conexiones y los checkpoints | Es lo que se mira en los logs para entender qué pasa en la base durante la carga y la transformación |
| Polars limitado a 2 hilos (`POLARS_MAX_THREADS=2`) | En la Mac (8 núcleos) Polars abría un hilo por núcleo: la exportación llegaba a 1,2 GB de pico y 258 s de CPU, y competía con Postgres. Con 2 hilos bajó a 711 a 721 MB y 52 a 143 s de CPU por mes |
| Tablero "Preguntas de negocio" en Grafana, con Postgres como origen de datos; los meses salen de las propias tablas de preguntas | Muestra las respuestas comparando los dos meses en gráficos, sin un paso extra en el pipeline: lee lo que dbt ya dejó en el esquema `preguntas` |
| Grafana en el puerto 3001 | El 3000 queda para la web de Dagster |

## Parte 1: ingesta

| Decisión | Por qué |
| --- | --- |
| Idempotencia: no se descarga si el archivo existe y su SHA-256 coincide con el de la última ingesta `ok` del log | Mirar solo si el archivo existe no alcanza: puede existir y estar corrupto. Probado en `test_ingesta.py`: con el archivo corrupto lo vuelve a bajar |
| Cuando la ingesta saltea un archivo no agrega fila al log | El log registra ingestas. Así una segunda corrida no cambia ningún conteo, que es lo que hay que mostrar en la demo |
| Descarga en bloques de 1 MB a un archivo `.tmp` que se renombra al terminar | Nunca hay más de 1 MB en memoria, y un corte a mitad de descarga no deja un archivo incompleto con el nombre definitivo |
| 3 reintentos con esperas de 2, 4 y 8 segundos; si falla, fila `error` en el log y código de salida distinto de 0 | Lo pide la consigna. La espera creciente evita insistir sobre un servidor saturado, y el código de salida corta el pipeline |
| La tabla de zonas usa la misma función `ingestar` que los meses | "Una sola vez" es un caso de la misma idempotencia; no hace falta código aparte |
| dlt carga a `raw.yellow_trips` con `merge` + `delete-insert` y clave `mes_archivo` | Antes de insertar un mes, dlt borra las filas que ya tenía de ese mes: recargarlo no duplica y no toca los demás |
| `ingestion_log` vive en Postgres (`raw.ingestion_log`); `ok` se anota recién después de cargar | Así `ok` significa "descargado y cargado". Si la carga falla, la próxima corrida lo vuelve a intentar |
| `LOAD__TRUNCATE_STAGING_DATASET=true` | El merge de dlt pasa por `raw_staging`; sin vaciarlo quedan dos copias de cada mes en disco |
| Las fechas de subida y bajada se cargan sin zona horaria (`timezone: False`), con la aclaración generada por una función (`sin_zona_horaria()`) | Son hora local de Nueva York; sin la aclaración dlt las guarda como UTC y las consultas por hora quedan corridas 3 horas. Es una función porque dlt escribe el nombre de la columna dentro de la aclaración: compartida entre las dos fechas, la segunda quedaba pisada |
| Opción `--forzar` en la ingesta | Vuelve a validar y cargar un mes ya ingestado sin bajarlo de nuevo. Sirve para reprocesar después de cambiar el contrato |

## Parte 2: esquema

| Decisión | Por qué |
| --- | --- |
| El contrato (`contracts/yellow_schema.yaml`) describe nombres en snake_case y tipos de Arrow (`int32`, `double`, `timestamp[us]`, `large_string`) | Es como se lee el Parquet antes de cargarlo, así se compara el archivo tal como viene. Tiene número de versión y su historial queda en Git |
| El chequeo de esquema es código nuestro (`src/esquema.py`) y no el contrato automático de dlt | Probamos `schema_contract` de dlt con `data_type: freeze` y frenaba cargas válidas (marzo 2025 contra una tabla creada con marzo 2024). El chequeo propio hace exactamente lo que pide la consigna |
| snake_case con la convención de nombres de dlt (`NamingConvention`) | Es la misma regla con la que dlt nombra las columnas: el contrato y la tabla nunca pueden quedar con nombres distintos. Normaliza también una columna que aparezca mañana |
| `cbd_congestion_fee` está marcada `opcional: true` | Distingue "falta una columna prevista" (2024, se sigue) de "el archivo está roto" (falta una obligatoria, se frena) |
| `cbd_congestion_fee` vale nulo en 2024, no 0, y se agrega como columna nula de tipo `double` | El cargo no existía: 0 significaría "se cobró cero", y los promedios ignoran los nulos mientras que un 0 los bajaría. Con el tipo declarado, la tabla tiene la columna aunque el primer mes cargado sea 2024 |
| Columna nueva que no está en el contrato: se reporta, no se carga y el pipeline sigue | Lo conocido sigue siendo válido. Incorporarla es una decisión humana: editar el contrato y subir la versión |
| Columna obligatoria faltante o tipo distinto: el archivo no se carga, el log registra `error` y el pipeline termina con error | Convertir tipos en silencio puede perder datos |
| El resultado de cada chequeo se guarda en `raw.reporte_esquema` | Queda la historia de qué se encontró en cada archivo y con qué versión del contrato |
| Los dos meses se unen en `raw.yellow_trips`, con `archivo_origen` y `mes_archivo` | La cuarentena pide el archivo de origen, y la regla de "subida fuera del mes" necesita el mes del archivo |

## Parte 3: calidad

| Decisión | Por qué |
| --- | --- |
| La calidad se hace en dbt: `stg_yellow_trips` (vista) → `trips_evaluados` → `trips_validos` / `cuarentena` → `reporte_calidad` y `reporte_calidad_reglas` | Cada paso es un archivo SQL y dbt los ejecuta en el orden que surge de los `ref()` |
| Severidad, umbral y justificación de cada regla en `contracts/reglas_calidad.csv` (un seed de dbt); las condiciones SQL en `trips_evaluados.sql` | dbt lee el seed antes de armar el SQL: cambiar una severidad es editar una celda, sin tocar código. Si una regla está en un lado y no en el otro, dbt frena con un error |
| Criterio de severidad: rechazo si la fila describe algo imposible o no se puede asignar a un mes o zona; advertencia si un dato es dudoso o falta pero el viaje existió y se cobró | Un criterio único evita decidir regla por regla "a ojo" y se explica en una frase |
| R03 distancia <= 0 es advertencia | El 95 % de esos viajes tiene cobro positivo, con total mediano de unos 20 dólares. Falta la distancia, no el viaje |
| R04 máximo de distancia: 100 millas, rechazo | El 99,99 % mide menos de 58 millas. Sobre 100 quedan 122 y 214 filas, casi todas de más de 1.000 millas |
| La regla de distancia de la consigna se parte en dos (R03 y R04) | Sin distancia registrada y distancia absurda tienen causas y severidades distintas |
| R06 pasajeros nulo o 0 es advertencia | Afecta al 13 % y al 22,7 %; los nulos son todo el tipo de pago 0. Rechazar distorsionaría la comparación entre años, y el dato no se usa en ningún cálculo |
| R07 con `LEFT JOIN` a zonas | Con `NOT IN`, una zona nula pasaba sin zona. Con el `LEFT JOIN` un id nulo también viola la regla (probado en `test_calidad.py`) |
| R08 duplicados con `row_number()` particionando por las 20 columnas del contrato y el archivo de origen; se conserva una copia | Rechazar todas las copias borraría el viaje; conservar una lo cuenta una sola vez |
| Regla propia R09: tarifa base <= 0, advertencia | En 2025-03 hay 140.469 viajes de tipo de pago 0 con tarifa negativa y total positivo. El viaje se cobró, pero la tarifa no sirve: la propina porcentual queda nula y la tarifa media se calcula sin ellos |
| Regla propia R10: velocidad promedio > 80 mph, rechazo | El 99,9 % promedia menos de 49 mph y el límite máximo del estado es 65. Más de 80 significa distancia u horarios mal cargados |
| Regla propia R11: zona 264 o 265, advertencia | Existen en la tabla (pasan R07) pero no son un lugar real. El flag permite sacarlas de los rankings por zona |
| Umbrales de R04 (100 millas) y R10 (80 mph) como variables de dbt en `dbt_project.yml` | Se cambian en un solo lugar y quedan a la vista |
| Severidades, umbrales y reglas propias los propuso Claude a pedido nuestro, a partir de las mediciones de `exploracion/` | Queda declarado; las revisamos para poder defenderlas |
| Las reglas violadas se guardan como texto separado por comas (`R04,R10`) en `reglas_violadas` (rechazos) y `flags` (advertencias) | Se lee a simple vista en una consulta. Si `reglas_violadas` no está vacío, la fila va a cuarentena |
| Una condición que da nulo cuenta como "no viola la regla" (salvo R07) | `CASE WHEN` solo marca cuando la condición es verdadera. Si falta el dato no podemos afirmar que la fila esté mal |
| La cuarentena guarda la fila con los nombres de columna normalizados | Los valores son los originales; solo cambia el nombre de la columna, igual que en `raw.yellow_trips` |
| La reconciliación es un test de dbt (`tests/dbt/reconciliacion.sql`) que cuenta leídas, aceptadas y cuarentena en tres tablas distintas | Contarlas por separado es lo que hace que el control sirva. Si no cierra, `dbt build` falla y el pipeline también. Resultado: 3.582.628 = 3.535.924 + 46.704 y 4.145.257 = 4.053.200 + 92.057 |
| Esquemas `raw`, `staging`, `calidad`, `curado`, `modelo` y `preguntas`, con la macro `generate_schema_name` | Sin la macro, dbt les antepone el esquema por defecto (`analitica_calidad`) |

## Parte 4: transformación

| Decisión | Por qué |
| --- | --- |
| Columnas derivadas y zonas en dbt (`curado.trips_curados`), a partir de `trips_validos` | Es la capa de análisis: duración, velocidad, fecha, hora, día ISO, propina % y barrio y zona de origen y destino |
| `velocidad_mph` nula si la distancia es <= 0 (R03); `propina_pct` nula si la tarifa es <= 0 (R09) | Un 0 mph sería un dato falso, y dividir por una tarifa nula o negativa da error o un porcentaje sin sentido. La duración no necesita protección porque R02 ya rechaza duraciones <= 0 |
| `dia_semana` ISO: 1 es lunes y 7 es domingo | Es el estándar ISO 8601; evita la ambigüedad de si la semana empieza en domingo o en lunes |
| Test `curado_no_pierde_filas`: por mes, `trips_curados` tiene las mismas filas que `trips_validos` | Control de que el cruce con zonas no perdió ni duplicó viajes |
| Parquet con un archivo por mes en `data/curated/yellow/year=AAAA/month=MM/trips.parquet` | Parquet lo lee cualquier herramienta sin depender de la base. Con un archivo por partición, reprocesar un mes es reemplazar un archivo |
| Exportación: `COPY` de Postgres a un CSV temporal en `/tmp` del contenedor y Polars lo convierte con `scan_csv` + `sink_parquet` | `COPY` es la forma más rápida de sacar datos de Postgres. El CSV va al disco del contenedor y no a `data/`, que en Mac es una carpeta compartida y lenta |
| La partición se escribe a un `.tmp` y se renombra; después se cuentan sus filas y se comparan con Postgres | Si se corta, la partición anterior queda intacta; si faltan filas, el paso termina con error |
| La exportación falla con un mensaje claro si una columna tiene un tipo que no espera | Un tipo inesperado indica que algo cambió aguas arriba; mejor frenar que escribir un Parquet con tipos distintos |
| `make reprocesar MES=...` vuelve a escribir solo la partición de ese mes y muestra las particiones antes y después | Es la evidencia que pide la consigna (4.4) |

## Parte 5: modelo y preguntas

| Decisión | Por qué |
| --- | --- |
| Modelo estrella en el esquema `modelo`: `dim_zone`, `dim_date`, `fact_trips` y `agg_zone_hour`, construidos desde `curado.trips_curados` | Se reconstruye entero en cada corrida, así nunca queda desfasado de la capa curada |
| `fact_trips` guarda claves y medidas, sin nombres de zona ni atributos de fecha | Esa información vive una sola vez en `dim_zone` y `dim_date`; es la separación que define un modelo estrella |
| `dim_date` incluye `anio_mes` (texto `AAAA-MM`) | Todas las preguntas filtran por mes con esa columna |
| Tests del modelo: claves únicas en las dimensiones, `relationships` de `fact_trips` contra `dim_date` y `dim_zone`, y `agg_cuadra_con_fact` | Prueban que el modelo estrella es consistente, no solo que las tablas existen |
| Las 6 preguntas son modelos de dbt (esquema `preguntas`, una tabla y un archivo por pregunta) | Cada respuesta queda guardada y se consulta desde DBeaver |
| Las preguntas (a) y (b) usan `agg_zone_hour`; las demás, `fact_trips` | La agregada responde por zona y hora con unas 211.000 filas en vez de 7,6 millones |
| Ingreso promedio por hora = ingreso total / viajes, no promedio de promedios | Promediar promedios de zonas con distinta cantidad de viajes da un número incorrecto |
| Tarifa media sin viajes con tarifa <= 0 (R09); rankings por zona sin las zonas 264 y 265 (R11) | Su tarifa base no es válida y bajaría el promedio; esas zonas no son un lugar real |
| Pregunta (b) con `DISTINCT ON` | Se queda con la hora de mayor ingreso de cada mes; Postgres no tiene `QUALIFY` |
| Pregunta (c): solo zonas con al menos 1.000 viajes en el mes | Sin mínimo, el ranking lo encabezan zonas con 1 o 2 viajes al 100 % |
| El mes asignado sale de la variable `MES` (macro `mes_asignado()`); el de comparación se calcula restando un año (`mes_anterior()`) | Un solo parámetro para todo el pipeline, como pide la consigna |

## Orquestación (Dagster)

| Decisión | Por qué |
| --- | --- |
| La ingesta es un asset, cada modelo y seed de dbt es un asset (vía `dagster-dbt`) y la exportación a Parquet es otro (`src/definitions.py`) | Dagster dibuja el grafo completo raw → staging → calidad → curado → modelo → preguntas, ejecuta en orden y guarda cada corrida con su duración y sus logs. Los tests de dbt aparecen como *asset checks* |
| Los assets de dbt se agrupan por carpeta con un traductor propio (`TraductorDbt`) | Por defecto quedaban todos en un grupo `default`; así el grafo muestra las etapas en el orden de la consigna |
| Los tests `curado_no_pierde_filas` y `agg_cuadra_con_fact` declaran a qué tabla pertenecen (`meta.dagster.ref`) | Comparan dos tablas y Dagster no sabía a cuál asignarlos |
| Un job, `pipeline_completo`, con el mes como configuración (por defecto, la variable `MES`); procesa el mes y el mismo mes del año anterior | Un solo parámetro |
| Comando único: `docker compose run --rm pipeline` (lo que corre `make all`). Levanta lo que necesita, corre el job y termina con el código de salida del pipeline | Funciona igual en Mac, Ubuntu y Windows |
| Sensor `nuevo_mes_publicado` (cada 6 horas): si la TLC publicó el mes siguiente al último procesado, lanza el job. Arranca apagado | La fuente publica un archivo por mes: la plataforma queda prendida y procesa sola lo nuevo. Apagado para que levantar el stack no dispare descargas pesadas sin querer |
| `dagster-webserver` y `dagster-daemon` quedan prendidos y guardan su historial en una base `dagster` aparte dentro del mismo Postgres | La web, el daemon y las corridas lanzadas desde la terminal ven el mismo historial, sin mezclarlo con los datos |
| Servicio `preparar` (`src/preparar.py`): corre una vez antes que Dagster, crea la base `dagster` si falta y genera el manifest de dbt | Dagster necesita el manifest para armar los assets de dbt |

## Observabilidad

| Decisión | Por qué |
| --- | --- |
| Métricas de cada etapa con psutil (`src/metricas.py`): duración, pico de RAM (proceso + subprocesos, medido cada 0,5 s), CPU, filas y si terminó bien | Es la observabilidad de los procesos que pidió el profe |
| Las métricas van al Pushgateway con etiquetas `etapa` y `mes`; Prometheus las lee cada 5 s | Una etapa corta puede terminar antes de que Prometheus pase a buscar; el Pushgateway guarda sus números |
| Se publica también cuando la etapa falla (`pipeline_etapa_exito` = 0), y si el Pushgateway no responde el pipeline sigue | Una falla tiene que verse en Grafana, y las métricas no pueden romper el procesamiento |
| dbt informa además la duración de cada modelo y test (`run_results.json`) | Muestra dónde está el costo: `trips_curados` y `trips_evaluados` son los modelos más pesados |
| postgres-exporter para la base y dos tableros: "Postgres - base taxi" y "Pipeline - procesos" | En uno se ve cómo reaccionó la base; en el otro, qué hizo cada etapa |
| Tablero de procesos: filas como número entero, barras de un solo color y RAM con umbrales (verde < 1,5 GB, naranja < 3 GB, rojo) | Grafana en español abreviaba millones como "Mil", y el degradé ponía en rojo valores grandes que no eran un problema |
| Logs con Loki y Alloy: Alloy lee los logs de los contenedores del proyecto por el socket de Docker, les pone la etiqueta `servicio` y los manda a Loki | Poder ver los logs de la base y de los procesos en Grafana. Alloy es el reemplazo actual de Promtail |
| Paneles de logs al pie de los dos tableros; el de Postgres sin las líneas de conexión | Métricas y logs en la misma pantalla. Dagster se conecta cada pocos segundos y esas líneas tapaban las consultas lentas y los checkpoints |
| Loki guarda 7 días de logs, con techo de 512 MB de RAM; Alloy, 256 MB | Suficiente para la defensa sin comprometer los 8 GB |

## Tests

| Decisión | Por qué |
| --- | --- |
| Tests de pytest contra una base aparte, `taxi_test`, que se crea y se borra en cada corrida de `make test` | Prueban el stack real (dlt, dbt y Postgres) sin tocar los datos |
| Test de calidad con 8 viajes sintéticos | Se sabe de antemano qué tiene que pasar con cada fila: cubre reglas de rechazo, una advertencia, zona nula y duplicados |
| El test de ingesta reemplaza la descarga por una falsa | No depende de internet y permite contar cuántas veces se intentó descargar (idempotencia y reintentos) |
| El test de reconciliación borra una fila aceptada y verifica que el control falla | Con datos reales la reconciliación siempre cierra; hay que probar también el caso en que no |
