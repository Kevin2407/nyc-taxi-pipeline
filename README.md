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

## Limitaciones conocidas

- La ingesta reintenta ante cualquier error de descarga, también los que no se arreglan reintentando. Un mes que todavía no está publicado devuelve `403 Forbidden` (probado con `2031-01`) y el script espera 14 segundos en total antes de registrar el error.
- El `ingestion_log` vive en `data/taxi.duckdb`. Si se borra la carpeta `data/`, se pierde el historial y la siguiente corrida descarga todo de nuevo.
- La tabla `yellow_trips` se crea con las columnas del contrato la primera vez. Si el contrato cambia, hay que borrar `data/taxi.duckdb` y volver a correr el pipeline.

## Tiempo de ejecución y pico de RAM

## Declaración de uso de IA

| Herramienta | Para qué se usó |
| --- | --- |
| GitHub Copilot | Generar la estructura inicial de carpetas y archivos vacíos (PR #1) |
| Claude | Guía paso a paso, explicación de conceptos y herramientas, propuesta de código que escribimos y probamos nosotros, y redacción de `exploracion/HALLAZGOS.md` y `DECISIONES.md` a partir de nuestras mediciones |
