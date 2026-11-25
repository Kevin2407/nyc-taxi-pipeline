# Pipeline NYC Taxi

Pipeline batch que ingiere, valida, limpia y modela los viajes de taxi amarillo de Nueva York de un mes y del mismo mes del año anterior (acá, **marzo 2025 contra marzo 2024**), y responde 6 preguntas de negocio sobre su propio modelo. Usa el stack visto en la materia: **dlt** para la ingesta, **PostgreSQL** como base, **dbt** para calidad, transformación y modelo, **Dagster** para orquestar, y **Prometheus, Grafana y Loki** para observar la base y los procesos, todo en **Docker**.

## Cómo instalar y ejecutar

Lo único que hace falta en la máquina es **Docker** (Docker Desktop en Mac y Windows, Docker Engine en Linux) y conexión a internet. Python, dbt, Dagster y el resto corren dentro de los contenedores. Los datos no están en el repositorio: el pipeline los descarga.

```bash
git clone https://github.com/Kevin2407/nyc-taxi-pipeline.git
cd nyc-taxi-pipeline
make all MES=2025-03
```

En Windows sin `make`, el equivalente exacto es:

```bash
docker compose run --rm -e MES=2025-03 pipeline
```

Ese comando construye la imagen (la primera vez), levanta Postgres, Dagster y la observabilidad, y corre el job `pipeline_completo` para el mes pedido y el mismo mes del año anterior: ingesta, contrato de esquema, calidad, transformación, Parquet, modelo y preguntas. Termina con código 0 si todo salió bien y distinto de 0 si algo falló.

| Comando | Qué hace |
| --- | --- |
| `make all MES=2025-03` | Comando único: el pipeline completo |
| `make reporte` | Reporte de calidad por mes y por regla, y filas en cuarentena con su regla violada |
| `make respuestas` | Las 6 respuestas de negocio |
| `make test` | Tests automáticos (pytest, contra una base de prueba aparte) |
| `make levantar` / `make apagar` | Deja prendida o apaga la plataforma |
| `make ingesta`, `esquema`, `calidad`, `transformacion`, `modelo` | Cada etapa por separado, sin Dagster |
| `make reprocesar MES=2025-03` | Vuelve a escribir solo la partición Parquet de ese mes |
| `make explorar` | Consultas de exploración sobre los datos cargados (`exploracion/*.sql`) |
| `make limpiar` | Borra la base, los volúmenes y `data/` para correr desde cero |

Mientras la plataforma está prendida:

| Servicio | Dirección |
| --- | --- |
| Dagster (grafo, corridas, logs, sensor) | http://localhost:3000 |
| Grafana (tableros "Postgres - base taxi", "Pipeline - procesos" y "Preguntas de negocio - comparación de meses"; usuario y contraseña `admin`) | http://localhost:3001 |
| Prometheus · Pushgateway · Alloy | http://localhost:9090 · http://localhost:9091 · http://localhost:12345 |
| PostgreSQL (por ejemplo, desde DBeaver; base, usuario y contraseña `taxi`) | `localhost:5432` |

### Demostración

1. **Correr el pipeline completo:** `make all MES=2025-03`, con Dagster abierto en *Runs*.
2. **Volver a correrlo y mostrar que los conteos no cambian:** otra vez `make all MES=2025-03`. La ingesta dice "Sin cambios" (el hash coincide con el del log) y los conteos de `make reporte` son los mismos.
3. **Reporte de calidad y una fila en cuarentena con su regla violada:** `make reporte`. Por ejemplo, el viaje de 320.136 millas en 7 minutos de marzo 2025 viola R04 (distancia excesiva) y R10 (velocidad imposible).

## Estructura del repositorio

```
README.md · RESULTADOS.md · DECISIONES.md
requirements.txt          librerías de Python con versión fija (van dentro de la imagen)
Makefile                  atajos: make all MES=..., make reporte, make test...
Dockerfile · docker-compose.yml · .env.example
contracts/
  yellow_schema.yaml      contrato de esquema (Parte 2)
  reglas_calidad.csv      catálogo de reglas: id, severidad, umbral y justificación (Parte 3)
src/
  ingesta.py              Parte 1: descarga con hash, reintentos y log; carga a Postgres con dlt
  esquema.py              Parte 2: compara el archivo contra el contrato antes de cargar
  calidad.py              Parte 3: reglas, cuarentena, reporte y reconciliación (corre sql/calidad)
  transformacion.py       Parte 4: capa curada (sql/curado) y Parquet particionado con Polars
  modelo.py               Parte 5: modelo estrella y preguntas (sql/modelo y sql/preguntas)
  definitions.py          orquestación con Dagster: job pipeline_completo y sensor
  metricas.py             métricas de cada etapa para Prometheus y Grafana
  base.py · correr_dbt.py · meses.py · preparar.py   utilidades
sql/                      una consulta por archivo (modelos de dbt)
  staging/  calidad/  curado/  modelo/  preguntas/
tests/                    tests de pytest; tests/dbt/ tiene los tests de datos de dbt
macros/                   funciones de Jinja que usan los modelos de dbt
dbt_project.yml · profiles.yml   configuración de dbt
dagster/                  configuración de Dagster
observabilidad/           Prometheus, Grafana (datasources y tableros), Loki y Alloy
exploracion/              consultas SQL sobre los datos crudos y HALLAZGOS.md, que justifican umbrales y severidades
```

`data/` no se sube (está en `.gitignore`): ahí el pipeline deja los archivos crudos (`data/raw/`) y la capa curada (`data/curated/`).

## Arquitectura

```
TLC (Parquet mensual) ──► 1. INGESTA (dlt) ──────────► raw.yellow_trips, raw.zonas, raw.ingestion_log
                             descarga a data/raw/yellow/year=AAAA/month=MM/ sin modificar,
                             hash SHA-256, 3 reintentos, log de control
                          2. ESQUEMA  (antes de cargar: contrato, snake_case, cbd nulo en 2024) ► raw.reporte_esquema
                                   │
                                   ▼  dbt (SQL en sql/, ejecutado dentro de Postgres)
                          staging.stg_yellow_trips  (los dos meses unificados)
                          3. CALIDAD ──► calidad.trips_validos (con flags)
                                      ├─► calidad.cuarentena (fila original + archivo + reglas)
                                      └─► calidad.reporte_calidad / reporte_calidad_reglas
                                          test de reconciliación: leídas = aceptadas + cuarentena
                          4. TRANSFORMACIÓN ──► curado.trips_curados (columnas derivadas y zonas)
                                             └─► data/curated/yellow/year=AAAA/month=MM/trips.parquet (Polars)
                          5. MODELO ──► modelo.dim_zone, dim_date, fact_trips, agg_zone_hour
                                     └─► preguntas.pregunta_a ... pregunta_f

Dagster ordena y ejecuta las etapas (job pipeline_completo) y guarda cada corrida.
Cada etapa mide con psutil su duración, RAM, CPU y filas ──► Pushgateway ──► Prometheus ──► Grafana
postgres-exporter mide la base ──► Prometheus ──► Grafana
Alloy junta los logs de todos los contenedores ──► Loki ──► Grafana
```

Todos los servicios corren en contenedores dentro de una red de Docker propia (`pipeline_net`) y se hablan por nombre: por ejemplo, dlt y dbt se conectan a `postgres:5432` y Prometheus lee `postgres-exporter:9187` y `pushgateway:9091`.

| Servicio | Qué es | Qué hace |
| --- | --- | --- |
| `postgres` | PostgreSQL 17 | La base: esquemas `raw`, `staging`, `calidad`, `curado`, `modelo` y `preguntas`. Techo de 1,5 GB de RAM |
| `pipeline` | Imagen propia (Python 3.12) | El comando único: corre el job de Dagster y termina |
| `dagster-webserver`, `dagster-daemon` | Dagster | La web (grafo de assets, corridas, logs) y el daemon que evalúa el sensor `nuevo_mes_publicado` |
| `preparar` | Imagen propia | Corre una vez al arrancar: crea la base `dagster` y el manifest de dbt |
| `herramientas` | Imagen propia | Para comandos sueltos: etapas de a una, tests, dbt |
| `postgres-exporter`, `pushgateway`, `prometheus`, `grafana` | Observabilidad de métricas | Base y procesos en dos tableros |
| `loki`, `alloy` | Observabilidad de logs | Logs de todos los contenedores, en Grafana |

**Herramientas elegidas.** dlt es el ingestador: el profe propuso dlt o Meltano, y Airbyte quedó descartado porque pide 8 GB de RAM solo para él, se instala aparte con su propio Kubernetes y guarda su configuración fuera del repositorio. dbt hace todo el SQL (calidad, curado, modelo y preguntas) dentro de Postgres. Polars escribe el Parquet en modo streaming para no cargar un mes entero en memoria. Dagster orquesta; un Makefile solo no muestra el grafo, no guarda el historial de corridas ni detecta meses nuevos.

**¿Corre continuamente?** La plataforma sí: Postgres, Dagster y la observabilidad quedan prendidos (`make levantar`). El procesamiento es batch porque el dato lo es: la TLC publica un archivo por mes, con unos dos meses de demora. El sensor `nuevo_mes_publicado` de Dagster se fija cada 6 horas si apareció el mes siguiente al último procesado y, si apareció, lanza el job solo. Arranca apagado, para que levantar el stack no dispare descargas; se prende desde la web de Dagster (*Automation*).

## Decisiones

El detalle fechado de cada decisión, con su porqué, está en `DECISIONES.md`. Acá van las que pide la consigna.

### Parte 1: ingesta

- `python -m src.ingesta --mes 2025-03` descarga a `data/raw/yellow/year=2025/month=03/yellow_tripdata_2025-03.parquet` sin modificarlo, en bloques de 1 MB a un `.tmp` que se renombra al terminar. La tabla de zonas se descarga una sola vez (misma regla de idempotencia).
- **Idempotencia:** si el archivo existe y su SHA-256 coincide con el de la última ingesta `ok` del log, no se descarga ni se carga nada. La carga a Postgres usa `merge` con estrategia `delete-insert` por `mes_archivo`: recargar un mes reemplaza solo ese mes.
- **`raw.ingestion_log`:** archivo, URL, filas, bytes, hash, fecha y hora, estado (`ok` o `error`) y detalle. `ok` se anota recién después de cargar.
- **Fallas de red:** hasta 3 reintentos con esperas de 2, 4 y 8 segundos; si sigue fallando, fila `error` en el log y código de salida distinto de 0.

### Parte 2: esquema

- **Contrato:** `contracts/yellow_schema.yaml` (versión 2): nombre en snake_case y tipo de Arrow de cada una de las 20 columnas; `cbd_congestion_fee` es opcional. Su historial está en Git.
- **Antes de cargar**, `src/esquema.py` compara el esquema real del Parquet contra el contrato y reporta columnas faltantes (obligatorias y opcionales), nuevas y con tipo distinto. El resultado de cada archivo queda en `raw.reporte_esquema`.
- **snake_case:** con la misma regla que usa dlt (`PULocationID` → `pu_location_id`).
- **Los dos meses se unifican** en `raw.yellow_trips`, con `archivo_origen` y `mes_archivo` en cada fila.
- **Valor de `cbd_congestion_fee` en 2024: nulo, no 0.** El cargo no existía: un 0 afirmaría que se cobró cero. Además los promedios ignoran los nulos y un 0 los bajaría. Resultado: las 3.582.628 filas de marzo 2024 tienen nulo y las 4.145.257 de marzo 2025 tienen valor.
- **Si mañana aparece una columna que no está en el contrato:** se reporta como "nueva", no se carga y el pipeline sigue (lo conocido sigue siendo válido). Para incorporarla se agrega al contrato y se sube la versión.
- **Si falta una columna obligatoria o cambia un tipo:** el archivo no se carga, el log registra `error` y el pipeline termina con error.

### Parte 3: calidad

Las reglas están en `contracts/reglas_calidad.csv` (id, descripción, severidad, umbral y justificación) y sus condiciones SQL en `sql/calidad/trips_evaluados.sql`. Cambiar una severidad es editar una celda del CSV; dbt lo lee antes de armar el SQL. Las mediciones que respaldan los umbrales están en `exploracion/HALLAZGOS.md`.

Criterio de severidad: **rechazo** cuando la fila describe algo imposible o no se puede asignar a un mes o a una zona; **advertencia** cuando un dato es dudoso o falta, pero el viaje existió y se cobró.

| Id | Regla | Severidad | Umbral | Por qué |
| --- | --- | --- | --- | --- |
| R01 | Subida fuera del mes del archivo | rechazo | Mes calendario del archivo | Quedaría en la partición equivocada |
| R02 | Bajada anterior o igual a la subida | rechazo | Duración > 0 | Duración imposible; no se puede calcular velocidad |
| R03 | Distancia menor o igual a 0 | advertencia | Distancia > 0 | El 95 % se cobró normalmente: falta el dato, no el viaje |
| R04 | Distancia excesiva | rechazo | 100 millas | El 99,99 % mide menos de 58; lo que pasa de 100 es error de carga |
| R05 | Importe total negativo | rechazo | Total >= 0 | Ajustes de disputas y viajes sin cargo, no precios |
| R06 | Pasajeros nulo o 0 | advertencia | Al menos 1 | Afecta al 13 % y al 22,7 %; no interviene en ningún cálculo |
| R07 | Zona de origen o destino inexistente (o nula) | rechazo | Existir en la tabla de zonas | No se puede enriquecer ni modelar |
| R08 | Duplicado exacto | rechazo | Las 20 columnas iguales en el mismo archivo | Contaría dos veces el mismo viaje; se conserva una copia |
| R09 | Tarifa base menor o igual a 0 (propia) | advertencia | Tarifa > 0 | Viajes cobrados con tarifa inservible; se excluyen de los cálculos sobre tarifa |
| R10 | Velocidad promedio imposible (propia) | rechazo | 80 mph | El 99,9 % promedia menos de 49 mph |
| R11 | Zona 264 o 265 (propia) | advertencia | Zonas 1 a 263 | Existen en la tabla pero no son un lugar real |

Los umbrales de R04 y R10 son variables de dbt (`dbt_project.yml`).

**Cuarentena y flags:** las filas que violan una regla de rechazo van a `calidad.cuarentena`, con la fila original, el archivo de origen y la lista de reglas violadas (por ejemplo, `R04,R10`). Las advertencias no descartan la fila: quedan en `calidad.trips_validos` con la columna `flags`.

**Tratamiento de nulos**

- `cbd_congestion_fee` es nulo en 2024 (ver Parte 2).
- `passenger_count` nulo no se completa ni se rechaza: se marca con R06.
- Una condición que da nulo porque le falta un dato cuenta como "no viola la regla", salvo R07: una zona nula no se puede asignar y se rechaza.
- La velocidad queda nula cuando la distancia es <= 0 (R03), y la propina como porcentaje de la tarifa queda nula cuando la tarifa es <= 0 (R09).

**Reporte y reconciliación** (`make reporte`):

| | Marzo 2024 | Marzo 2025 |
| --- | --- | --- |
| Filas leídas | 3.582.628 | 4.145.257 |
| Aceptadas | 3.535.924 | 4.053.200 |
| En cuarentena | 46.704 (1,30 %) | 92.057 (2,22 %) |

La reconciliación es un test de dbt (`tests/dbt/reconciliacion.sql`): devuelve los meses donde leídas ≠ aceptadas + cuarentena. Si devuelve alguno, `dbt build` falla, el paso de Dagster falla y el pipeline termina con error. Cada número se cuenta en una tabla distinta (staging, válidos y cuarentena) para que el control sirva.

### Parte 4: transformación

Columnas derivadas de `curado.trips_curados` (`sql/curado/trips_curados.sql`):

| Columna | Cálculo | Cuándo queda nula |
| --- | --- | --- |
| `duracion_min` | segundos entre subida y bajada / 60 | nunca (R02 rechaza duraciones <= 0) |
| `velocidad_mph` | distancia / duración en horas | distancia <= 0 (R03) |
| `fecha_subida`, `hora_subida`, `dia_semana` | fecha, hora 0 a 23 y día ISO (1 lunes, 7 domingo) | nunca |
| `propina_pct` | propina / tarifa x 100 | tarifa <= 0 (R09) |
| `pu_borough`, `pu_zone`, `do_borough`, `do_zone` | cruce con la tabla de zonas | nunca (R07 garantiza que la zona existe) |

La capa curada se escribe además en Parquet particionado estilo Hive, `data/curated/yellow/year=AAAA/month=MM/trips.parquet` (`src/transformacion.py`): Postgres saca el mes con `COPY` y Polars escribe el Parquet en streaming. Se escribe a un `.tmp` y se renombra; después se cuentan sus filas y se comparan con Postgres.

**Reprocesar un mes reemplaza solo su partición.** `make reprocesar MES=2025-03` vuelve a escribir solo la partición de marzo 2025 y muestra las particiones antes y después. Prueba del 23/11/2026 en la Mac (horas UTC del contenedor):

| Partición | Filas antes | Archivo antes | Filas después | Archivo después |
| --- | --- | --- | --- | --- |
| `year=2024/month=03` | 3.535.924 | 106.453.144 bytes, 01:27:10 | 3.535.924 | 106.453.144 bytes, 01:27:10 (sin tocar) |
| `year=2025/month=03` | 4.053.200 | 124.426.701 bytes, 01:26:09 | 4.053.200 | 123.925.467 bytes, 02:11:17 (reescrito) |

El tamaño del archivo reescrito cambia un poco porque Postgres no devuelve las filas siempre en el mismo orden y la compresión de Parquet depende del orden; las filas son las mismas.

### Parte 5: modelo

Modelo estrella en el esquema `modelo` (`sql/modelo/`), construido desde la capa curada:

```
              dim_date
                 │ fecha
                 │
           fact_trips ── pu_zone_id / do_zone_id ── dim_zone
                 │
                 └──► agg_zone_hour (agregada)
```

| Tabla | Granularidad (una fila es...) | Filas (marzo 2024 + marzo 2025) |
| --- | --- | --- |
| `fact_trips` | un viaje aceptado por las reglas de calidad | 7.589.124 |
| `dim_zone` | una zona de taxi de la TLC | 265 |
| `dim_date` | un día calendario con al menos un viaje | 62 |
| `agg_zone_hour` | una zona de origen en una fecha y una hora de subida | 211.405 |

Tests de dbt sobre el modelo: claves únicas en las dimensiones, cada viaje apunta a una fecha y a dos zonas existentes (`relationships`) y la tabla agregada suma los mismos viajes e ingresos que la de hechos. Las preguntas están en `sql/preguntas/`, una por archivo, y sus resultados en `RESULTADOS.md`.

### Tests

`make test` corre 8 tests con pytest. Los que necesitan base usan una base aparte, `taxi_test`, que se crea al empezar y se borra al terminar.

| Test | Qué verifica |
| --- | --- |
| `test_calidad.py` | **Reglas sobre datos sintéticos:** con 8 viajes inventados, R01, R04+R10, R05, R07 (zona 999 y zona nula) y R08 van a cuarentena con su regla; R06 queda en válidos con el flag; el reporte da 8 = 2 + 6 |
| `test_ingesta.py` | **Idempotencia:** la segunda corrida no descarga ni agrega filas; si el archivo se corrompe, lo vuelve a bajar y reemplaza el mes sin duplicar. **Reintentos:** ante una falla de red, 3 reintentos y fila `error` en el log |
| `test_reconciliacion.py` | **Reconciliación:** pasa con los datos correctos y falla si se pierde una fila aceptada |
| `test_esquema.py` | Columna opcional faltante (nula), columna nueva (se reporta y no se carga), tipo distinto y obligatoria faltante (frenan) |
| `test_meses.py` | Cálculo del mes anterior y siguiente |

Además, cada corrida del pipeline ejecuta los 26 tests de datos de dbt (claves, nulos, valores aceptados, relaciones, reconciliación, que la capa curada no pierda filas y que la agregada cuadre).

## Observabilidad

- **Tablero "Postgres - base taxi":** conexiones, filas leídas y escritas por segundo, bloques desde memoria o disco, archivos temporales, transacciones y tamaño de la base (postgres-exporter). Al pie, los logs de Postgres: consultas de más de 1 segundo y checkpoints.
- **Tablero "Pipeline - procesos":** por etapa y mes, si terminó bien, cuánto tardó, pico de RAM, CPU y filas; los modelos de dbt más lentos; la duración de cada etapa a lo largo de las corridas. Lo publica `src/metricas.py` (psutil + Pushgateway). Al pie, los logs del pipeline y de Dagster.
- **Tablero "Preguntas de negocio - comparación de meses":** las 6 preguntas de la consigna, mes asignado contra el mismo mes del año anterior, leídas directamente de las tablas del esquema `preguntas` (origen de datos Postgres en Grafana). Se actualiza solo al terminar cada corrida.
- **Dagster:** cada corrida con sus pasos, duración, logs y el resultado de cada test de dbt.

Ejemplo de uso: el tablero de procesos mostró que la exportación tardaba 2,8 minutos en la Mac contra 23 segundos en Linux; la causa era escribir el CSV temporal en la carpeta compartida con la máquina. Lo movimos al disco del contenedor y la siguiente corrida bajó a 1,8 minutos.

## Limitaciones conocidas

- **Mac de 8 GB:** con todo el stack prendido, la memoria queda justa y el tiempo de dbt varía entre corridas (de 8,4 a 12 minutos medido) según lo que esté usando la máquina. Conviene darle a Docker Desktop entre 5 y 6 GB.
- **La primera ejecución** descarga las imágenes de Docker (varios GB) e instala las librerías: tarda bastante más que las siguientes.
- **dbt reconstruye todas las tablas en cada corrida** (no es incremental). Con dos meses son unos minutos; con muchos meses convendría materializar por mes.
- **La ingesta reintenta ante cualquier error de descarga,** también los que no se arreglan reintentando: un mes que todavía no está publicado devuelve `403` y espera 14 segundos en total antes de registrar el error.
- **Las tablas de calidad y del modelo guardan copias de los datos** (unos 8 a 9 GB de disco para los dos meses, entre Postgres y Parquet).
- **`R02` se multiplicó por 20 entre 2024 y 2025** (1.128 contra 22.280 filas). Casi todas son pagos con tarjeta con la misma hora exacta de subida y bajada; no sabemos la causa.
- **Windows:** Alloy lee los logs por el socket de Docker (`/var/run/docker.sock`), que Docker Desktop ofrece en esa ruta. Clonar el repo dentro de WSL evita la lentitud de las carpetas compartidas.

## Tiempo de ejecución y pico de RAM

Medido el 23/11/2026 en una MacBook Air M2 con 8 GB de RAM, con el pipeline completo orquestado por Dagster (`make all MES=2025-03`) y los datos ya descargados. Los números salen del tablero "Pipeline - procesos" y del log de Dagster. La corrida completa tardó **15 min 26 s** de punta a punta.

| Etapa | Duración | Pico de RAM del proceso | CPU |
| --- | --- | --- | --- |
| Ingesta sin cambios (por mes) | 0,4 a 2,7 s | 345 a 353 MB | menos de 1 s |
| Ingesta, primera carga (por mes) | 79 a 83 s | — | — |
| dbt: staging, calidad, curado, modelo, preguntas y 26 tests | 12 min (8,4 a 12 min según la corrida) | 550 MB (más Postgres, con techo de 1,5 GB) | 83 s |
| Exportación a Parquet (por mes) | 55 s (2024-03) y 100 s (2025-03) | 711 a 721 MB | 52 a 143 s |

dbt es lo que más tarda: reconstruye en cada corrida las tablas de los dos meses (unos 7,7 millones de filas) y su tiempo depende de cuánta memoria le queda libre a Postgres en la máquina. Polars corre con 2 hilos (`POLARS_MAX_THREADS`): con un hilo por núcleo, en la Mac la exportación llegaba a 1,2 GB y competía con Postgres.

Postgres tiene un techo de 1,5 GB y el resto de los contenedores, techos que suman menos de 3 GB más.

## Declaración de uso de IA

| Herramienta | Para qué se usó |
| --- | --- |
| GitHub Copilot | Generar la estructura inicial de carpetas y archivos vacíos (PR #1) |
| Claude | Guía paso a paso y explicación de conceptos y herramientas. Escribió la mayor parte del código y la configuración (docker-compose, Dockerfile, módulos de `src/`, SQL de dbt, tests y tableros de Grafana) a partir de nuestras decisiones, y redactó `DECISIONES.md`, `RESULTADOS.md` y este README a partir de nuestras corridas. Nosotros lo ejecutamos, lo revisamos y lo probamos en nuestras máquinas |
