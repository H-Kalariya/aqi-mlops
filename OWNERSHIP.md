# Owner: Shared (M1 as repo/release manager) — Path Ownership

# OWNERSHIP.md — AQI Forecaster MLOps

Every file has exactly one owner. "Shared" files are owned by M1 as repo/release manager.

## Ownership Table

| Path | Owner | Requirement |
|------|-------|-------------|
| `config.yaml` | Shared (M1) | Core configuration |
| `params.yaml` | M1 | Pipeline parameters |
| `README.md` | Shared (M1) | Documentation |
| `OWNERSHIP.md` | Shared (M1) | Ownership tracking |
| `Makefile` | Shared (M1) | Build automation |
| `.pre-commit-config.yaml` | M1 | Git hooks |
| `.gitignore` | Shared (M1) | Git config |
| `.dvcignore` | M1 | DVC config |
| `.env.example` | Shared (M1) | Environment template |
| `requirements.txt` | Shared (M1) | Full dependencies |
| `requirements-api.txt` | M2 | API runtime dependencies |
| `pyproject.toml` | Shared (M1) | Project metadata |
| `dvc.yaml` | M1 | DVC pipeline definition |
| `.dvc/` | M1 | DVC internals |
| `data/` | M1 | Data versioning (DVC-tracked) |
| `src/common/` | Shared (M1) | Shared interfaces & schemas |
| `src/ingest/` | M1 | Data ingestion |
| `src/validate/` | M1 | Data validation (Pandera) |
| `src/features/` | M1 | Feature engineering |
| `src/train/` | M1 | Model training |
| `src/evaluate/` | M1 | Model evaluation |
| `src/drift/` | M3 | Drift detection & promotion |
| `api/` | M2 | FastAPI serving |
| `Dockerfile` | M2 | Docker image |
| `docker-compose.yml` | M2 | Base compose stack |
| `deploy/` | M2 | Deployment strategies (nginx, scripts) |
| `monitoring/` | M3 | Prometheus, Grafana, Alertmanager |
| `.github/workflows/` | M3 | CI/CD pipelines |
| `scripts/` | M3 | Deployment & loop scripts |
| `tests/m1/` | M1 | M1 tests |
| `tests/m2/` | M2 | M2 tests |
| `tests/m3/` | M3 | M3 tests |
| `git_scenarios/m1/` | M1 | Git scenario: pre-commit, revert |
| `git_scenarios/m2/` | M2 | Git scenario: conflict, rebase |
| `git_scenarios/m3/` | M3 | Git scenario: cherry-pick, tags |
| `docs/DECISIONS.md` | Shared (M1) | Design decisions |
| `docs/member1_guide.md` | M1 | M1 member guide |
| `docs/member2_guide.md` | M2 | M2 member guide |
| `docs/member3_guide.md` | M3 | M3 member guide |
| `docs/demo_script.md` | Shared (M1) | Demo walkthrough |
| `handoff/` | Shared (M1) | Handoff packaging |
