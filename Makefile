# Owner: Shared (M1 as repo/release manager) — Build automation
.PHONY: setup data train serve up down scale canary rollout rollback test lint drift loop clean

# ── Setup ──
setup:
	pip install -r requirements.txt
	pre-commit install
	@echo "✅ Setup complete"

# ── M1: Data & Training ──
data:
	python -m src.ingest.run
	python -m src.validate.run
	python -m src.features.run
	@echo "✅ Data pipeline complete"

train:
	python -m src.train.run
	python -m src.evaluate.run
	@echo "✅ Training complete"

# ── M2: Serving ──
serve:
	uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

# ── M2: Docker Compose ──
up:
	docker compose up -d --build
	@echo "✅ Stack is up"

down:
	docker compose down -v
	@echo "✅ Stack is down"

scale:
	docker compose -f docker-compose.yml -f deploy/docker-compose.scale.yml up -d --build --scale api=3
	@echo "✅ Scaled to 3 replicas behind nginx"

canary:
	docker compose -f docker-compose.yml -f deploy/docker-compose.canary.yml up -d --build
	@echo "✅ Canary deployment active (9:1 split)"

# ── M2: Deployment ──
rollout:
	@if [ -z "$(TAG)" ]; then echo "Usage: make rollout TAG=<new_tag>"; exit 1; fi
	bash deploy/scripts/rolling_update.sh $(TAG)

rollback:
	bash deploy/scripts/rollback.sh

# ── Testing & Linting ──
test:
	pytest tests/ -v --tb=short

lint:
	ruff check src/ api/ tests/
	black --check src/ api/ tests/

# ── M3: Drift & Continuous Training ──
drift:
	python -m src.drift.drift_check
	@echo "✅ Drift check complete"

loop:
	bash scripts/run_full_loop.sh

# ── Cleanup ──
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage
	@echo "✅ Cleaned"
