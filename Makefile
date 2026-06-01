.PHONY: dev dev-backend dev-frontend dev-worker dev-beat migrate seed install-backend install-frontend test

# ─── Environment ─────────────────────────────────────────────────────────────
# Activate venv automatically if it exists
VENV        := $(shell [ -d .venv ] && echo "source .venv/bin/activate &&" || echo "")
PG_PATH     := /opt/homebrew/opt/postgresql@16/bin
PY_PATH     := /opt/homebrew/opt/python@3.12/bin
NODE_PATH   := /opt/homebrew/opt/node@20/bin
EXPORT_PATH := export PATH="$(PY_PATH):$(PG_PATH):$(NODE_PATH):$$PATH" &&
PYTHONPATH_EXPORT := export PYTHONPATH="$$(pwd)" &&
DB_URL      ?= postgresql+asyncpg://lms_user:lms_pass@localhost:5432/lms_db

# ─── Local development (no Docker) ──────────────────────────────────────────

dev:
	./dev.sh

dev-backend:
	$(EXPORT_PATH) $(VENV) $(PYTHONPATH_EXPORT) cd backend && uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	$(EXPORT_PATH) cd frontend && npm run dev

dev-worker:
	$(EXPORT_PATH) $(VENV) $(PYTHONPATH_EXPORT) cd backend && celery -A backend.tasks worker --loglevel=info

dev-beat:
	$(EXPORT_PATH) $(VENV) $(PYTHONPATH_EXPORT) cd backend && celery -A backend.tasks beat --loglevel=info

# ─── Database ─────────────────────────────────────────────────────────────────

migrate:
	$(EXPORT_PATH) $(VENV) $(PYTHONPATH_EXPORT) export DATABASE_URL=$(DB_URL) && cd backend && alembic upgrade head

migrate-down:
	$(EXPORT_PATH) $(VENV) $(PYTHONPATH_EXPORT) export DATABASE_URL=$(DB_URL) && cd backend && alembic downgrade -1

seed:
	$(EXPORT_PATH) $(VENV) $(PYTHONPATH_EXPORT) set -a && [ -f backend/.env ] && . backend/.env; set +a && export DATABASE_URL=$${DATABASE_URL:-$(DB_URL)} && cd backend && python3 -m backend.scripts.seed

# ─── Install ──────────────────────────────────────────────────────────────────

install-backend:
	$(EXPORT_PATH) python3.12 -m venv .venv && source .venv/bin/activate && pip install -e "backend/."

install-frontend:
	$(EXPORT_PATH) cd frontend && npm install --legacy-peer-deps

# ─── Testing ──────────────────────────────────────────────────────────────────

test:
	$(EXPORT_PATH) $(VENV) $(PYTHONPATH_EXPORT) cd backend && pytest tests/test_payment_calculator.py tests/test_status_machine.py tests/test_auth.py -v

test-all:
	$(EXPORT_PATH) $(VENV) $(PYTHONPATH_EXPORT) cd backend && pytest tests/ -v

# ─── Migration from Sheets ───────────────────────────────────────────────────

install-migration:
	$(EXPORT_PATH) $(VENV) pip install -r migration/requirements.txt

migration-extract:
	$(EXPORT_PATH) $(VENV) python3 migration/extract.py

migration-transform:
	$(EXPORT_PATH) $(VENV) python3 migration/transform.py

migration-load:
	$(EXPORT_PATH) $(VENV) export DATABASE_URL=$(DB_URL) && python3 migration/load.py

migration-verify:
	$(EXPORT_PATH) $(VENV) export DATABASE_URL=$(DB_URL) && python3 migration/verify.py

# ─── RSA Keys (run once) ─────────────────────────────────────────────────────

gen-keys:
	@mkdir -p backend/keys
	openssl genrsa -out backend/keys/private.pem 2048
	openssl rsa -in backend/keys/private.pem -pubout -out backend/keys/public.pem
	@echo "Keys generated in backend/keys/"
	@echo "Next: paste them into backend/.env as JWT_PRIVATE_KEY and JWT_PUBLIC_KEY"
