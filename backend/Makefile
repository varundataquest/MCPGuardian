PY?=python3
PIP?=pip

.PHONY: dev
dev:
	PYTHONPATH=backend uvicorn app.main:app --reload --port 8000

.PHONY: install
install:
	$(PIP) install -r requirements.txt

.PHONY: smoke
smoke:
	PYTHONPATH=backend $(PY) backend/scripts/smoke_pipeline.py

.PHONY: test
test:
	PYTHONPATH=backend pytest -q


