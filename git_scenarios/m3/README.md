# Member 3 Git Scenario: Production Hotfix Cherry-Pick & Release Tagging

## Purpose & Scope
This scenario demonstrates:
1. **Production Hotfix Workflow**: An emergency hotfix is applied directly to the production branch (`main`).
2. **Cherry-Pick Synchronization**: Using `git cherry-pick <commit-sha>`, the critical hotfix is ported into the active development branch (`dev`) without dragging incomplete development code into production or forcing premature branch merges.
3. **Semantic Version Tagging**: Creation of annotated Git tags (`v1.0` and `v1.1`) marking major operational milestones (initial release and drift-retrained promotion).

## Step-by-Step Instructions
To run this scenario under your own Git identity in a sandbox repository:

```bash
# From repository root
chmod +x git_scenarios/m3/scenario_m3.sh
./git_scenarios/m3/scenario_m3.sh
```

## Expected Output
Terminal logs will be saved automatically to:
`git_scenarios/evidence/m3_git_scenario.log`

Key milestones in the log:
1. Tag `v1.0` created on `main`.
2. `dev` branch diverges with new features.
3. Emergency fix committed to `main`.
4. `git cherry-pick` applies hotfix patch onto `dev`.
5. Release `v1.1` merged and tagged with descriptive release message.
