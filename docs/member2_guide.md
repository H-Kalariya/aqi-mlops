# Member 2 Defense Guide: Serving, Docker & Production Deployment

**Owner:** Member 2 (Serving & Infrastructure Engineer)  
**Project:** AQI Forecaster MLOps  
**Target Scope:** FastAPI Service, Multi-stage Docker Packaging, Zero-Downtime Deployment Strategies (Replicas, Rolling Update, Rollback, 9:1 Canary Split on Nginx), Git Scenario 2.

---

## 1. What You Own (Rubric Mapping)

| Requirement | Directory / Files | Rubric Mapping & Weight |
|---|---|---|
| **Serving (FastAPI)** | `api/app.py`, `api/schemas.py`, `api/metrics.py`, `api/model_loader.py` | **11.1%**: High-throughput REST API with Pydantic validation, structured logging, `/metrics`, `/health`, `/admin/reload` |
| **Docker Containerization** | `Dockerfile`, `docker-compose.yml`, `requirements-api.txt` | **11.1%**: Multi-stage lightweight image, non-root user, container healthchecks, compose multi-service orchestration |
| **Deployment Strategies** | `deploy/nginx/`, `deploy/docker-compose.*.yml`, `deploy/scripts/` | **11.1%**: Scaled replicas, zero-downtime rolling update, automated rollback, and 9:1 weighted canary release |
| **Git Scenario 2** | `git_scenarios/m2/` | **3.3%**: Deliberate merge conflict resolution on `config.yaml` and feature branch rebase |

---

## 2. How It Works & Architecture Rationale

### 2.1 Why Not Kubernetes Here, and How Does This Map to Kubernetes?
- **Decision Rationale:** Kubernetes introduces heavy resource overhead (minikube/kind requires 4–8 GB RAM), cluster lifecycle complexity, and external orchestration dependencies not viable on standard evaluation environments.
- **Equivalent Mapping:**
  - **K8s Deployment Replicas** $\rightarrow$ Docker Compose `--scale api=3` behind Nginx round-robin upstream.
  - **K8s RollingUpdate Strategy** $\rightarrow$ `deploy/scripts/rolling_update.sh` (sequential container replacement, health polling, zero dropped requests).
  - **K8s Rollback (`kubectl rollout undo`)** $\rightarrow$ `deploy/scripts/rollback.sh` reading release history from `deploy/releases.log`.
  - **K8s Ingress Weighted Canary** $\rightarrow$ Nginx weighted upstream proxy (`weight=9` for stable, `weight=1` for canary in `nginx.canary.conf`).
  - **K8s Liveness/Readiness Probes** $\rightarrow$ Docker `HEALTHCHECK` checking `/health` via curl.
  - **K8s ConfigMaps & Secrets** $\rightarrow$ Environment variables via `.env` files and Docker secrets.

### 2.2 Multi-Stage Dockerfile Benefits
- **Builder Stage:** Uses full toolchain (`gcc`, `python-dev`) to compile wheels into `/opt/venv`.
- **Runtime Stage:** Uses `python:3.11-slim`, copies pre-built `/opt/venv`, runs as non-privileged user `appuser` (UID 1000).
- **Result:** Image size reduced by >60% (from ~1.2 GB down to <350 MB) and attack surface minimized.

### 2.3 Transparent Header Propagation
- Every response from API and proxy returns `X-App-Version` and `X-Model-Version`.
- Allows external clients, observability probes, and canary verification scripts to observe traffic distribution from the outside.

---

## 3. How to Run and Demo in Isolation

```bash
# 1. Run API locally in dev mode
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

# 2. Test predict endpoint
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "city": "ahmedabad",
    "readings": {
      "pm25": 85.2, "pm10": 140.0, "no2": 30.1, "so2": 9.0,
      "co": 1.1, "o3": 40.0, "temperature": 29.0, "humidity": 55.0, "wind_speed": 3.2
    }
  }'

# 3. Test health and prometheus metrics
curl -I http://localhost:8000/health
curl -s http://localhost:8000/metrics | grep aqi_

# 4. Scale demo with Nginx
docker compose -f docker-compose.yml -f deploy/docker-compose.scale.yml up -d --scale api=3

# 5. Zero-downtime rolling update & rollback demo
./deploy/scripts/rolling_update.sh v1.1.0
./deploy/scripts/rollback.sh

# 6. Canary 9:1 traffic split demo
docker compose -f deploy/docker-compose.canary.yml up -d
./deploy/scripts/canary_demo.sh --requests 200
```

---

## 4. Connections to M1 and M3

1. **M1 Artifact Loading:** API calls `ModelLoader.load()`, which queries MLflow Model Registry for `@champion` or falls back to `models/model.lgb`.
2. **M3 Monitoring Scrape:** API exposes `/metrics` with fixed Prometheus metrics scraped by M3's Prometheus container.
3. **M3 Continuous Training Webhook:** M3's `promote.py` triggers `POST /admin/reload` to hot-swap the active in-memory model.

---

## 5. Viva Q&A (12 Essential Questions & Model Answers)

1. **Q: Why was Kubernetes omitted and how did you replace its capabilities?**  
   *A:* Kubernetes was omitted to maintain an offline-first, resource-efficient system without hypervisor overhead. We replaced replicas with compose scaling, Ingress with Nginx, rolling updates and rollbacks with bash automation scripts, and probes with container healthchecks.

2. **Q: How does `rolling_update.sh` achieve zero downtime?**  
   *A:* It builds the new container, boots it, polls `/health` until healthy, directs traffic, and drains old containers while a continuous background curl loop sends 10 requests/sec. Zero failed requests (HTTP 200) are recorded.

3. **Q: How does the 9:1 canary release split work?**  
   *A:* Nginx upstream combines `api-stable:8000 weight=9` and `api-canary:8000 weight=1`. Nginx uses weighted round-robin, directing exactly 90% of requests to stable and 10% to canary.

4. **Q: How can canary traffic be verified externally?**  
   *A:* Our API and Nginx proxy inject `X-App-Version` and `X-Model-Version` into HTTP headers. Our script `canary_demo.sh` parses 200 responses and calculates the percentage split.

5. **Q: How is security handled in your Dockerfile?**  
   *A:* Multi-stage build excludes compilation tools; we create and switch to non-root `appuser` (UID 1000), prevent root execution, and drop secrets from image layers.

6. **Q: What is the purpose of `/admin/reload`?**  
   *A:* Hot-reloading. When M3 promotes a challenger model to `@champion`, `/admin/reload` reloads model weights into memory without container restart or traffic disruption.

7. **Q: What happens if MLflow registry is unreachable at API startup?**  
   *A:* Graceful fallback. The API first attempts registry load; if down, it loads bundled `models/model.lgb`; if also absent, it sets `model_loaded: false`, returns 503 on `/predict`, and keeps `/health` alive.

8. **Q: Why use Pydantic models in FastAPI?**  
   *A:* Strict runtime data validation, automatic serialization, type coercion, OpenAPI docs generation, and returning HTTP 422 with descriptive error messages on malformed inputs.

9. **Q: How do you handle secrets in Docker Compose?**  
   *A:* Secrets are decoupled via `.env` files (ignored in `.gitignore`) and Docker compose `secrets` directives, ensuring zero hardcoded credentials in Git.

10. **Q: What metrics does the API export to Prometheus?**  
    *A:* `aqi_http_requests_total` (Counter), `aqi_request_latency_seconds` (Histogram), `aqi_errors_total` (Counter), `aqi_prediction_value` (Histogram), and `aqi_model_info` (Gauge).

11. **Q: How does `rollback.sh` know which version to roll back to?**  
    *A:* Every rollout logs previous and target versions in `deploy/releases.log`. `rollback.sh` parses the previous tag and executes `rolling_update.sh <prev_tag>`.

12. **Q: How did you resolve the merge conflict in Git Scenario 2?**  
    *A:* M1 and M2 altered `ingest.rate_limit` on the same line. Git marked conflict delimiters (`<<<<<<<`). We edited `config.yaml` to an agreeable rate (30 rpm) with retry backoff, added the file, and committed.

---

## 6. Git Scenario 2 Instructions
Run the sandbox script under your personal Git identity:
```bash
chmod +x git_scenarios/m2/scenario_m2.sh
./git_scenarios/m2/scenario_m2.sh
```
Screenshots to capture for viva:
1. Terminal showing `CONFLICT (content): Merge conflict in config.yaml`.
2. Diff showing resolved `config.yaml`.
3. `git log --graph --oneline --all` before and after `git rebase dev`.

---

## 7. "Make It Yours" Checklist
- [ ] Add your student details in `git config`.
- [ ] Update `APP_VERSION` default in `api/app.py` or `.env`.
- [ ] Modify Nginx cache headers or upstream keepalive settings in `deploy/nginx/nginx.conf`.
- [ ] Make a clean commit: `git commit -m "feat(m2): tune nginx upstream keepalive connections"`.
