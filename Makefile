# Pipeline NYC Taxi.
#
# Uso:
#   make all MES=2025-03     corre todo para el mes y el mismo mes del año anterior
#   make test                corre los tests automáticos
#   make limpiar-datos       borra data/ para correr desde cero
#
# Si no se pasa MES, se usa 2025-03. El mes de comparación se calcula solo.

MES ?= 2025-03
MES_ANTERIOR := $(shell echo $(MES) | awk -F- '{ printf "%d-%s", $$1 - 1, $$2 }')

# Python con el que se crea el entorno virtual. Se puede cambiar, por ejemplo:
#   make all PYTHON_BASE=/opt/anaconda3/envs/py311/bin/python
PYTHON_BASE ?= python3
VENV := .venv
PYTHON := $(VENV)/bin/python

.PHONY: all ingesta esquema calidad transformacion modelo test limpiar-datos

all: modelo

INSTALADO := $(VENV)/.instalado

# Crea el entorno virtual, solo si no existe.
$(PYTHON):
	$(PYTHON_BASE) -m venv $(VENV)

# Instala las dependencias. Se vuelve a correr solo si cambia requirements.txt.
$(INSTALADO): requirements.txt | $(PYTHON)
	$(PYTHON) -m pip install --quiet -r requirements.txt
	touch $(INSTALADO)

ingesta: $(INSTALADO)
	@echo "== 1. Ingesta: $(MES) y $(MES_ANTERIOR) =="
	$(PYTHON) -m src.ingesta --mes $(MES)
	$(PYTHON) -m src.ingesta --mes $(MES_ANTERIOR)

esquema: ingesta
	@echo "== 2. Esquema =="
	$(PYTHON) -m src.esquema --mes $(MES)
	$(PYTHON) -m src.esquema --mes $(MES_ANTERIOR)

calidad: esquema
	@echo "== 3. Calidad =="
	$(PYTHON) -m src.calidad --mes $(MES)
	$(PYTHON) -m src.calidad --mes $(MES_ANTERIOR)

transformacion: calidad
	@echo "== 4. Transformación =="
	$(PYTHON) -m src.transformacion --mes $(MES)
	$(PYTHON) -m src.transformacion --mes $(MES_ANTERIOR)

modelo: transformacion
	@echo "== 5. Modelo y preguntas =="
	$(PYTHON) -m src.modelo --mes $(MES)

test: $(INSTALADO)
	$(PYTHON) -m pytest -q

# Si el Finder de macOS crea un .DS_Store mientras se borra, rm falla; se reintenta una vez.
limpiar-datos:
	rm -rf data || (sleep 1 && rm -rf data)
