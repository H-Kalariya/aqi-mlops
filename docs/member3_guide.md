# Member 3 Defense Guide: Monitoring, CI/CD & Continuous Training

**Owner:** Member 3 (MLOps, CI/CD & Observability Engineer)  
**Project:** AQI Forecaster MLOps  
**Target Scope:** Prometheus & Alertmanager & Grafana Monitoring, GitHub Actions CI/CD (Workflows for CI, CD, Drift Check, Retraining), Evidently Drift Detection, Closed-Loop Model Promotion, Git Scenario 3.

---

## 1. What You Own (Rubric Mapping)

| Requirement | Directory / Files | Rubric Mapping & Weight |
|---|---|---|
| **Monitoring Stack** | `monitoring/prometheus.yml`, `monitoring/alert_rules.yml`, `monitoring/alertmanager.yml`, `monitoring/grafana/` | **11.1%**: Full observability: Prometheus scraping, custom alerting rules, Alertmanager routing, provisioned Grafana dashboards |
| **CI/CD Automation** | `.github/workflows/ci.yml`, `.github/workflows/cd.yml`, `scripts/deploy_local.sh` | **11.1%**: Automated quality gates (lint, tests, synthetic train, docker build), container registry publishing (GHCR), deployment triggers |
| **Continuous Training** | `src/drift/`, `.github/workflows/drift-check.yml`, `.github/workflows/retrain.yml`, `scripts/run_full_loop.sh` | **11.1%**: Automated closed loop: drift detection (Evidently) $\rightarrow$ retrain trigger $\rightarrow$ champion vs challenger comparison $\rightarrow$ conditional promotion & reload |
| **Git Scenario 3** | `git_scenarios/m3/` | **3.3%**: Emergency production hotfix on `main`, `git cherry-pick` into `dev`, and annotated semantic release tags (`v1.0`, `v1.1`) |

---

## 2. How It Works & Architecture Rationale

### 2.1 The Closed Continuous Training Loop
```
[ Incoming Data / Drift ]
           │
           ▼
[ Evidently Drift Check ] ──(No drift)──► Exit Cleanly
           │ (Drift Detected > 30% features)
           ▼
[ Automated Retraining ] (Triggers M1 pipeline on updated data)
           │
           ▼
[ Model Evaluation ] ──► Computes challenger MAE & RMSE
           │
           ▼
[ Promotion Engine (promote.py) ]
           ├── challenger_mae < champion_mae ──► Reassign @champion alias ──► POST /admin/reload
           └── challenger_mae >= champion_mae ──► Retain current champion (Audit log recorded)
```

### 2.2 Why Evidently for Drift Monitoring?
- Evaluates statistical data drift across multidimensional features (PM2.5, PM10, NOx, weather).
- Distinguishes sensor noise from systematic distribution shifts (e.g. seasonal winter smog or Diwali fireworks).
- Generates both human-interpretable HTML dashboards (`reports/drift_report.html`) and structured machine JSON (`reports/drift_metrics.json`).

### 2.3 Prometheus & Grafana Observability
- Prometheus scrapes API metrics every 5s using compose DNS.
- Custom alerting rules detect operational anomalies:
  - `APIDown`: Instance unreachable for > 1 min.
  - `HighErrorRate`: HTTP 5xx errors > 5% over 5 mins.
  - `HighLatencyP95`: P95 response latency > 1 sec.
  - `PredictionDistributionShift`: Predicted AQI median shifts > 250 over 15 mins.
- Grafana dashboard provisioned automatically from code without manual UI setup.

---

## 3. How to Run and Demo in Isolation

```bash
# 1. Run data drift detection
python -m src.drift.drift_check

# 2. Inject synthetic data drift (simulate severe Diwali smog)
python -m src.drift.inject_drift --factor 2.5 --days 7

# 3. Re-run drift check on drifted data (verify drift detected)
python -m src.drift.drift_check --current data/processed/drifted_data.csv

# 4. Compare and promote challenger
python -m src.drift.promote

# 5. Run the complete closed loop in one single command:
./scripts/run_full_loop.sh --factor 2.5 --fast

# 6. View generated reports
cat reports/drift_metrics.json
cat reports/promotion_decision.json
```

---

## 4. Connections to M1 and M2

1. **M1 Training Pipeline:** When drift is detected, M3 triggers `src.train.run` and `src.evaluate.run` from M1.
2. **M1 Metric Comparison:** M3 compares challenger `metrics.json` against MLflow champion MAE.
3. **M2 API Reload:** If challenger wins, `promote.py` updates the registry and sends HTTP POST to M2's API `/admin/reload`.
4. **M2 Observability:** Prometheus scrapes M2's `/metrics` endpoint to populate Grafana dashboards and fire Alertmanager rules.

---

## 5. Viva Q&A (12 Essential Questions & Model Answers)

1. **Q: How does the system detect that a deployed model is degrading?**  
   *A:* Through dual observability: data drift monitoring with Evidently comparing reference training data against inference data, and Prometheus tracking prediction distribution histograms and latency.

2. **Q: Why does `drift_check.py` always exit with return code 0?**  
   *A:* Data drift is a business operational condition, not an unhandled software crash. Crashing with code 1 would fail CI/cron steps prematurely. The decision is serialized to `drift_metrics.json` for orchestration logic to consume.

3. **Q: What criteria determines whether a retrained model is promoted?**  
   *A:* Strict performance improvement: `challenger_mae < champion_mae`. If the challenger does not improve upon the champion, the champion remains active and the decision is audited in `reports/promotion_decision.json`.

4. **Q: How does zero-downtime model update happen upon promotion?**  
   *A:* M3's `promote.py` updates the `@champion` alias in the MLflow registry and makes a lightweight HTTP POST to `/admin/reload`. The API hot-swaps the model object in memory without restarting containers.

5. **Q: What is the difference between CI and CD in your GitHub Actions?**  
   *A:* CI runs on every Pull Request (linting, pytest, pipeline validation, docker build check). CD runs only on merges to `main` (trains model, packages container, pushes image to GHCR, and executes rolling update).

6. **Q: What happens if Prometheus detects `APIDown` or `HighErrorRate`?**  
   *A:* Alerts fire based on expressions in `alert_rules.yml`. Prometheus pushes alert payloads to Alertmanager, which groups them, deduplicates, and dispatches notifications via configured webhooks.

7. **Q: What statistical test does the drift detection engine use?**  
   *A:* Two-sample Kolmogorov-Smirnov (KS) test for continuous variables and Wasserstein distance / chi-square for categorical distributions with a significance threshold $p < 0.05$.

8. **Q: How do you prevent endless retraining loops on noisy data?**  
   *A:* `config.yaml` enforces both a share-of-drifted-features threshold (e.g. $\ge 30\%$) and minimum dataset sample size before triggering retraining.

9. **Q: How are Grafana dashboards version controlled?**  
   *A:* Via Grafana provisioning YAML (`datasources/datasource.yml` and `dashboards/dashboard.yml`) and JSON dashboard definitions (`aqi_dashboard.json`) mounted as Docker volumes.

10. **Q: Why use `workflow_dispatch` in GitHub Actions?**  
    *A:* It enables event-driven programmatic triggering of `retrain.yml` by the daily cron drift check or by authorized operators through the GitHub CLI/API.

11. **Q: What is the benefit of cherry-picking in Git Scenario 3?**  
    *A:* `git cherry-pick` extracts an urgent bug fix committed on `main` and applies it cleanly to `dev` without merging unreleased development features into production or vice-versa.

12. **Q: How do annotated tags (`v1.0`, `v1.1`) support MLOps?**  
    *A:* Annotated tags store tagger identity, date, and release messages directly in Git objects, tying specific Git commits to container releases, DVC data versions, and model registry artifacts.

---

## 6. Git Scenario 3 Instructions
Run the sandbox script under your personal Git identity:
```bash
chmod +x git_scenarios/m3/scenario_m3.sh
./git_scenarios/m3/scenario_m3.sh
```
Screenshots to capture for viva:
1. Terminal showing initial tag `v1.0` on `main`.
2. Terminal showing hotfix commit on `main`.
3. `git cherry-pick` applying the hotfix onto `dev`.
4. `git tag -l -n2` showing annotated tags `v1.0` and `v1.1`.

---

## 7. "Make It Yours" Checklist
- [ ] Add your student name and email to `git config`.
- [ ] Modify alerting threshold in `monitoring/alert_rules.yml` (e.g. latency threshold or error rate).
- [ ] Add an extra visualization panel in `monitoring/grafana/dashboards/aqi_dashboard.json`.
- [ ] Make a clean commit: `git commit -m "feat(m3): tune alert thresholds for high latency tolerance"`.
