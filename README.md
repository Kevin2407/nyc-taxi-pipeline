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

## Limitaciones conocidas

- La ingesta reintenta ante cualquier error de descarga, también los que no se arreglan reintentando. Un mes que todavía no está publicado devuelve `403 Forbidden` (probado con `2031-01`) y el script espera 14 segundos en total antes de registrar el error.
- El `ingestion_log` vive en `data/taxi.duckdb`. Si se borra la carpeta `data/`, se pierde el historial y la siguiente corrida descarga todo de nuevo.
- La tabla `yellow_trips` se crea con las columnas del contrato la primera vez. Si el contrato cambia, hay que borrar `data/taxi.duckdb` y volver a correr el pipeline.

## Tiempo de ejecución y pico de RAM

## Declaración de uso de IA

| Herramienta | Para qué se usó |
| --- | --- |
| GitHub Copilot | Generar la estructura inicial de carpetas y archivos vacíos (PR #1) |
| Claude | Guía paso a paso, explicación de conceptos y herramientas, propuesta de código que escribimos y probamos |
