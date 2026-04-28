---
allowed-tools: Bash(docker compose *), Bash(git *), Edit(!tests/**), Write(!tests/**), Read
---

The tests have been reviewed and approved. Complete the implementation.

## Step 1 — Write Implementation
Implement the feature. Infer code style and conventions from the existing codebase.

STRICT RULE: Do NOT modify any files under `tests/`. Do not add, edit, or delete any test files under any circumstances.

## Step 2 — Update Docs
Update documentation under `docs/` to reflect the new feature.

## Step 3 — Test Loop
Run and repeat until exit code is 0. Fix only implementation files — never test files:
```
docker compose -f tests/docker-compose.yaml --project-directory tests up --build --abort-on-container-exit --exit-code-from test 2>&1
```

## Step 4 — Reformat
```
docker compose -f reformat/docker-compose.yaml up --build --abort-on-container-exit --exit-code-from reformat 2>&1
```

## Step 5 — Lint Loop
Run and repeat until exit code is 0. Fix only implementation files — never test files:
```
docker compose -f lint/docker-compose.yaml up --build --abort-on-container-exit --exit-code-from linter 2>&1
```

## Step 6 — Validate Docs Loop
Run and repeat until exit code is 0:
```
docker compose -f docs-validate/docker-compose.yaml --project-directory docs-validate up --build --abort-on-container-exit --exit-code-from docs-validator 2>&1
```

## Step 7 — Update CHANGELOG
1. Run `git tag --sort=-v:refname | head -5` to find the most recent tag
2. If `CHANGELOG.md` does not exist, create it with a standard header
3. Add a new entry at the top for the current change, using the next logical version after the most recent tag
4. Summarize what was implemented, what tests were added, and what docs were updated

## Step 8 — Commit
1. Run `git status` to see all modified files
2. Stage and commit only the files that were changed by this implementation (excluding test files if they were somehow touched — they should not have been)
3. Use a descriptive commit message:
```
git add <file1> <file2> ...
git commit -m "<reasonable commit message>"
git push -u origin <current-branch>
```

## Step 9 — Report Token Usage
Run:
```
/cost
```
Report the token usage and cost for this session so far.
