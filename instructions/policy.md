# Agent Policy — Version A1 (Restored 2026-08-12)

This document outlines the strategy for the agent's core decision policy located in [policy.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/policy.py).

## Current State: Pure Heuristic Blueprint Engine

`policy.py` (Version A1) implements a highly optimized **pure heuristic strategy** mined directly from 72 top-player replays (144 episodes, 100k–158k scores). It achieves a median score of **~111k–115k** locally (8 seeds x 2 seats).

### Strategy Blueprint (from top-player replays):
- **Land:** 3 quadrants only (NE day 7, SW day 11; never the 4th at 4000).
- **Labor:** 5 hands day 0, ~3 days 1–6, 8 by day 7, 11–14 from day 11. Daily re-hire (fib cost).
- **Animals:** 14 PASTURE (8 COW + 6 SHEEP) from day 11+, all fed and cared daily. Generates ~295 MILK + 166 WOOL / episode.
- **Crops:** 42 STRAWBERRY (first yield day 10, 4-tick lifetime), 12 MELON (10 days, one harvest), ~7 WHEAT (2-day cycle filler and feed).
- **Tactics:** Tier-based task assignment (service → water → harvest → place → build → plant → weed); sticky claims to prevent worker oscillation; separate feed-carriers; CARE on all animals daily.

### Key Implementation Details:
- **Sticky task claims:** Each unit holds a claim until the task disappears, preventing workers from oscillating between jobs (saves ~54% of turns vs. flat distance scoring).
- **Feed routing:** Only wheat-carrying workers are assigned to hungry animals; non-wheat carriers redirect to the shed to pick up wheat first.
- **Tier system:** Tasks are assigned tier-by-tier (e.g., all "service" tasks before any "plant"), so urgent survival work always runs first.

### Discarded Experiments:
- **Goose/COOP setup:** Costed −7,085 points; never attempted again.
- **Crew size >13:** Fib hire cost explodes past 13 (14th hand costs 987/day marginal vs 609/day for all 13). Testing 15-crew lost −22,138 (p=0.000, 0/16 wins).
- **Earlier land unlocks (days 6/10):** Lost −2,347 (p=0.004). Days 7/11 are already tuned.

## Dead Code: Decision Transformer

The codebase contains a NumPy `DecisionTransformer` class and `rl_weights.npz`, but:
- `dt_task` is computed at ~policy.py:1036 
- **immediately discarded** via `dt_assigned_task = None` at line 1044
- never influences task assignment or gameplay
- A/B test (A1 with DT vs without): **identical scores, p=1.000** — confirmed the DT is completely disconnected.

The "hybrid" label in prior docs is a misnomer; the agent is pure heuristic. The `rl_weights.npz` in the submission tar is inert dead weight (harmless but unnecessary). The DecisionTransformer code is preserved as a reference if future work wants to actually wire it in.
