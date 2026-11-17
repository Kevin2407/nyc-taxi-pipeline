# Pipeline NYC Taxi

## Cómo instalar y ejecutar

## Arquitectura

## Decisiones

El detalle fechado de cada decisión está en `DECISIONES.md`. Acá van las que pide la consigna.

### Esquema

- **Valor de `cbd_congestion_fee` en 2024: nulo.** El cargo de congestión no existía en 2024. Un 0 afirmaría que se evaluó y no se cobró; el nulo dice que el dato no existe. Además `avg()` ignora los nulos, mientras que un 0 bajaría cualquier promedio. En la tabla unificada, las 3.582.628 filas de marzo 2024 tienen nulo y las 4.145.257 de marzo 2025 tienen valor.
- **Si aparece una columna que no está en el contrato:** el pipeline la reporta como "nueva", no la carga y sigue. Las columnas conocidas siguen siendo válidas, así que no hay motivo para frenar. Para incorporarla hay que agregarla a `contracts/yellow_schema.yaml` y subir el número de versión, y ese cambio queda registrado en Git.
- **Si falta una columna obligatoria o cambia un tipo:** el pipeline frena con código de salida distinto de 0 y no carga el archivo.
- **Si falta una columna opcional** (hoy solo `cbd_congestion_fee`): se reporta y se completa con nulo.

### Calidad

Las reglas están en `contracts/reglas_calidad.yaml`, cada una con identificador, descripción, severidad, umbral y justificación. Las mediciones que las respaldan están en `exploracion/HALLAZGOS.md`.

Criterio de severidad: **rechazo** cuando la fila describe algo imposible o no se puede asignar a un mes o a una zona; **advertencia** cuando un dato es dudoso o falta, pero el viaje existió y se cobró.

| Id | Regla | Severidad | Umbral | Por qué |
| --- | --- | --- | --- | --- |
| R01 | Subida fuera del mes del archivo | rechazo | Mes calendario del archivo | Quedaría en la partición equivocada |
| R02 | Bajada anterior o igual a la subida | rechazo | Duración > 0 | Duración imposible; no se puede calcular velocidad |
| R03 | Distancia menor o igual a 0 | advertencia | Distancia > 0 | El 95 % se cobró normalmente: falta el dato, no el viaje |
| R04 | Distancia excesiva | rechazo | 100 millas | El 99,99 % mide menos de 58; lo que pasa de 100 es error de carga |
| R05 | Importe total negativo | rechazo | Total >= 0 | Ajustes de disputas y viajes sin cargo, no precios |
| R06 | Pasajeros nulo o 0 | advertencia | Al menos 1 | Afecta al 13 % y al 22,7 %; no interviene en ningún cálculo |
| R07 | Zona de origen o destino inexistente | rechazo | Existir en la tabla de zonas | No se puede enriquecer ni modelar |
| R08 | Duplicado exacto | rechazo | Todas las columnas iguales | Contaría dos veces el mismo viaje; se conserva una copia |
| R09 | Tarifa base menor o igual a 0 (propia) | advertencia | Tarifa > 0 | Viajes cobrados con tarifa inservible; se excluyen de los cálculos sobre tarifa |
| R10 | Velocidad promedio imposible (propia) | rechazo | 80 mph | El 99,9 % promedia menos de 49 mph |
| R11 | Zona 264 o 265 (propia) | advertencia | Zonas 1 a 263 | Existen en la tabla pero no son un lugar real |

**Tratamiento de nulos**

- `cbd_congestion_fee` es nulo en 2024 (ver Esquema).
- `passenger_count` nulo no se completa ni se rechaza: se marca con R06.
- Una condición que da nulo porque le falta un dato se toma como "no viola la regla".
- La velocidad queda nula cuando la distancia es menor o igual a 0, y la propina como porcentaje de la tarifa queda nula cuando la tarifa es menor o igual a 0.

**Resultado de la validación** (salida de `python -m src.calidad --mes AAAA-MM`)

| | Marzo 2024 | Marzo 2025 |
| --- | --- | --- |
| Filas leídas | 3.582.628 | 4.145.257 |
| Aceptadas | 3.535.924 | 4.053.200 |
| En cuarentena | 46.704 (1,30 %) | 92.057 (2,22 %) |

En los dos meses se cumple leídas = aceptadas + cuarentena. Si no se cumpliera, el pipeline termina con código de salida 1.

### Transformación

Columnas derivadas de la capa curada:

| Columna | Cálculo | Cuándo queda nula |
| --- | --- | --- |
| `duracion_min` | segundos entre subida y bajada / 60 | nunca (R02 rechaza duraciones <= 0) |
| `velocidad_mph` | distancia / duración en horas | distancia <= 0 (R03) |
| `fecha_subida` | fecha de la subida | nunca |
| `hora_subida` | hora de la subida, 0 a 23 | nunca |
| `dia_semana` | día ISO: 1 lunes, 7 domingo | nunca |
| `propina_pct` | propina / tarifa x 100 | tarifa <= 0 (R09) |
| `pu_borough`, `pu_zone`, `do_borough`, `do_zone` | cruce con la tabla de zonas | nunca (R07 garantiza que la zona existe) |

**Reprocesar un mes reemplaza solo su partición.** Prueba del 17/11/2026: se escribieron los dos meses y después se reprocesó solo marzo 2025.

| Partición | Filas antes | Archivo antes | Filas después | Archivo después |
| --- | --- | --- | --- | --- |
| `year=2024/month=03` | 3.535.924 | 136.506.067 bytes, 15:37 | 3.535.924 | 136.506.067 bytes, 15:37 (sin tocar) |
| `year=2025/month=03` | 4.053.200 | 158.539.385 bytes, 15:37 | 4.053.200 | 158.640.007 bytes, 15:39 (reescrito) |

Los conteos se obtienen con `python -m src.transformacion --mes AAAA-MM`, que al final cuenta las filas de cada partición leyendo los archivos.

### Modelo

Modelo estrella en `data/taxi.duckdb`, construido por `src/modelo.py` con los SQL de `sql/modelo/` a partir de la capa curada.

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

`agg_zone_hour` tiene viajes, ingreso total (`sum(total_amount)`) y duración media en minutos. Las preguntas de negocio están en `sql/preguntas/`, una por archivo, y sus resultados en `RESULTADOS.md`.

## Limitaciones conocidas

- La ingesta reintenta ante cualquier error de descarga, también los que no se arreglan reintentando. Un mes que todavía no está publicado devuelve `403 Forbidden` (probado con `2031-01`) y el script espera 14 segundos en total antes de registrar el error.
- El `ingestion_log` vive en `data/taxi.duckdb`. Si se borra la carpeta `data/`, se pierde el historial y la siguiente corrida descarga todo de nuevo.
- La tabla `yellow_trips` se crea con las columnas del contrato la primera vez. Si el contrato cambia, hay que borrar `data/taxi.duckdb` y volver a correr el pipeline.
- La detección de duplicados compara todas las columnas de todas las filas del mes. Es el paso que más memoria usa del pipeline.
- Reprocesar un mes da las mismas filas, pero el archivo Parquet puede variar unos bytes, porque el orden de las filas no está fijado y eso cambia la compresión. Ordenar al escribir lo haría idéntico a costa de más tiempo y memoria.

## Tiempo de ejecución y pico de RAM

## Declaración de uso de IA

| Herramienta | Para qué se usó |
| --- | --- |
| GitHub Copilot | Generar la estructura inicial de carpetas y archivos vacíos (PR #1) |
| Claude | Guía paso a paso y explicación de conceptos y herramientas. Propuesta del código Python de `src/`, que escribimos, ejecutamos y probamos nosotros. Redacción de `exploracion/HALLAZGOS.md`, `DECISIONES.md`, `RESULTADOS.md` y las secciones de decisiones de este README a partir de nuestras corridas. Escribió los scripts `exploracion/explorar_umbrales.py` y `exploracion/explorar_resultados.py`, y los SQL de `sql/modelo/` y `sql/preguntas/` |
