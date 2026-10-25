# Member 2 Git Scenario: Merge Conflict Resolution & Feature Rebase

## Purpose & Scope
This scenario demonstrates:
1. **Deliberate merge conflict**: M1 and M2 both alter `ingest.rate_limit` in `config.yaml` on separate branches (`feat/m1-data-rate` vs `feat/m2-rate-limit`).
2. **Conflict resolution**: Merging the second branch triggers Git conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`). The conflict is resolved and cleanly committed.
3. **Interactive/Linear Rebase**: A feature branch branched from older commits is rebased onto updated `dev` to produce a clean, linear git commit history.

## Step-by-Step Instructions
To run this scenario under your own Git identity in a sandbox clone:

```bash
# From repository root
chmod +x git_scenarios/m2/scenario_m2.sh
./git_scenarios/m2/scenario_m2.sh
```

## Expected Output
Terminal logs will be saved to:
`git_scenarios/evidence/m2_git_scenario.log`

Key milestones in the log:
1. Two divergent branches created with different `rate_limit` settings on the same line.
2. First branch merges cleanly into `dev`.
3. Second branch merge triggers conflict status.
4. Conflict markers inspected and resolved to `rate_limit: 30`.
5. Rebase command runs and transforms commit graph into linear history.
