# Kagriculture Agent — Resume Checkpoint

> **Created**: 2026-08-07
> **Status**: PENDING — Teamwork agent could not launch (quota limit). Resume manually.

---

## What Was Already Done

### 1. Repository Cleanup (COMPLETED ✅)
All junk files were deleted from the repo:
- Screen recordings, logs, debug scripts, temp test files, old backups, intermediate checkpoints.
- `downloads/protected/` was preserved (NEVER touch this).
- See `instructions/cleanup.md` for the full cleanup command.

### 2. Instructions Written (COMPLETED ✅)
9 markdown files were created in `instructions/` to guide AI agents:
- `restrictions.md`, `brain.md`, `resume.md`, `submission.md`, `evaluation.md`, `environment.md`, `heuristics.md`, `reinforcement_learning.md`, `cleanup.md`
- **READ `instructions/restrictions.md` FIRST** before making any changes.

### 3. Agent Improvement (NOT STARTED ❌ — This is what you need to do)
The teamwork agent was supposed to do this but hit a quota wall. Here is the full task:

---

## Task To Complete

### Problem Statement
The current agent (built from `downloads/protected/heuristic_submission.tar.gz`) scores 11k-70k but has critical reasoning gaps:
1. **Not hiring workers when it should**: e.g., has 32+ coins but doesn't buy workers when they're needed.
2. **Not claiming ready products**: Harvested/produced goods sit uncollected, wasting turns and value.
3. **Not learning from top player patterns**: The agent doesn't follow the strategic patterns that top-scoring players use.

### Step-by-Step Instructions

#### Step 1: Backup Current Agent
```bash
cd /home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture
mkdir -p versions
cp heuristic.py versions/heuristic_backup_$(date +%Y%m%d).py
cp main.py versions/main_backup_$(date +%Y%m%d).py
```

#### Step 2: Analyze Top Player Replays
JSON replay files from top players will be placed in `downloads/training/`.
- Parse these JSON files to extract the action sequences of winning players.
- Focus on identifying patterns for:
  - **When do top players hire workers?** (at what coin thresholds, at what day ranges)
  - **When do they claim/harvest products?** (do they do it every turn? prioritize certain crops?)
  - **What is their crop/animal ratio strategy?**
  - **How do they manage their economy?** (buying seeds, selling products, maintaining reserves)

#### Step 3: Update `heuristic.py` with New Patterns
The core logic lives in `heuristic.py` (24KB, ~600 lines). Key areas to fix:

**Fix 1 — Worker Hiring Logic**: 
Find the section that handles hiring. Add logic to aggressively hire workers when:
- Coins > 32 AND current workers < needed workers for the land/animals owned.
- Top players likely hire early and often.

**Fix 2 — Product Claiming/Harvesting**:
Find the harvesting/collecting priority queue. Ensure:
- Ready products are ALWAYS claimed before planting new crops.
- Collecting animal products (eggs, milk, wool) is prioritized when animals are healthy and producing.

**Fix 3 — Apply Extracted Patterns**:
Whatever patterns you extract from Step 2, encode them as rules in the heuristic priority system.

#### Step 4: Verify Changes
```bash
python evaluate.py main.py heuristic.py --games 4
```
- The updated agent should show statistically significant improvement.
- Check that the specific behaviors (worker hiring at >32 coins, product claiming) are triggered.

### Key Files Reference
| File | Purpose |
|------|---------|
| `main.py` | Main agent entrypoint (710 lines, hybrid RL+heuristic) |
| `heuristic.py` | Rule-based fallback engine (600 lines, market pricing + operations) |
| `env_wrapper.py` | Feature vectorization for RL model |
| `rl_inference.py` | Pure-numpy neural net forward pass |
| `rl_weights.npz` | Trained PPO weights |
| `evaluate.py` | A/B evaluation harness with paired t-test |
| `build_submission.py` | Packages submission tar.gz |
| `downloads/training/*.json` | Top player replay JSONs to analyze |
| `downloads/protected/` | ⚠️ NEVER MODIFY OR DELETE |

### Restrictions (CRITICAL)
1. **NEVER delete or modify `downloads/protected/`**
2. **NEVER add print() to submission files** (stdout is used for game communication)
3. **ALWAYS backup before modifying** core files
4. **ALWAYS run `python evaluate.py` after changes** to verify no regressions
5. **Read `instructions/` folder** for full documentation on the architecture
