# Git & GitHub

This repo is pushed to **https://github.com/gytdrop/KaggricultureAgent**, branch
`main`. `origin` is already configured — no need to add it again.

```bash
git remote -v
git log --oneline
```

## Committing

The only files that belong in a commit are code, docs, and small config:
`heuristic.py`, `ml_main.py`, `CHECKPOINT_RESUME.md`, `instructions/`,
`versions/*.py` (historical snapshots of the agent, kept for the record).

> [!CAUTION]
> **Never `git add -A` or `git add .` in this repo.** `downloads/training/`
> alone is ~2.3 GB of replay JSONs (73 files, ~30 MB each) and is not covered
> by any earlier `.gitignore` rule pattern-wise — it is excluded by an
> explicit `downloads/` line. A broad add stages the entire corpus and the
> push will be rejected by GitHub on repository size. Stage files by name:
>
> ```bash
> git add heuristic.py ml_main.py CHECKPOINT_RESUME.md instructions/ versions/
> git status --short          # review before committing
> git diff --cached | grep -iE "api[_-]?key|secret|password|token"   # sanity check
> ```

## What's gitignored and why

| Path | Reason |
|---|---|
| `downloads/` | 2.3 GB of replay JSONs; not needed to run or resume the agent, just to re-derive the strategy blueprint |
| `.agents/` | orchestrator scratch state, not durable |
| `*.tar.gz`, `*.npz`, `*.zip` | build artifacts, regenerate with `build_submission.py` |
| `*.log` | run output |

`downloads/protected/` is small (one tar.gz) and would be fine to track, but
since its parent `downloads/` is ignored wholesale it is excluded too — that
file is not reproducible if lost, so treat "not on GitHub" as a reason to be
extra careful locally (see `instructions/restrictions.md`), not as a gap to fix
by force-adding it.

## Pushing

```bash
git push -u origin main     # first push already done; subsequent ones just `git push`
```

Ownership was verified with `gh repo view gytdrop/KaggricultureAgent --json owner`
before the first push — do that again if working against a different repo.
