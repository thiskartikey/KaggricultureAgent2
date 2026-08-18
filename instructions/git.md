# Git & GitHub

This repo is on branch `phase2-improvements`. Remote `origin` is already configured.

```bash
git remote -v
git log --oneline -5
```

## Committing

Stage only meaningful code and docs:

```bash
git add policy.py src/ tests/ docs/ instructions/ versions/ experiments/ CHECKPOINT_RESUME.md
git status --short          # review before committing
git diff --cached | grep -iE "api[_-]?key|secret|password|token"   # sanity check
git commit -m "[KaggriRatchet] EXP-YYYYMMDD-NN: description"
```

> [!CAUTION]
> **Never `git add -A` or `git add .`** — `replays/` contains GB-scale replay JSONs.
> Stage files explicitly by name or directory.

## What's gitignored

| Path | Reason |
|---|---|
| `replays/` | GB-scale replay JSONs |
| `data/` | Derived CSV/JSON artifacts (regenerate with parser) |
| `venv/` | Local virtualenv |
| `*.tar.gz`, `*.npz` | Build artifacts |
| `__pycache__/`, `.pytest_cache/` | Python caches |

## Pushing

```bash
git push
```

## Champion archive convention

Every promoted experiment is archived as `versions/EXP-YYYYMMDD-NN_policy.py`.
The current champion is `versions/EXP-20260815-69_policy.py`.
