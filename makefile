VENV := .venv
PYTHON := $(VENV)/bin/python

# --------- Setup básico ---------
.PHONY: init init-dev test

init:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

# init-dev = entorno de desarrollo (extiende init)
init-dev: init
	$(PYTHON) -m pip install -r requirements-dev.txt

# --------- Calidad / tests ---------
test:
	$(PYTHON) -m pytest