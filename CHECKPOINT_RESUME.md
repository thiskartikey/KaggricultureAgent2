# Kagriculture Agent — Resume Checkpoint

> **Updated**: 2026-08-07
> **Status**: ✅ v7 built, verified, and pushed. v5 was submitted to Kaggle live
> (see §7b/7c for the live-match results) — v7 supersedes it and is not yet
> submitted.
> **Previous checkpoint** (now superseded, its premises were wrong): `versions/archive/CHECKPOINT_RESUME_20260807_pre-v5.md`

**If you are a fresh agent picking this up: read this whole file first. It is
self-contained. Do not trust `instructions/environment.md` — see §7.**

---

## 0. Repository

This repo is pushed to GitHub: **https://github.com/gytdrop/KaggricultureAgent**
(branch `main`). Full commit history, including every version referenced below
as `versions/heuristic_vN.py`, lives there — clone or `git log` it instead of
re-deriving history from file timestamps.

```bash
git remote -v          # origin -> github.com/gytdrop/KaggricultureAgent.git
git log --oneline       # commit history
```

`downloads/` (2.3 GB of replay JSONs, §3) and `.agents/` are gitignored and
**not** on GitHub — only `versions/` (small, code) is tracked for history.
See `instructions/git.md` for the commit/push workflow, including the trap
that `git add -A` stages the entire replay corpus and will be rejected by
GitHub on size.

---

## 1. Where things stand

The agent is a **pure heuristic**. `ml_main.py` imports nothing but `heuristic.py`;
the RL path (`env_wrapper.py`, `rl_inference.py`, `rl_weights.npz`) is present in
the repo but **dead code** — verified by running a tarball containing only
`main.py` + `heuristic.py` and getting byte-identical scores.

Measured with `evaluate.py`, 10 seeds × 2 seats = 20 games per pairing:

| Matchup | New | Old | Result |
|---|---|---|---|
| v5 vs the original `heuristic.py` | **110,561** | 1,638 | 20/20 wins, p=0.000 |
| v5 vs intermediate build | **91,837** | 70,663 | 20/20 wins, p=0.000 |

Self-play (both seats running v5, harsher — they compete for the same market):
**~85k–93k**. Top leaderboard replays are **100k–158k**.

The starting point scored **1,929** — it *lost* money from the 3,000 start. The
old checkpoint's claim of "11k–70k" was wrong, as was its diagnosis.

### Reproduce the numbers

```bash
python evaluate.py heuristic.py versions/heuristic_BASELINE_ab.py --games 10
```

⚠️ Scores swing ~2× run to run. **Never A/B on a single game.** Use ≥10 seeds and
read the p-value.

---

## 2. Ground truth — read the env source, do not guess

The real rules ship with the package:

```
~/.local/lib/python3.14/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py
```

~1060 lines. Several assumptions baked into the old code were wrong against it
(e.g. `LAND_PRICES` was coded `[1000,2000,3000]`; it is actually `[1000,2000,4000]`).

Mechanics that actually drive strategy:

- 720 steps = **30 days × 24 turns**. Reward = **final money**. Start 3,000.
- **Farm hands are wiped every night** (`_end_of_day`) — they must be re-hired
  *every morning*. The n-th hire *of that day* costs `fib(n)` (1,1,2,3,5,8,…),
  so a 13-hand crew is only ~609/day. Hands respawn on the 4 shed-access tiles.
- A plant becomes a WEED after **2 consecutive unwatered days**, and its planting
  day already counts as unwatered — **it must be watered the day it is sown**.
- **Ongoing** crops (STRAWBERRY, TOMATO) yield on schedule *regardless of
  watering*; watering only adds yield on non-ongoing crops (WHEAT, MELON) inside
  `[(max_yield_day+1)//2, max_yield_day]`. So strawberries can be watered on
  alternate days to stay alive, freeing a lot of labour.
- An animal escapes after **2 consecutive unfed days** (1 WHEAT/day each).
  `CARE` + `FEED` on the same day banks `pending_care_bonus`, which **accumulates**
  and pays out on the next production day — roughly triples animal yield.
- Every animal drops **1 FERTILIZER/day free** (base 100).
- Shed holds **100 items; end-of-day overflow is DISCARDED**, and a full shed
  blocks `BUY_ANIMAL` / `BUY_PRODUCT`.
- **Only 10 market orders per turn** are processed; extras are dropped silently.
- `BUY_PRODUCT` only works for **WHEAT and FERTILIZER**.
- Market: FERTILIZER has **no town demand at all**, so its price never recovers.
  Demand ∝ number of shops selling it: WHEAT 5, STRAWBERRY 4, MILK 3, MELON 0.

---

## 3. Top-player blueprint (mined from the replays)

Source data: 73 JSONs in `downloads/training/` (2.2 GB) → 144 player-episodes.
Aggregated over the **117 player-episodes scoring ≥100k**:

- **Land**: 3 quadrants only — NE at day 7 (1000), SW at day 11 (2000).
  The 4th (4000) is **never** bought; it cannot pay back.
- **Steady state from day 11** on 75 tiles: **14 PASTURE (8 COW + 6 SHEEP),
  42 STRAWBERRY, 12 MELON, ~7 WHEAT**.
- **Day 0 opening**: 6 PASTURE, 11 MELON, 7 WHEAT, 2 COW, 2 SHEEP, 5 HIRE,
  8 WHEAT bought as feed — exactly 10 market orders.
- **Hands**: 5 on day 0, only **~3 on days 1–6** (one quadrant needs little
  labour and every coin is wanted for seed/livestock), 8 by day 7, **11–14 daily
  from day 11**.
- **Zero** GOOSE/COOP/EGG, zero CARROT, zero TOMATO — all dominated.
- From ~day 20 spent MELON tiles are recycled into WHEAT (fast 5-day cycle).

Mining scripts are in the session scratchpad and easy to recreate; the aggregate
conclusions above are the durable part.

---

## 4. Traps that cost enormous score — do not reintroduce

1. **Hiring.** The old code hired once on day 0, then a hardcoded 32-coin reserve
   blocked a **1-coin** hire, so it ran ~10 days with **zero hands**. That single
   bug was most of the 1,929 score.
2. **Feeding.** A worker can only `FEED` while **carrying WHEAT**. Assigning the
   merely *closest* worker to a hungry animal made it arrive empty-handed, do the
   care/collect chores instead, and the herd starved from 14 down to 6.
   Restricting hungry animals to wheat-carrying workers was worth **+21k
   head-to-head on its own**. Workers also grab wheat at dawn, when they respawn
   already standing on the shed tiles.
3. **Task thrashing.** A single flat `distance − priority` score made workers
   oscillate and burned **~85% of all unit-turns on walking** (top replays: ~46%).
   Fixed with (a) **strict tiers** matched **by pure distance** inside each tier,
   and (b) **sticky claims** — a claim is held until the job disappears from the
   task list.
4. **Pasture spam.** The old code built a pasture on every free tile (23 → 57),
   paving over all the crop land. Cap is 14.
5. **Harvest timing.** Non-ongoing crops keep accruing yield while watered;
   harvesting clears the tile. Harvest at `max_yield_day`, not the first moment
   `yield_units > 0` — otherwise you throw away most of a melon.

---

## 5. File map

| File | Role |
|---|---|
| `heuristic.py` | **The entire agent.** ~970 lines, all strategy lives here |
| `ml_main.py` | Entrypoint; packaged as `main.py`, just delegates to `heuristic.agent` |
| `evaluate.py` | A/B harness, both seats, paired t-test |
| `build_submission.py` | Builds `ml_submission.tar.gz` |
| `env_wrapper.py`, `rl_inference.py`, `rl_weights.npz` | **Unused** (dead RL path) |
| `downloads/training/*.json` | 73 top-player replays |
| `downloads/protected/` | ⚠️ **NEVER modify or delete** |
| `versions/` | Backups, incl. `heuristic_BASELINE_ab.py` (the pre-rewrite agent) |

Internal structure of `heuristic.py`: market price model (mirrors the env
exactly) → specs → blueprint targets → `_make_market_orders` → `_scan` →
`_build_tasks` → `_assign_tasks` (tiers + sticky claims) → `_unit_op` → `_agent`
→ `agent` (**must stay the last top-level function**).

---

## 6. Submission

```bash
python build_submission.py
```

Produces `ml_submission.tar.gz` (964 KB). **Verified**: extracted to a clean temp
dir and run from a neutral cwd (so `import heuristic` can only resolve inside the
extraction, as on Kaggle) — both seats `DONE`, no timeouts. 2.4 ms per agent call
against the 1 s `actTimeout`.

Not yet uploaded — that is the user's call.

**Optional slimming**: 98.8% of the tarball is the unused `rl_weights.npz`.
A tarball of only `main.py` + `heuristic.py` scores *identically* (verified).
Trim `files_to_add` in `build_submission.py` to those two entries to get ~11 KB.

---

## 7. Corrections to `instructions/`

`instructions/environment.md` was factually wrong and will mislead you:

- It said the season ends **day 365** — it is **day 30** (720 steps ÷ 24).
- It said the goal is "total assets (cash + land/animal valuation)" — the reward
  is **final money only**. Land and livestock are worth nothing at the buzzer, so
  everything must be converted to cash before day 29 ends.

Those two lines have been corrected in the file. The rest of `instructions/`
(`restrictions.md`, `submission.md`, `evaluation.md`) is accurate and still worth
reading. `instructions/heuristics.md` describes the *old* task-priority design
that was replaced in §4.3 — treat it as historical.

**Do not run the cleanup command in `instructions/cleanup.md` as written.** It
ends with `find downloads/ ... ! -name 'protected' -exec rm -rf {} +`, which
deletes all 73 training replays (2.2 GB, not easily re-downloadable).

---

## 7c. v7 — the compaction breakthrough (read this before tuning anything)

Three live losses were analysed (eps 90752570, 90754154, 90754089). Our stats
were near-identical in all three (HIRE exactly 10,891; FEED 234-243; CARE
252-263; efficiency 30%), while the three winners' styles varied wildly — one
spent 16k total, another 44k. So there was no single tactic to copy. Two signals
were consistent: **every winner fed at least as often as they cared** (we did
the reverse), and they ran 31-38% useful unit-turns against our 30%.

**The breakthrough was spatial, not strategic.** `_free_cells` returned tiles in
row-major order, so pastures got built in the far corners while feeding costs a
shed round-trip per animal. Sorting free cells by distance from the shed —
claiming land from the centre outwards — was worth **+17,521 (24/24)** by itself.

**Then the ordering mattered enormously.** Feeding every animal daily was tested
twice:

| | before compaction | after compaction |
|---|---|---|
| feed every animal daily | **−11,018** (0/24) | **+18,184** (0/24) |

Same patch, opposite sign. On a scattered farm, feeding stole the crew from
urgent watering and crops died; on a compact farm it is cheap and unlocks the
accumulating care bonus. **If a labour-side change fails, re-test it after any
routing improvement before concluding it is bad.**

Net v7 vs the v5 that was submitted: **123,369 vs 81,261, +42,107, 24/24, p=0.000.**
Mechanics moved into the winners' band: efficiency 30%→35%, FEED 238→325
(now exceeding CARE, the winners' signature), MILK 119→210, WOOL 89→138.

Crew size was re-swept after each change and **13 remains the peak** every time
(9 and 11 and 15 all lose). Do not cut it on the strength of an opponent's
9-hand economy — that was tested three times and lost every time.

## 7b. Live-game analysis vs Juan David Bolanos (ep 90752570)

First real match: **gytdrop 97,389 vs Juan David Bolanos 110,541**. The gap was
**not** revenue — we *out-grossed* him, 124,494 to 122,911. It was entirely cost:

| | us | him |
|---|---|---|
| gross sales | **124,494** | 122,911 |
| total spend | **33,163** | 16,615 |
| — hiring | **10,891** | 2,585 |
| — wheat bought as feed | **6,512** | 2,690 |
| — land | 3,000 (3 quadrants) | 1,000 (2 quadrants) |
| avg hands/day | 9.9 (13 late) | flat 9 |

His three edges were a flat 9-hand crew, buying the 2nd quadrant on **day 0**,
and growing 130 wheat seeds instead of importing feed.

**Only the wheat one transfers.** Each was ablated separately against v5
(10 seeds x 2 seats each):

| Change | vs v5 | Verdict |
|---|---|---|
| Crew 9 (his) | **−17,103** | much worse — **do not** |
| Crew 11 | −6,966 | worse |
| Buy land day 0 | −1,306 | noise, p=0.29 |
| **Grow wheat, don't buy** | **+5,964** | **adopted** |

Crew size was then swept both ways and **13 is the peak**: 9 < 11 < **13** > 15 > 17
(crew 17 collapses to 48k). His 9-hand economy works for *his* agent because his
routing is tighter (38% useful unit-turns vs our 30%, 3,769 moves vs our 5,112).
Ours genuinely needs the bodies. **Cutting the crew is only worth revisiting
after the walking problem is fixed, not before.**

Adopted change (v6): wheat seed target `max(4, min(rest,25))` → `max(8, min(rest,30))`.
Validated at **+5,531, 25/32 wins, p=0.000** over 16 seeds x 2 seats.

Lesson: five changes were bundled first and lost 23,619 (0/24). Ablate one at a time.

## 8. Next levers (highest value first)

Measured per-episode sales, us vs the ≥100k replays:

| Product | Us | Top players | Gap |
|---|---|---|---|
| STRAWBERRY | 166 | 396 | **−230** |
| MILK | 115 | 295 | **−180** |
| WOOL | 83 | 203 | **−120** |
| FERTILIZER | 224 | 220 | ✅ matched |
| MELON | 134 | 193 | −59 |

1. **Replanting.** We PLANT only ~96 times a game while harvesting ~318 — tiles
   are cleared and then left fallow. Kameron Green planted **319** times and
   grossed 155,703 (the highest gross seen). This is now the largest single gap.
   Likely causes: seed budget, and `plant` sitting at tier 2 behind upkeep.
2. **More routing.** Compaction took efficiency 30%→35%; the best opponent hit
   38%. Remaining ideas: order the water queue along a route rather than by
   nearest-worker, and let workers chain adjacent tiles.
3. **Melon pricing.** Juan realised 196/unit on 108 melons; we get ~153/unit on
   ~133. We dump into our own price — consider a per-day melon sell cap.
4. **GOOSE is not actually dominated.** Juan ran 2 geese for 87 EGG (~4,982).
   EGG decays logarithmically so its price barely moves. The mined blueprint
   said zero geese, but that was an average over many players — worth one test.
