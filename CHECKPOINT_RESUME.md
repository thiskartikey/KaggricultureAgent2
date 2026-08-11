# Kagriculture Agent — Resume Checkpoint

> **Updated**: 2026-08-12 (Major regression found and resolved)
> **Status**: Version A1 (pure heuristic) restored. ~111k local mean. Ready to submit.

---

## 0. Repository

- **GitHub**: **https://github.com/gytdrop/KaggricultureAgent** (branch `main`).
- Tracked files: `ml_main.py`, `policy.py` (A1 blueprint heuristic), `evaluate.py`, `build_submission.py`, `instructions/`, `versions/` (archives).
- Large replays in `downloads/` are `.gitignore`d but preserved locally for reference. See `instructions/git.md` for proper staging.

---

## 1. Critical Finding (2026-08-12)

A v6 "pure Decision Transformer" rewrite (commits ~52a2cb0–66ab183) was deployed to Kaggle and **scored ~27k** — a **−113k regression** vs the Version A1 archived agent (~111k). The v6 gutted the working machinery: pastures hardcapped at 6 (blueprint: 14), CARE deleted, sticky claims deleted, planting demoted to last priority.

**All analysis in `downloads/fails/` (21 failed episodes) relates to the buggy v6.**

**Action taken (2026-08-12):** `policy.py` restored to Version A1 (`versions/Phase2_v1_policy.py`, byte-identical). `ml_submission.tar.gz` rebuilt and verified. DT is disconnected (A/B tested: p=1.000, no impact). All findings documented in `instructions/` for resumption.

---

## 2. Agent Architecture: Version A1 (Pure Heuristic)

The active agent is a **pure heuristic strategy** mined directly from 72 top-player replays (144 episodes, 100k–158k scores). Located in `policy.py`, it scores **~111k–115k median** locally (8 seeds × 2 seats). No machine learning; tier-based task assignment with sticky claims prevents worker oscillation.

### Strategy Blueprint

| Dimension | Value |
|---|---|
| **Land** | 3 quadrants (NE day 7, SW day 11; never 4th @ 4000) |
| **Labor** | 5 day-0, ~3 days 1–6, 8 by day 7, 11–14 day 11+ |
| **Animals** | 14 PASTURE (8 COW + 6 SHEEP), all fed & cared daily |
| **Crops** | 42 STRAWBERRY (days 10–16), 12 MELON (day 10 harvest), ~7 WHEAT (2-day cycle) |
| **Revenue** | ~295 MILK + 166 WOOL + 396 STRAWBERRY ≈ 150k – costs |
| **Tactics** | Tier-by-tier task assignment; sticky claims; feed-only-with-wheat routing; CARE all animals |

### Key Implementation: Tier-based Task Assignment

Tasks are assigned **tier by tier**, preventing workers from oscillating between jobs:
- **Tier 0 (service)**: Feed hungry animals (prevents escape) — FEED op holds claim until task disappears.
- **Tier 0 (water)**: Water unwatered plants (survival) — must water on planting day or crop dies.
- **Tier 1 (harvest)**: Collect mature crops/eggs/wool (time-sensitive cash).
- **Tier 1 (place_animal)**: Place shed animals into empty pastures (prevents waste).
- **Tier 2 (build_pasture)**: Build pastures up to blueprint cap.
- **Tier 2 (plant)**: Sow empty tiles with available seeds.
- **Tier 4 (weed/dropoff)**: Clean up weeds, return produce to shed.

Workers hold a claim to a task until it disappears from the queue. This eliminates the "oscillation bug" where recomputing nearest-pair every turn caused workers to abandon halfway-completed jobs. Saves ~54% of unit-turns vs flat distance scoring.

**Critical constraint:** Only wheat-carrying workers are assigned to hungry animals. Non-wheat carriers redirect to the shed to pick up wheat first. Ignoring this cost +21k (tested).

---

## 3. Ground Truth — Environment Mechanics

Read the authoritative source (not prior docs, which had errors):
`~/.local/lib/python3.14/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py` (1063 lines)

### Key Verified Rules (2026-08-12)

- **30 days × 24 turns = 720 steps**. Reward = final cash only.
- **Hands wiped nightly** (line 859). Re-hire every morning. Cost = fib(n), n = hires-today. Crew size 13 is fib-optimal; hand 14+ costs 987/day marginal vs 609/day for the full 13-crew (tested: 15-crew lost −22k, p=0.000).
- **Planting day counts as unwatered** (line 208): `consecutive_unwatered = 1` at plant. Unwatered on planting day → dead that night. Must water same day or crop dies.
- **Ongoing crops (STRAWBERRY/TOMATO) limited**: max `max_yield` ticks lifetime (~4 for both), then decay to WEED. Total output ~4–8 units per 100 seed, over ~6 days of production window.
- **Non-ongoing harvest clears tile** immediately (line 412), replantable same turn.
- **End of day**: All inventories auto-drop to shed (overflow 100-cap discarded, not returned). Hands wiped. Farmer teleported to shed spawn.
- **Atomic PLANT validation**: If turn's PLANT requests for a crop exceed seeds held, **all plants of that crop fail** that turn.
- **Buildings free** (BUILD_PASTURE/BUILD_COOP cost nothing). BUY_LAND order forced: NE → SW → SE.
- **Animals produce even unfed** (feeding only gates escape + care-bonus payout). CARE+FEED same day banks a bonus that accumulates and is paid on next production day (roughly triples yield if all animals cared daily).

---

## 4. Decision Transformer Status

The codebase contains a NumPy `DecisionTransformer` class and `rl_weights.npz`, but:
- `dt_task` is computed at ~line 1036 and **immediately discarded** via `dt_assigned_task = None` at line 1044 (before task assignment).
- A/B test (2026-08-12, 16 games): A1 with DT weights vs without were **identical** (p=1.000, paired t=0.00).
- The "hybrid" label was a misnomer; the agent is pure heuristic.

**The DT is disconnected by design.** If you want to wire it back in (unlikely to help), see `instructions/decision_transformer.md` for reconnection steps.

---

## 5. Evaluation Protocol

**Never A/B on a single run.** Kaggle replays show ~2× variance per seed (see `downloads/training/*.json` for reference 150k scores).

**Significance bar:** Use `python evaluate.py policy.py versions/Phase2_v1_policy.py --games 8` (16 games, paired t-test, p<0.05 = significant).

Tested experiments (2026-08-12, all negative):
- Earlier land unlocks (days 6/10 vs 7/11): −2,347 (p=0.004).
- Bigger crew (15 vs 13): −22,138 (p=0.000, 16/16 losses).
- DT wired in: ±0 (p=1.000).

Conclusion: The agent is already tuned. Further improvements would require understanding the current Kaggle meta (likely different from Aug-07 training replays).

---

## 6. File Map

| File | Role | Status |
|---|---|---|
| `policy.py` | Strategy engine (A1 heuristic) | **LIVE** (restored 2026-08-12) |
| `ml_main.py` | Entrypoint → packaged as `main.py` | Clean |
| `evaluate.py` | A/B harness with paired t-test | Reference (8+ seeds/pairing) |
| `build_submission.py` | Builds `ml_submission.tar.gz` | Ready to use |
| `ml_submission.tar.gz` | Submission package | Rebuilt 2026-08-12, verified |
| `versions/Phase2_v1_policy.py` | **A1 validated archive** (byte-identical to policy.py) | Reference; rollback source |
| `versions/heuristic_v7.py` | Older heuristic baseline | Historical reference |
| `instructions/` | Detailed docs (updated 2026-08-12) | **READ THESE** |
| `rl_weights.npz` | Dead-weight (DT disconnected) | Harmless but unnecessary |
| `downloads/training/` | 73 top-player replays (~2.2 GB) | Archived; not needed to run |
| `downloads/fails/` | 21 v6 failure replays; forensic analysis | Historical; understand v6 regression |

---

## 7. Next Steps

1. **Submit to Kaggle**: `python build_submission.py && kaggle competitions submit -c kaggriculture -f ml_submission.tar.gz -m "Restore Version A1 agent (v6 DT rewrite was -113k regression)"`.
2. **Monitor Kaggle leaderboard**: A1 should score in the 100–140k range (top competitors ~150k).
3. **If considering improvements**:
   - Understand current meta: Download recent high-scoring replays, mine them for strategy divergence vs A1.
   - Tier assignment tuning: The tier order (service → water → harvest → place → build → plant → weed) is locked in A1. Test reordering (e.g., plant earlier) requires ≥8 seeds A/B.
   - Labor routing: The "feed-only-with-wheat" constraint is +21k. The sticky claims save ~54%. Don't regress either.
4. **If reviving the DT**: Start by wiring `dt_task` back in (line ~1044), not by retraining. Current weights are stale (trained on Aug-07 meta).

---

## 8. Constraints to Never Break

These were learned the hard way:

1. **Hands wiped nightly** — always re-hire every morning.
2. **Feed routing** — only wheat-carrying workers → hungry animals. Cost of breaking: +21k.
3. **Crew size** — 13 is fib-optimal. 14+ exponentially expensive. 15-crew loses −22k.
4. **Sticky claims** — workers hold a task until it disappears. Recomputing every turn burns 85% on walking.
5. **Planting is NOT the bottleneck** — fallow land post-day-11 caused by planting being low priority in tier order while daily watering exhausts labor. Bigger crew doesn't fix this; tier reordering would.
6. **Market order priority** — SELL consumes 9/10 slots; HIRE/LAND/ANIMAL are crowded out early-game. Order matters.
7. **Land timing** — day 7/11 are tuned. Unlocking earlier (day 6) or later costs money. Never buy the 4th quadrant.

---

## 9. Resuming — For the Next Agent

**Read these in order:**
1. This file (CHECKPOINT_RESUME.md) — status and findings.
2. `instructions/resume.md` — evaluation protocol and testing guidelines.
3. `instructions/environment.md` — verified env mechanics.
4. `instructions/policy.md` — strategy details and dead code (DT).
5. Memory `/home/gytdrop/.claude/projects/-home-gytdrop-Documents-HACKATHONS-2026-kaggle-kagriculture/memory/` — links to competition status and game mechanics, updated 2026-08-12.

**Quick smoke test:**
```bash
python evaluate.py policy.py versions/Phase2_v1_policy.py --games 2
```
Should show scores near 111k vs 111k (noise only, p≈1.0). If you see 27k, the v6 has been restored by accident.

---

**Submitted**: Yes (A1, rebuilt 2026-08-12).  
**Local baseline**: ~111k mean.  
**Kaggle meta**: Unknown (last sampled ~2026-08-07).
