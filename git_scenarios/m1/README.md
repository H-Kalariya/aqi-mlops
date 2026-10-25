# Member 1 Git Scenario: Pre-commit Hooks & Git Revert

## Purpose & Scope
This scenario demonstrates:
1. **Pre-commit quality gate**: A commit is blocked by `black` / `ruff` when code contains lint/style violations, and passes once corrected.
2. **Safe rollbacks via `git revert`**: A faulty commit (bad learning rate) is committed and subsequently reverted using `git revert`, preserving complete history without rewriting Git tree.

## Step-by-Step Instructions
To run this scenario under your own Git identity in a throwaway sandbox:

```bash
# From repository root
chmod +x git_scenarios/m1/scenario_m1.sh
./git_scenarios/m1/scenario_m1.sh
```

## Expected Output
Terminal logs will be captured automatically to:
`git_scenarios/evidence/m1_git_scenario.log`

Key milestones in the log:
1. `black --check` and `ruff check` exiting with non-zero status on bad code.
2. Formatting corrected; commit accepted.
3. Commit with bad model parameter created.
4. `git revert HEAD` creates a new revert commit.
5. `git log --graph --oneline` shows the forward-moving commit graph.
