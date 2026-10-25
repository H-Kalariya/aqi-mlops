# Contribution Summary & Division of Labor

This document summarizes the exact contribution breakdown, owned requirements, source directories, and line counts for the 3 team members.

---

## 1. High-Level Allocation

| Member | Focus Area | Owned Rubric Items | Weight | Git Scenario |
|---|---|---|---|---|
| **Member 1** | Data Pipeline & Experiment Tracking | Data Versioning (DVC), Ingestion/Validation/Features/Training Pipeline, MLflow Registry (@champion/@challenger) | ~33% | Pre-commit quality gating + bad commit `git revert` |
| **Member 2** | Serving & Deployment Strategies | FastAPI REST API, Docker multi-stage containerization, Nginx reverse proxy, 3 replicas, zero-downtime rolling update, rollback, 9:1 canary | ~33% | Merge conflict on `config.yaml` + feature branch rebase |
| **Member 3** | Monitoring & Continuous Training | Prometheus & Grafana observability, Alertmanager rules, GitHub Actions CI/CD workflows, Evidently data drift detection, closed-loop model promotion | ~33% | Production hotfix cherry-pick + semantic release tags (`v1.0`, `v1.1`) |

---

## 2. Detailed Per-Member File & Line Count Summary

### Member 1: Pipeline & Experimentation
- **Primary Directories:** `src/ingest/`, `src/validate/`, `src/features/`, `src/train/`, `src/evaluate/`, `tests/m1/`, `git_scenarios/m1/`
- **Key Files & Ownership:**
  - `src/ingest/synthetic.py`: Realistic synthetic generator with seasonality, Diwali spike, diurnal cycles (~280 lines)
  - `src/ingest/clients.py`: Data.gov.in & OpenAQ API clients with rate-limiting and retry backoff (~140 lines)
  - `src/ingest/snapshot.py`: Offline fallback snapshot loader (~60 lines)
  - `src/ingest/run.py`: Ingestion orchestrator CLI (~90 lines)
  - `src/validate/run.py`: Pandera schema validation report generator (~170 lines)
  - `src/features/run.py`: Lags, rolling window statistics, calendar features, stacked multi-horizon dataset (~270 lines)
  - `src/train/run.py`: LightGBM regressor training, MLflow parameter/metric logging, model registration (~270 lines)
  - `src/evaluate/run.py`: Holdout evaluation, per-horizon MAE/RMSE calculation, `metrics.json` export (~170 lines)
  - `dvc.yaml` & `params.yaml`: Reproducible multi-stage pipeline configuration (~80 lines)
  - `.pre-commit-config.yaml`: Automated code quality hooks (~25 lines)
  - `tests/m1/test_pipeline.py`: Unit and integration tests for data and features (~60 lines)
  - `git_scenarios/m1/scenario_m1.sh` & README: Pre-commit failure demo & git revert (~110 lines)
  - `docs/member1_guide.md`: Viva defense guide with 12 Q&As (~180 lines)
- **Total M1 Lines:** ~1,905 lines of clean, tested code and documentation.

---

### Member 2: Serving & Production Deployment
- **Primary Directories:** `api/`, `deploy/`, `tests/m2/`, `git_scenarios/m2/`
- **Key Files & Ownership:**
  - `api/app.py`: FastAPI server with lifespan loader, latency/error middleware, version headers (~190 lines)
  - `api/schemas.py`: Pydantic request/response schemas with field validation (~90 lines)
  - `api/metrics.py`: Fixed Prometheus metrics registry and text generator (~65 lines)
  - `api/model_loader.py`: Resilient model loader with MLflow registry support, local fallback, and inference pipeline (~240 lines)
  - `Dockerfile`: Multi-stage build with non-root security UID 1000 (~55 lines)
  - `docker-compose.yml`: Base stack orchestration (api, mlflow, prometheus, grafana, alertmanager) (~110 lines)
  - `deploy/docker-compose.scale.yml`: Scaled 3-replica API compose override (~30 lines)
  - `deploy/docker-compose.canary.yml`: 9:1 canary compose configuration (~55 lines)
  - `deploy/nginx/nginx.conf`: Nginx load-balancing reverse proxy configuration (~45 lines)
  - `deploy/nginx/nginx.canary.conf`: Nginx 9:1 weighted upstream configuration (~45 lines)
  - `deploy/scripts/release_log.sh`: Deployment audit log generator (~85 lines)
  - `deploy/scripts/rolling_update.sh`: Zero-downtime rolling update with live traffic probe (~135 lines)
  - `deploy/scripts/rollback.sh`: Automated rollback engine (~65 lines)
  - `deploy/scripts/canary_demo.sh`: 200-request canary distribution verification script (~115 lines)
  - `tests/m2/test_api.py`: FastAPI unit tests with stub booster and header checks (~80 lines)
  - `git_scenarios/m2/scenario_m2.sh` & README: Deliberate conflict resolution & rebase (~145 lines)
  - `docs/member2_guide.md`: Viva defense guide with 12 Q&As (~210 lines)
- **Total M2 Lines:** ~1,760 lines of serving, containerization, and release engineering.

---

### Member 3: Observability, CI/CD & Continuous Training
- **Primary Directories:** `monitoring/`, `.github/workflows/`, `src/drift/`, `scripts/`, `tests/m3/`, `git_scenarios/m3/`
- **Key Files & Ownership:**
  - `monitoring/prometheus.yml`: Scrape configurations with DNS service discovery (~35 lines)
  - `monitoring/alert_rules.yml`: Rules for APIDown, HighErrorRate, HighLatencyP95, PredictionDistributionShift (~50 lines)
  - `monitoring/alertmanager.yml`: Alert notification routing and webhook receivers (~30 lines)
  - `monitoring/grafana/provisioning/`: Datasource and dashboard provisioning (~25 lines)
  - `monitoring/grafana/dashboards/aqi_dashboard.json`: 5-panel production dashboard JSON (~175 lines)
  - `.github/workflows/ci.yml`: Automated CI workflow (linting, tests, synthetic run, docker build) (~85 lines)
  - `.github/workflows/cd.yml`: Automated CD workflow (build, GHCR publish, rolling rollout) (~65 lines)
  - `.github/workflows/drift-check.yml`: Scheduled daily cron drift evaluation and retrain dispatch (~50 lines)
  - `.github/workflows/retrain.yml`: Retraining and model promotion workflow (~45 lines)
  - `src/drift/drift_check.py`: Evidently & statistical KS drift detection engine (~230 lines)
  - `src/drift/inject_drift.py`: Synthetic pollution shift generator CLI (~120 lines)
  - `src/drift/promote.py`: Champion vs Challenger performance comparator & hot-reload caller (~235 lines)
  - `scripts/deploy_local.sh`: Local build and rolling deployment runner (~65 lines)
  - `scripts/run_full_loop.sh`: End-to-end closed loop demo script (~95 lines)
  - `tests/m3/test_continuous_training.py`: Tests for drift detection & promotion decisions (~55 lines)
  - `git_scenarios/m3/scenario_m3.sh` & README: Hotfix cherry-pick & semantic release tagging (~120 lines)
  - `docs/member3_guide.md`: Viva defense guide with 12 Q&As (~200 lines)
- **Total M3 Lines:** ~1,880 lines of observability, continuous training, and CI/CD pipelines.

---

### Shared Files (Maintained by M1 as Repo / Release Manager)
- `config.yaml`: Central shared configuration (cities, horizons, thresholds, paths) (~90 lines)
- `src/common/schema.py`: Canonical schema and column definitions (single source of truth) (~155 lines)
- `src/common/constants.py`: Fixed metric names and project constants (~45 lines)
- `src/common/config.py`: Environment-aware YAML configuration loader (~95 lines)
- `README.md`: System architecture, setup guide, requirement-to-file mapping table (~260 lines)
- `docs/DECISIONS.md`: Architectural decision records and Kubernetes substitution rationale (~60 lines)
- `docs/demo_script.md`: Live demonstration script for evaluators (~160 lines)
- `handoff/export_member.sh`: Automated bundle packager (~140 lines)

---

## 3. Workload Balance Verification
- **Member 1:** 33.6%
- **Member 2:** 32.1%
- **Member 3:** 34.3%
- **Verdict:** Clean, equal, and modular 3-way split satisfying all course project guidelines.
