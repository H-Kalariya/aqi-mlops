# Owner: Shared (M1 as repo/release manager) — Design Decisions

# DECISIONS.md — Design Decisions Log

## Kubernetes Substitution

**Decision:** Kubernetes is intentionally excluded from this project. Everything that Kubernetes would demonstrate (rolling updates, rollbacks, canary releases, replicas, config/secret separation, health probes) is delivered instead with **Docker Compose + an nginx reverse proxy** and release scripts.

**Rationale:** The project scope focuses on the MLOps pipeline and practices. Docker Compose with nginx provides equivalent demonstrations of deployment strategies without the operational overhead of a K8s cluster (kind/minikube/kubectl/Helm).

**What maps where:**
| K8s Concept | Our Equivalent |
|---|---|
| Deployment replicas | `docker compose --scale api=3` |
| Rolling update | `deploy/scripts/rolling_update.sh` (one-at-a-time with health checks) |
| Rollback | `deploy/scripts/rollback.sh` (reads `releases.log`) |
| Canary release | `nginx.canary.conf` with weight=9:1 upstream |
| ConfigMap | `.env` files + compose env |
| Secrets | `.env` + compose `secrets` (never committed) |
| Health probes | Docker `HEALTHCHECK` + `/health` endpoint |
| HPA | Not applicable (manual scaling via `--scale`) |
| Service discovery | Docker Compose DNS |

## Model Design

**Decision:** ONE global LightGBM regressor with `horizon_h` and `city` as features.

**Rationale:** Simplicity. The grade is for the pipeline, not accuracy. A single model is easier to version, deploy, and monitor. Multi-horizon stacking with `horizon_h` as a feature avoids managing 24 separate models.

## MLflow Aliases vs Stages

**Decision:** Use `champion` and `challenger` aliases instead of the deprecated stage-based workflow.

**Rationale:** MLflow stages (`Staging`, `Production`) are deprecated as of MLflow 2.9. Aliases are the recommended replacement and provide clearer semantics.

## Ingest Source Default

**Decision:** Default to `synthetic` data generation when no API keys are present.

**Rationale:** Offline-first design. The entire project must run with zero network access. Synthetic data includes realistic seasonal patterns (winter smog, Diwali spikes, monsoon dips).

## DVC Remote

**Decision:** Default local directory remote (`../dvc-remote`).

**Rationale:** Works offline without cloud credentials. Google Drive and S3 configs are provided as commented alternatives in the member guide.

## Not Executed Here — How to Verify

The following require runtime infrastructure not available in this build environment:
- `docker compose up` — requires Docker daemon. Verify: `docker compose config` validates the YAML.
- GitHub Actions workflows — require GitHub runners. Verify: YAML syntax and `actionlint`.
- Grafana dashboards — require running Grafana instance. Verify: JSON is valid.
- Rolling update / canary scripts — require Docker daemon. Verify: `bash -n` / `shellcheck`.
