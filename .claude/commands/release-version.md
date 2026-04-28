---
allowed-tools: Bash(git *), Edit, Write, Read
---

## Step 1 — Find Most Recent Tag
Run:
```
git tag --sort=-v:refname | head -1
```

If no tags exist, use the first commit as the baseline:
```
git rev-list --max-parents=0 HEAD
```

## Step 2 — Get the Diff
Run:
```
git diff <most-recent-tag>..HEAD --stat
```

Then get the full log of commits since that tag:
```
git log <most-recent-tag>..HEAD --oneline
```

## Step 3 — Decide Version Bump
Based on the diff and commit log, decide whether this is a **minor** or **patch** bump:
- **minor** — new features, new public APIs, new commands, meaningful new behaviour
- **patch** — bug fixes, refactors, documentation updates, small tweaks

Do NOT bump major — that requires explicit human instruction.

## Step 4 — Find and Update the Version
Search the repo for where the version is defined. Common locations:
- `pyproject.toml` → `version = "x.y.z"`
- `setup.py` → `version="x.y.z"`
- `src/__init__.py` or similar → `__version__ = "x.y.z"`
- `package.json` → `"version": "x.y.z"`

Find it, bump it according to Step 3, and update the file.

## Step 5 — Update CHANGELOG.md
- If `CHANGELOG.md` does not exist, create it
- Add a new entry at the top using the new version number and today's date
- Use the format already present in the file if it exists, otherwise use this structure:
```
## [x.y.z] - yyyy-mm-dd

### Added
- ...

### Changed
- ...

### Fixed
- ...
```

- Base the entry strictly on what you see in the diff and commit log — do not invent or assume anything
- Do not modify any existing entries below the new one

## Step 6 — Commit and Tag
```
git add <version-file> CHANGELOG.md
git commit -m "chore: bump version to x.y.z"
git tag x.y.z
git push origin <current-branch>
git push origin x.y.z
```

## Step 7 — Report Token Usage
Run:
```
/cost
```
Report the token usage and cost for this session so far.