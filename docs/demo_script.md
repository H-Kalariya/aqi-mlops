# AQI Forecaster MLOps: Complete Live Demo Script

This script provides the exact sequence of commands and expected terminal outputs for demonstrating the complete end-to-end system to evaluators.

---

## Demo Flow Overview
```
[1. Verification & Tests] ➔ [2. Data & Model Pipeline] ➔ [3. API & Serving] ➔
[4. Deployment Strategies] ➔ [5. Observability & Dashboard] ➔ [6. Continuous Training Loop]
```

---

## Step 1: Quality Gates & Unit Tests
Run the automated test suite covering all 3 members (M1, M2, M3):

```bash
pytest -v tests/
```
**Expected Output:**
```
tests/m1/test_pipeline.py::test_synthetic_data_generation PASSED
tests/m1/test_pipeline.py::test_schema_validation_passes PASSED
tests/m1/test_pipeline.py::test_schema_validation_fails_on_corrupt_data PASSED
tests/m1/test_pipeline.py::test_no_feature_leakage_and_time_split PASSED
tests/m2/test_api.py::test_health_endpoint PASSED
tests/m2/test_api.py::test_metrics_endpoint PASSED
tests/m2/test_api.py::test_predict_endpoint_success PASSED
tests/m2/test_api.py::test_predict_bad_input_validation PASSED
tests/m3/test_continuous_training.py::test_drift_detected_on_shifted_data PASSED
tests/m3/test_continuous_training.py::test_drift_not_detected_on_identical_data PASSED
tests/m3/test_continuous_training.py::test_promotion_promotes_when_challenger_is_better PASSED
tests/m3/test_continuous_training.py::test_promotion_rejects_when_challenger_is_worse PASSED

======================= 12 passed in ~6.5s =======================
```

---

## Step 2: Member 1 Data & Model Pipeline (DVC & MLflow)
Execute the complete data pipeline from synthetic generation to model evaluation:

```bash
# Ingest data
python -m src.ingest.run --source synthetic --days 90

# Schema validation
python -m src.validate.run

# Feature engineering
python -m src.features.run

# Train model & log to MLflow
python -m src.train.run --fast

# Evaluate model
python -m src.evaluate.run
```
**Expected Output:**
- `data/raw/aqi_raw.csv` and `data/processed/features.csv` generated.
- `metrics.json` written with MAE, RMSE, and model version.
- Model registered as `@champion` in MLflow.

---

## Step 3: Member 2 Serving & API Verification
Launch the FastAPI service locally or verify health & prediction:

```bash
# In terminal 1 (start API):
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000

# In terminal 2: Health probe (observe headers)
curl -i http://localhost:8000/health
```
**Expected Output:**
```http
HTTP/1.1 200 OK
content-type: application/json
x-app-version: dev
x-model-version: 1

{"status":"ok","model_loaded":true,"model_version":"1","app_version":"dev"}
```

Send inference request:
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "city": "ahmedabad",
    "readings": {
      "pm25": 85.2, "pm10": 140.0, "no2": 30.1, "so2": 9.0,
      "co": 1.1, "o3": 40.0, "temperature": 29.0, "humidity": 55.0, "wind_speed": 3.2
    }
  }'
```
**Expected Output:**
```json
{
  "city": "ahmedabad",
  "model_version": "1",
  "model_alias": "champion",
  "forecast": [
    {"horizon_h": 1, "aqi": 128.4},
    ...
    {"horizon_h": 24, "aqi": 142.1}
  ]
}
```

---

## Step 4: Member 2 Zero-Downtime Deployment & Canary Demo
Demonstrate Nginx load balancing, rolling updates, rollbacks, and canary traffic split:

```bash
# 1. Zero-downtime rolling update (tests background continuous traffic)
chmod +x deploy/scripts/*.sh
./deploy/scripts/rolling_update.sh v1.1.0 --scale 3

# 2. View release log
./deploy/scripts/release_log.sh list

# 3. Rollback to previous version
./deploy/scripts/rollback.sh

# 4. Demonstrate 9:1 Canary Traffic Split
./deploy/scripts/canary_demo.sh --requests 200
```
**Expected Output:**
```
=== Observed Traffic Split (200 requests) ===
X-APP-VERSION        COUNT      PERCENTAGE  
---------------------------------------------
1.0.0 (Stable)       182        91.0%
1.1.0 (Canary)       18         9.0%
---------------------------------------------
Status: PASS — Canary traffic successfully isolated to ~10%.
```

---

## Step 5: Member 3 Monitoring & Observability
Scrape metrics and view Prometheus & Grafana stack:

```bash
# Check Prometheus metrics exported by API
curl -s http://localhost:8000/metrics | grep aqi_

# Start full monitoring stack (Prometheus, Alertmanager, Grafana):
docker compose up -d prometheus grafana alertmanager
```
- Open Grafana at `http://localhost:3000` (credentials: `admin` / `admin`).
- Navigate to **Dashboards > AQI Operations > AQI MLOps Production Dashboard**.
- Observe live panels:
  - System & Model Info
  - HTTP Request Rate (req/sec)
  - P95 Latency (seconds)
  - API Error Rate
  - Prediction Distribution Histogram

---

## Step 6: Member 3 Continuous Training Closed-Loop Demo
Demonstrate the automated feedback loop from distribution shift to promotion:

```bash
chmod +x scripts/*.sh
./scripts/run_full_loop.sh --factor 2.5 --fast
```
**Expected Output:**
```
======================================================================
 AQI MLOps: Continuous Training Closed-Loop Demonstration
 Workflow: Detect Drift -> Retrain -> Compare -> Promote -> API Reload
======================================================================

[Step 1/6] Injecting synthetic data drift into recent data...
[inject_drift] Injecting drift for 504 records (factor=2.5)

[Step 2/6] Running data drift analysis...
[drift_check] Analysis complete: drift_detected=True, share_drifted=0.40, drifted_features=['pm25', 'pm10', 'aqi']
[drift_check] Metrics saved to: reports/drift_metrics.json

[Step 3/6] Ingesting updated data and regenerating feature matrix...
[Step 4/6] Retraining LightGBM challenger model...
[Step 5/6] Evaluating challenger model on holdout set...
[Step 6/6] Executing champion vs. challenger promotion decision...
[promote] Verdict: PROMOTED
[promote] Reason: Challenger MAE (14.2) is strictly better than Champion MAE (21.5).
[promote] Calling API reload endpoint: http://localhost:8000/admin/reload

======================================================================
 Closed-Loop Demonstration Complete!
======================================================================
```
