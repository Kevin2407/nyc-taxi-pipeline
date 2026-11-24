# Pipeline NYC Taxi. Todo corre en Docker: estos objetivos son atajos de "docker compose".
# En Windows sin make, cada objetivo se corre copiando su comando (ver README).
#
#   make all MES=2025-03     comando único: levanta todo y corre el pipeline completo
#   make reporte             demo: reporte de calidad y filas en cuarentena
#   make respuestas          las 6 respuestas de negocio
#   make test                tests automáticos
#   make levantar / apagar   prende o apaga la plataforma (Dagster, Grafana, Postgres...)
#   make explorar            consultas de exploración (exploracion/*.sql) sobre los datos cargados
#
# Etapas sueltas, sin Dagster (para desarrollo o para mostrarlas de a una):
#   make ingesta | esquema | calidad | transformacion | modelo
#   make reprocesar MES=...  vuelve a escribir solo la partición Parquet de ese mes (demo 4.4)

MES ?= 2025-03
MES_ANTERIOR := $(shell echo $(MES) | awk -F- '{ printf "%d-%s", $$1 - 1, $$2 }')
CORRER := docker compose run --rm -e MES=$(MES) herramientas

.PHONY: all levantar apagar reporte respuestas test explorar ingesta esquema calidad transformacion reprocesar modelo limpiar

all:
	docker compose run --rm -e MES=$(MES) pipeline

levantar:
	docker compose up -d

apagar:
	docker compose down

reporte:
	$(CORRER) python -m src.calidad --mes $(MES) --solo-reporte

respuestas:
	$(CORRER) python -m src.modelo --mes $(MES) --solo-respuestas

test:
	docker compose run --rm herramientas pytest

# Corre cada consulta de exploracion/ en Postgres y muestra el resultado.
explorar:
	docker compose up -d --wait postgres
	for f in exploracion/0*.sql; do echo "=== $$f"; docker compose exec -T postgres psql -U taxi -d taxi < $$f || exit 1; done

ingesta:
	$(CORRER) python -m src.ingesta --mes $(MES)
	$(CORRER) python -m src.ingesta --mes $(MES_ANTERIOR)

esquema:
	$(CORRER) python -m src.esquema --mes $(MES)
	$(CORRER) python -m src.esquema --mes $(MES_ANTERIOR)

calidad:
	$(CORRER) python -m src.calidad --mes $(MES)

transformacion:
	$(CORRER) python -m src.transformacion --mes $(MES)
	$(CORRER) python -m src.transformacion --mes $(MES_ANTERIOR) --solo-parquet

reprocesar:
	$(CORRER) python -m src.transformacion --mes $(MES) --solo-parquet

modelo:
	$(CORRER) python -m src.modelo --mes $(MES)

# Borra TODO lo generado (volúmenes de Docker y data/) para probar desde cero.
limpiar:
	docker compose down -v
	rm -rf data || (sleep 1 && rm -rf data)
