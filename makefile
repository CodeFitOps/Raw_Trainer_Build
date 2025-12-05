# Makefile para RawTrainer_build

VENV ?= .venv
PYTHON ?= $(VENV)/bin/python

# ---------- Setup básico ----------

.PHONY: init
init:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

# ---------- Calidad / tests ----------

.PHONY: test
test:
	$(PYTHON) -m pytest

# Aquí en el futuro podemos añadir linters:
# .PHONY: lint
# lint:
# 	$(PYTHON) -m ruff src tests

# ---------- CLI / App ----------

.PHONY: run
run:
	$(PYTHON) main.py

# Validar un workout:
# uso: make validate FILE=path/to/workout.yaml
.PHONY: validate
validate:
	@if [ -z "$(FILE)" ]; then \
	  echo "ERROR: debes pasar FILE=..."; \
	  exit 1; \
	fi
	$(PYTHON) main.py validate $(FILE)

# Previsualizar + opción de run manual:
# uso: make preview FILE=path/to/workout.yaml
.PHONY: preview
preview:
	@if [ -z "$(FILE)" ]; then \
	  echo "ERROR: debes pasar FILE=..."; \
	  exit 1; \
	fi
	$(PYTHON) main.py preview $(FILE)

# Importar workout en el repositorio local gestionado:
# uso: make import FILE=/ruta/al/workout.yaml
.PHONY: import
import:
	@if [ -z "$(FILE)" ]; then \
	  echo "ERROR: debes pasar FILE=..."; \
	  exit 1; \
	fi
	$(PYTHON) main.py import $(FILE)

# ---------- Utilidades internas ----------

# Regenerar bloque de alias para ~/.zshrc
.PHONY: aliases
aliases:
	$(PYTHON) internal_tools/generate_shell_aliases.py --workouts-dir data/workouts_files
	$(PYTHON) internal_tools/generate_shell_aliases.py --workouts-dir data/workouts_files