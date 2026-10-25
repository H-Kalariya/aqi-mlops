# Member 1 Defense Guide: Data Versioning, Pipeline & Experiment Tracking

**Owner:** Member 1 (Pipeline Engineer & Release Manager)  
**Project:** AQI Forecaster MLOps  
**Target Scope:** Data Versioning (DVC), Automated Pipeline (Ingest → Validate → Features → Train → Evaluate), Experiment Tracking & Model Registry (MLflow Champion/Challenger), Git Scenario 1.

---

## 1. What You Own (Rubric Mapping)

| Requirement | Directory / Files | Rubric Mapping & Weight |
|---|---|---|
| **Data Versioning** | `dvc.yaml`, `params.yaml`, `.dvcignore`, `data/raw/`, `data/processed/`, `data/snapshot/` | **11.1%**: Verifiable lineage and data tracking without committing large CSVs into Git |
| **Pipeline Architecture** | `src/ingest/`, `src/validate/`, `src/features/`, `src/train/`, `src/evaluate/` | **11.1%**: End-to-end reproducible pipeline stages from synthetic/live ingestion to evaluation |
| **Experiment Tracking** | `src/train/run.py`, `src/evaluate/run.py`, MLflow tracking with `champion`/`challenger` aliases | **11.1%**: Model parameters, MAE/RMSE metrics, artifacts, and version registration |
| **Git Scenario 1** | `.pre-commit-config.yaml`, `git_scenarios/m1/` | **3.3%**: Pre-commit gating (Black/Ruff) and safe rollback via `git revert` |

---

## 2. How It Works & Architecture Rationale

### 2.1 Why LightGBM?
- LightGBM handles tabular features with high efficiency, native categorical feature support (`city`), and zero requirement for deep learning acceleration.
- Single global model predicts 24 horizons simultaneously by treating `horizon_h` as a feature and `aqi_target` as the value at `t + horizon_h`.
- Stacked horizon architecture avoids training 24 separate models, keeping training sub-minute on CPU.

### 2.2 Why Model Registry Aliases (Champion / Challenger) over Stages?
- MLflow deprecated Stage transitions (`Staging`, `Production`, `Archived`) in favor of **Model Aliases**.
- Aliases allow mutable pointers (`@champion`, `@challenger`) to immutable version numbers (`v1`, `v2`).
- Seamless canary deployments and API reload: the API always points to `@champion` without code changes.

### 2.3 Data Lineage & DVC Pipeline
- `dvc.yaml` defines explicit stages: `ingest` → `validate` → `features` → `train` → `evaluate`.
- Every model run logs the Git commit SHA and DVC data hash tag (`data_version`) to MLflow tags, guaranteeing 100% auditability back to exact training data.

---

## 3. How to Run and Demo in Isolation

```bash
# 1. Run full DVC pipeline
dvc repro

# 2. Or run Python steps manually:
# Step A: Ingest synthetic data (30 days)
python -m src.ingest.run --source synthetic --days 30

# Step B: Validate with Pandera schema
python -m src.validate.run

# Step C: Feature engineering (lags, rolling, calendar, horizons)
python -m src.features.run

# Step D: Train LightGBM model and log to MLflow
python -m src.train.run --fast

# Step E: Evaluate model and output metrics.json
python -m src.evaluate.run

# 3. Inspect MLflow experiments
mlflow ui --port 5000
```

---

## 4. Connections to M2 and M3

1. **Fixed Feature Schema (`src/common/schema.py`)**: Defines exact columns (`pm25`, `pm10`, `no2`, `so2`, `co`, `o3`, `temperature`, `humidity`, `wind_speed`, `aqi`, lags, rolling stats). M2's API validates against this schema.
2. **Model Registry Output**: M1 logs and registers `aqi-forecaster` with alias `@champion`. M2's API loader retrieves this exact alias at startup.
3. **Evaluation Metrics Contract (`metrics.json`)**: M1 produces `metrics.json` (`{"mae": ..., "rmse": ..., "model_version": ...}`) which M3's `promote.py` parses to decide promotion.

---

## 5. Viva Q&A (12 Essential Questions & Model Answers)

1. **Q: Why is data versioning necessary in ML systems when code is already in Git?**  
   *A:* Datasets are large, binary or semi-structured, and change independently of code. Committing large CSVs balloons Git history. DVC stores metadata pointers in Git while offloading raw payloads to remote storage.

2. **Q: How does DVC track changes between runs?**  
   *A:* DVC computes md5 content hashes of declared dependencies (`deps`) and outputs (`outs`) in `dvc.yaml`. If neither code nor data hashes changed, `dvc repro` skips the stage.

3. **Q: How do you prevent data leakage in feature engineering?**  
   *A:* We use a strict time-based split without shuffling (`time_based_split`). Lag and rolling statistics are computed strictly on past timestamps grouped by city before the cutoff.

4. **Q: Why use synthetic data generation instead of only relying on live APIs?**  
   *A:* Offline-first reliability. Live APIs (e.g. data.gov.in) suffer from rate limits, network outages, and missing API keys. Synthetic generation produces realistic diurnal and seasonal cycles with controlled seeds.

5. **Q: How does your Pandera schema catch data corruption?**  
   *A:* It enforces physical boundaries (e.g. PM2.5 within 0–1000 µg/m³, AQI 0–500), non-null constraints on primary keys, and timestamp monotonicity. Failures exit non-zero and output an issue report.

6. **Q: Why LightGBM over deep neural networks (LSTM/Transformer) for this AQI problem?**  
   *A:* Tabular meteorological and pollutant data with lag features is dominated by gradient boosted trees. LightGBM trains in seconds on CPU, handles missing values, and allows straightforward SHAP/feature importance analysis.

7. **Q: How does the model forecast 24 hours into the future?**  
   *A:* We stack training rows across horizons 1..24 with `horizon_h` as an input feature and target = AQI at `t + horizon_h`. Inference calls the model for all 24 horizons simultaneously.

8. **Q: What is the difference between MLflow stages and aliases?**  
   *A:* Stages (`Production`, `Staging`) are hardcoded, deprecated, and single-tenant. Aliases (`@champion`, `@challenger`) are dynamic labels pointing directly to specific versions, enabling multi-tenant routing and canary testing.

9. **Q: How is model reproducibility guaranteed?**  
   *A:* Every MLflow run logs the exact hyperparameter dictionary, random seed (42), Git commit SHA, and DVC data hash.

10. **Q: What happens if validation data contains null pollutant readings?**  
    *A:* Ingestion imputes transient sensor drops via forward-fill within 3 hours. Severe gaps trigger schema validation failure and flag data for re-ingestion.

11. **Q: What metrics are logged and why?**  
    *A:* MAE (Mean Absolute Error) for intuitive AQI-point error interpretation and RMSE (Root Mean Squared Error) to penalize severe outlier prediction spikes.

12. **Q: How did you handle pre-commit hooks and bad commit rollbacks?**  
    *A:* `.pre-commit-config.yaml` runs Black and Ruff before every commit. For bad commits, `git revert` was used instead of `git reset` to preserve immutable audit trails in shared branches.

---

## 6. Git Scenario 1 Instructions
Run the sandbox script under your personal Git identity:
```bash
chmod +x git_scenarios/m1/scenario_m1.sh
./git_scenarios/m1/scenario_m1.sh
```
Screenshots to capture for viva:
1. Terminal showing `black --check` blocking the commit with non-zero exit.
2. Terminal showing successful commit after formatting fix.
3. `git log --graph --oneline` showing the bad commit followed by the `Revert "..."` commit.

---

## 7. "Make It Yours" Checklist
- [ ] Add your personal student ID and name in `git config user.name` and `user.email`.
- [ ] Modify `config.yaml` with an additional pollutant or tune `synthetic_months: 6`.
- [ ] Adjust LightGBM parameters in `params.yaml` (`learning_rate: 0.03`, `num_leaves: 35`).
- [ ] Make a clean commit: `git commit -m "feat(m1): optimize LightGBM tree depth and add personal notes"`.
