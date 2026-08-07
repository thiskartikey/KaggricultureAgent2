# Workspace Cleanup Guidelines

To maintain a clean and lightweight repository, agents must periodically remove temporary development artifacts and logs.

## Forbidden/Junk Files

Never commit or leave the following files in the repository:
1. **Screen Recordings**: `.webm` screencasts.
2. **Log Files**: Standard error/output dumps (`stderr*.log`, `stdout*.log`, `debug.log`, `train.log`).
3. **Temporary Scripts**: One-off debugging, patching, or testing scripts (`debug_*.py`, `fix*.py`, `patch_*.py`, `test_monitor*.py`).
4. **Intermediate Models/Checkpoints**: Only the final `rl_weights.npz` and `rl_final_model.zip` should remain. Delete `rl_checkpoints/` and `rl_logs/` after training runs.

## Standard Cleanup Command

Run this command to clean up the repository workspace:
```bash
rm -rf Screencast_*.webm stderr*.log stdout*.log filtered*.log train.log tuning_run*.log log.txt score_log.txt debug.log debug2.log sim_output.txt money_trace.txt money_trace.py debug_*.py fix*.py patch_*.py test_monitor*.py test_portfolio*.py test_picks.py test_load.py test_match.py test_error.py test_eval.py test_empty_structs.py test_build.py test_assignment.py run_test.py v1_backup.py v2.py v2b.py v3.py v3_good.py v4_rolesplit_REJECTED.py revancedmain.py v2 tuning rl_checkpoints rl_best rl_logs && find downloads/ -mindepth 1 -maxdepth 1 ! -name 'protected' -exec rm -rf {} +
```

> [!CAUTION]
> Always verify that `downloads/protected/` is untouched and preserved.

> [!WARNING]
> **Do not run the command above verbatim.** Its final clause
> (`find downloads/ -mindepth 1 -maxdepth 1 ! -name 'protected' -exec rm -rf {} +`)
> deletes `downloads/training/` — 73 top-player replay JSONs, ~2.2 GB, which are
> the source of the strategy blueprint in `CHECKPOINT_RESUME.md` and are not
> easily re-downloaded. Drop that clause, or scope it to the specific junk you
> actually want gone. The `rm -rf` list of `debug_*.py` / `fix*.py` /
> `patch_*.py` / `test_monitor*.py` files is safe on its own.
