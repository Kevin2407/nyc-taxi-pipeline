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
| 2026-11-16 | Las reglas violadas se guardan como texto separado por comas (`R04,R10`) en dos columnas: `reglas_violadas` (rechazos) y `flags` (advertencias) | Se lee a simple vista en una consulta y se arma con `CASE WHEN` + `concat_ws`, sin funciones avanzadas. Si `reglas_violadas` no está vacío, la fila va a cuarentena |
| 2026-11-16 | Una condición que da nulo cuenta como "no viola la regla" | `CASE WHEN` solo marca cuando la condición es verdadera. Si falta el dato no podemos afirmar que la fila esté mal |
| 2026-11-16 | Duplicados con `row_number()` particionando por todas las columnas del contrato; se rechaza `copia > 1` | Numera las filas idénticas: la primera se conserva y las demás van a cuarentena |
| 2026-11-16 | Salidas de calidad: tablas `trips_validos`, `cuarentena`, `reporte_calidad` y `reporte_calidad_reglas` en `data/taxi.duckdb` | Todo se consulta con SQL. Cada mes se borra antes de insertarse, así que reprocesar no duplica (probado corriendo 2025-03 dos veces) |
| 2026-11-16 | La reconciliación cuenta leídas, aceptadas y cuarentena en tres tablas distintas y corta con código 1 si no cierra | Contarlas por separado es lo que hace que el control sirva. Resultado: 3.582.628 = 3.535.924 + 46.704 y 4.145.257 = 4.053.200 + 92.057 |
| 2026-11-16 | La cuarentena guarda la fila con los nombres de columna ya normalizados | Los valores son los originales, sin modificar; solo cambia el nombre de la columna, igual que en `yellow_trips` |
| 2026-11-17 | La capa curada se escribe en Parquet, un archivo por mes en `data/curated/yellow/year=AAAA/month=MM/trips.parquet` | Parquet lo lee cualquier herramienta sin depender de nuestra base. Con un archivo por partición, reprocesar un mes es reemplazar un archivo |
| 2026-11-17 | La partición se escribe a un `.tmp` y se renombra al terminar | Si el proceso se corta, la partición anterior queda intacta. Misma técnica que la ingesta |
| 2026-11-17 | `velocidad_mph` queda nula si la distancia es <= 0 (R03); `propina_pct` queda nula si la tarifa es <= 0 (R09) | Un 0 mph sería un dato falso, y dividir por una tarifa nula o negativa da error o un porcentaje sin sentido. La duración no necesita protección porque R02 ya rechaza duraciones <= 0 |
| 2026-11-17 | `dia_semana` con `isodow`: 1 es lunes y 7 es domingo | Es el estándar ISO 8601; evita la ambigüedad de si la semana empieza en domingo o en lunes |
| 2026-11-17 | Zonas con `LEFT JOIN`, dos veces (origen y destino) | Conserva todos los viajes aunque faltara una zona. R07 ya garantiza que existen, así que no queda ninguna nula |
| 2026-11-17 | Después de escribir, se cuentan las filas del archivo y se comparan con `trips_validos`; si no coinciden, código 1 | Control barato de que el JOIN no perdió ni duplicó filas |
| 2026-11-17 | Modelo estrella como tablas en `data/taxi.duckdb`, construidas desde la capa curada en Parquet | La capa curada es la fuente; el modelo se reconstruye entero en cada corrida (unos segundos) y así nunca queda desfasado |
| 2026-11-17 | `fact_trips` guarda claves y medidas, sin nombres de zona ni atributos de fecha | Esa información vive una sola vez en `dim_zone` y `dim_date`; es la separación que define un modelo estrella |
| 2026-11-17 | `dim_date` incluye `anio_mes` (texto `AAAA-MM`) | Todas las preguntas filtran por mes con esa columna, cruzando con la dimensión |
| 2026-11-17 | Un archivo SQL por tabla del modelo (`sql/modelo/01..04`) y por pregunta (`sql/preguntas/a..f`), ejecutados en orden por `src/modelo.py` | Lo pide la consigna; además cada consulta se lee sin abrir el Python. La numeración fija el orden: `agg_zone_hour` depende de `fact_trips` |
| 2026-11-17 | Las preguntas (a) y (b) usan `agg_zone_hour`; las demás, `fact_trips` | La agregada responde por zona y hora con ~211.000 filas en vez de 7,6 millones. El resto necesita columnas que la agregada no tiene |
| 2026-11-17 | Ingreso promedio por hora = ingreso total / viajes, no promedio de promedios | Promediar promedios de zonas con distinta cantidad de viajes da un número incorrecto |
| 2026-11-17 | Tarifa media sin viajes con tarifa <= 0 (R09) | Su tarifa base no es válida y bajaría el promedio |
| 2026-11-17 | Rankings por zona sin las zonas 264 y 265 (R11) | No son un lugar real |
| 2026-11-17 | Pregunta (c): solo zonas con al menos 1.000 viajes en el mes | Sin mínimo, el ranking lo encabezan zonas con 1 o 2 viajes al 100 %, que no dicen nada |
| 2026-11-17 | El mes de comparación es el mismo mes del año anterior, calculado a partir de `--mes` | Lo pide la consigna; así el comando recibe un solo parámetro |
| 2026-11-17 | Makefile con un objetivo por etapa, encadenados por dependencias (`all → modelo → transformacion → calidad → esquema → ingesta`) | Se puede correr el pipeline entero o hasta una etapa. Make frena en el primer comando que devuelve código distinto de 0 |
| 2026-11-17 | El mes de comparación lo calcula el Makefile (`MES_ANTERIOR`) restando un año a `MES` | El comando recibe un solo parámetro, como pide la consigna |
| 2026-11-17 | El Makefile crea `.venv` si no existe y reinstala dependencias solo si cambió `requirements.txt` (marca `.venv/.instalado`) | Quien clona corre un solo comando sin preparar nada. Las corridas siguientes no reinstalan |
| 2026-11-17 | `PYTHON_BASE` configurable (por defecto `python3`) | El Python por defecto de cada máquina es distinto; en la Mac de Kevin `python3` es 3.14 y usamos 3.11 |
| 2026-11-17 | El Makefile lo escribió Claude directamente en el repo | Las líneas de comandos de Make tienen que empezar con tabulador, y al copiar desde un chat suelen quedar espacios |
| 2026-11-17 | Tests con datos sintéticos (4 o 5 viajes inventados) en una base temporal | Se sabe de antemano qué tiene que pasar con cada fila, corren en menos de un segundo y no tocan `data/` |
| 2026-11-17 | El test de ingesta reemplaza la descarga por una falsa con `monkeypatch` | No depende de internet y permite contar cuántas veces se intentó descargar |
| 2026-11-17 | La reconciliación se separó en la función `reconciliacion_cierra` | Se puede probar sola con números inventados, incluido el caso en que no cierra, que con datos reales nunca pasa |
| 2026-11-17 | El test de calidad cubre una regla de rechazo, una de advertencia y los duplicados | La consigna pide al menos una regla; así el mismo test prueba los tres caminos posibles de una fila |
