# Design: Win-Rate Ratchet and Policy Macro Rewrite

Date: 2026-08-18
Status: Awaiting review
Supersedes: `/home/boris/.gemini/antigravity-ide/brain/7150db7e-3ccb-49ed-8e28-2be43cc5576a/implementation_plan.md`

---

## 1. Why the previous plan is being replaced

The previous plan identified four root causes for a stalled score: evaluation tooling
flaws, replay parser fragmentation, heuristic saturation in `policy.py`, and an
autoresearch bottleneck. Measurement against the live competition contradicts its
central premise and two of its four root causes.

### 1.1 The performance gap is smaller and differently shaped than assumed

The previous plan states the gap as "~88k local pool mean vs 140k-158k top leaderboard
champions" and sets out to close "50k+". That comparison puts our mean against the top
players' maximum. Measured from downloaded Kaggle replays:

| Player | Mean cash | Median | Win rate | n |
|---|---|---|---|---|
| Ankit Sain (us) | 78,971 | 79,754 | 64.3% | 14 |
| Ankit Sain (us, wider sample) | 79,618 | 78,780 | 55.8% | 43 |
| Ezzzzzekki | 94,437 | 86,955 | 98.3% | 59 |
| GiovanniCR | 89,558 | 89,013 | 95.0% | 60 |
| HealthStone | 92,360 | 89,420 | 98.3% | 60 |
| Ueddy | 95,729 | 92,182 | 95.0% | 60 |
| Utkarsh #2 | 97,080 | 96,707 | 83.3% | 60 |

The real cash gap is 11,000-18,000 (12-22%), not 50,000+. The win-rate gap is far
larger in relative terms: 56% against 83-98%.

### 1.2 The leaderboard metric was misidentified

The Kaggle score is a skill rating modelled as a Gaussian `N(mu, sigma^2)`, not a cash
total. Sigma contracts as a submission accumulates episodes, and only the latest two
submissions per team stay live. Rating moves on win, loss, or tie; the margin of victory
is discarded.

Current standing: public score 1028.8, rank approximately 1994 of 5132 teams. Top of
leaderboard is 3196-3276.

This invalidates the objective function used throughout the existing harness.
`evaluate.py`, `src/autoresearch/evaluator.py`, and the ratchet all optimise mean cash
delta. Cash beyond the amount needed to win is worth nothing to the rating.

### 1.3 There is no infrastructure failure to repair

The previous plan's first root cause was broken evaluation and tooling hiding agent
crashes. Verified against the live competition:

- 79 of 79 episodes for the current submission report state `COMPLETED`. No errors, no
  timeouts.
- Measured agent step time: mean 1.15 ms, p99 3.01 ms, max 59.03 ms, against an
  `actTimeout` of 1000 ms. No timeout risk.
- The submission tarball contains the correct `main.py` and `policy.py`.

Whatever is costing rank, it is not packaging or runtime failure.

### 1.4 The local opponent pool cannot measure what we need

`src/autoresearch/pool_evaluator.py` defines its pool as five checkpoints from our own
lineage: `Phase2_v1`, `Phase2_v7`, `Phase2_v11`, `EXP-20260814-12`, `EXP-20260815-69`.
The directory it also reads, `opponent_clones/`, does not exist. The pool reports an
87.5% win rate. Real-world win rate is 55.8%.

---

## 2. What the previous plan got right

Two claims survive verification and are carried forward.

**Town shop blindness is real.** An AST-level scan of the live decision path in
`policy.py` (everything below line 1050; the code above that threshold is the dead
decision-transformer scaffolding, with `DT_MODEL = None`) finds zero references to
`market.prices` and zero to `town.unlocked_shops`. The agent is blind to both.

**The self-play blind spot is real**, though the previous plan misdiagnoses its cause.
It is not only that symmetric improvements cancel. In a shared market, the strength of
the sparring partner inflates both the absolute score and the delta. See section 5.

---

## 3. New findings that drive this design

### 3.1 Market mechanics that the policy ignores

The market is shared between both players and prices move with net inventory. Premium
resources use `above_target > 1`, so modest gluts drive them to the $1 floor:
strawberry reaches the floor at roughly 62 units of excess inventory. Meanwhile wheat
price rises across the season (observed $25 to $51) because both players buy it for
animal feed, and fertilizer price collapses (observed $100 to $6) because both players
dump it.

The current policy sells everything every turn without consulting a price.

### 3.2 An idle-tile window at day 17-23

Instrumented self-play run, our agent, midday snapshots:

```
day 18 free=10  crops={STRAW:35, MELON:9, WHEAT:7}  seeds={WHEAT:22}  money=24333  hands=13
day 19 free=12  crops={STRAW:35, MELON:9, WHEAT:5}  seeds={WHEAT:34}  money=28696  hands=13
day 20 free=19  crops={STRAW:34, MELON:1, WHEAT:6}  seeds={WHEAT:36}  money=36724  hands=13
day 21 free=17  crops={STRAW:33, WHEAT:9}           seeds={WHEAT:37}  money=41615  hands=13
day 22 free=14  crops={STRAW:30, WHEAT:12}          seeds={WHEAT:32}  money=47834  hands=13
day 23 free= 6  crops={STRAW:28, WHEAT:20}          seeds={WHEAT:24}  money=49168  hands=13
```

This is not a shortage of seeds, money, or labour: at day 20 the agent holds 36 wheat
seeds, $36,724, and 13 hands while leaving 19 tiles idle. The nine melons are planted in
one day-0 batch and expire in one batch around day 19. `PLANT` does not outrank watering
and animal service until the day-20 tier promotion, which then takes four days to drain
the backlog.

Confirmed against real opponents across 14 Kaggle replays, mean idle tiles at midday:

| Day | Us | Opponent |
|---|---|---|
| 15 | 2.1 | 8.9 |
| 20 | 17.5 | 9.4 |
| 25 | 2.4 | 17.7 |

Cost estimate: roughly 84 idle tile-days, about 28 wheat cycles at $100-150 each, so
$3,000-4,000 or 4-5% of our mean. Real but not the whole gap. The farm demonstrably
absorbs the land at day 15 and day 25, so this is a scheduling artifact, not a capacity
ceiling.

### 3.3 Scripted-replay opponents are not viable

Replaying GiovanniCR's recorded action sequence from a 149,642-point episode against our
policy under fresh seeds produced 62,589 and 79,309. Actions are state-coupled through
weeds, money, and market prices, and `info.seed` is reported as 0 with
`configuration.seed` cleared, so the original episode cannot be reproduced. This rules
out the cheapest route to a real opponent pool.

---

## 4. Objective and measurement

**The objective changes from mean cash delta to probability of winning.**

Measurement is two-tier.

**Local screening.** Win rate against a diversified opponent pool. Measured cost is
9.2 s per game on 16 cores, so a 64-game evaluation completes in roughly 45 seconds of
wall clock with 14 workers.

**Kaggle confirmation.** Submission slot 2, with the current champion held in slot 1 as
a same-window control. Approximately two days per reading as sigma contracts. Holding a
control matters because ratings drift with the composition of the opponent field; without
it, a field-wide shift is indistinguishable from a real gain.

Local screening is a proxy. Where local and Kaggle disagree, Kaggle is authoritative and
the local pool is corrected.

---

## 5. Evaluation harness rebuild

### 5.1 Diversified opponent pool

Populate `opponent_clones/` with four to six deliberately off-lineage strategies:
melon-heavy, animal-heavy, wheat-rush, early-aggression, low-labour. These are built by
pushing constants far away from champion values, not by mutating around them. The goal is
strategic diversity, not strength. `pool_evaluator.py` already auto-loads every file in
that directory, so no harness change is needed to admit them.

### 5.2 Win-rate gating

Add a win-rate criterion to Stage 3 in `src/autoresearch/evaluator.py`. Promotion
requires an improvement in win rate, with cash delta demoted to a tiebreak.

Note an existing ordering defect: `pool_evaluator.py` already computes
`win_rate_overall` and `win_rate_vs_strong` and gates on the latter at 0.40, but Stages
1 and 2 of `evaluator.py` reject candidates on `delta <= reject_delta` before they ever
reach the pool. The win-rate machinery exists and is currently unreachable. Reordering
the cascade is part of this work.

### 5.3 Preconditions retained

Stage 0 invariant and AST lint gate, plus the full pytest suite (currently 105 passing),
remain hard preconditions for any candidate.

---

## 6. Role of the autoresearch ratchet

The ratchet is retained, repaired, and demoted from source of gains to finisher.

### 6.1 It works

151 experiments over three days, 13 KEEP and 138 REJECT for an 8.6% hit rate. Its
accumulated gain generalises to unseen seeds, which rules out seed overfitting:

| Seed set | Delta vs `Phase2_v12` | Win rate |
|---|---|---|
| 1000-1015 (the ratchet's own training seeds) | +39,353 | 100% |
| 20000-20015 (held out) | +38,804 | 100% |
| 55000-55015 (held out) | +41,892 | 100% |

### 6.2 It is opponent-overfit, not seed-overfit

Against `Phase2_v12` our champion earns 92k. Against a peer mirror it earns 66k. On real
Kaggle it earns 79k. In a shared market a weak sparring partner inflates both the
absolute score and the delta, because it leaves market share uncontested. The ratchet
optimised "beat our own lineage" and succeeded completely, which converted into 93 rating
points (935.3 to 1028.8) while real-world win rate remained at 56%.

### 6.3 Its search space is exhausted and too narrow to reach the macro work

Of 151 experiments, 77 are grid sweeps. `TARGET_STRAWBERRY` alone was probed 34 times.
Campaign 8 ran 16 experiments for zero promotions. `TIER1_PARAMS` contains 8 entries
against 32 module-level constants in `policy.py`.

Tier 3 edits only `TASK_TIER` integers. Tier 2 accepts `new_block_source` as a caller
argument, so it cannot originate new logic; a human or LLM must write the block. Only
Tiers 1 and 3 are autonomous.

No amount of constant tuning can create a code path that reads `market.prices`.

### 6.4 Changes to the ratchet

1. Repoint the gate at the diversified pool and gate on win rate.
2. Widen `TIER1_PARAMS` from 8 to approximately 25 parameters. The sweeps are exhausted;
   the box is not.
3. Run it after each macro change lands, to re-tune constants around the new
   architecture. Constants tuned for a price-blind agent are wrong once the agent can see
   prices: `TARGET_STRAWBERRY=35` encodes how much can be dumped at any price, and under
   price-aware selling the binding constraint becomes the glut threshold instead of
   throughput.

### 6.5 Alternatives considered and rejected

**Reinforcement learning or decision transformer.** Already attempted; commit a169088
records a 113k regression, and the dead scaffolding remains in `policy.py` at
`OBS_DIM = 107`. Six weeks with light compute is not an adequate budget.

**Behavioural cloning from the replay corpus.** Same compute constraint. The corpus has
already yielded its value through rule mining in `docs/analysis/decision-rules.md`.

**Population-based or cross-entropy-method search.** Searches the same constant box by a
different route; adds no capabilities.

---

## 7. Policy macro rewrite

Four workstreams, ordered by strength of evidence.

| # | Workstream | Evidence | Estimated value |
|---|---|---|---|
| 1 | Melon-expiry staggering and `PLANT` tier promotion | Instrumented: 19 idle tiles at day 20 with 36 seeds, $36,724, 13 hands available | $3,000-4,000 |
| 2 | Price-aware market layer | Zero references to `market.prices` in the live path; strawberry floors at ~62 units of glut; market is shared | Unquantified, probably the largest |
| 3 | Town shop demand read | Zero references to `town.unlocked_shops`; up to 8 shop instances each draining 6 units per day | Moderate |
| 4 | Schedule alignment to mined rules | Top players unlock NE day 6 and SW day 10 and reach 14 hands by day 20; we use (7, 9) and 13 hands | Small, low risk |

Workstream 1 is cheap and independently gateable. Workstream 4 is low risk. Workstreams
2 and 3 are bundles that require atomic gating, because their parts are not individually
positive: price-aware selling on its own is likely to lose, since holding stock while the
opponent dumps first floors the price before we sell.

### 7.1 Dropped from the previous plan

- The 50k-gap premise and the 140k-158k comparison.
- The five-subsystem division, the subagent delegation matrix, and the verification
  cascade diagrams. These are process ceremony with no effect on score.
- The framing of evaluation and tooling flaws as a root cause.
- "Animal Route Synchronization" as a headline item. Its stated evidence, that
  uncoordinated visits move travel from 46% to roughly 70% of worker turns, could not be
  reproduced. It is demoted to a candidate to be tested, not a planned change.

Retained: town shop blindness (verified), and endgame liquidation, demoted because we
already idle only 2.4 tiles at day 25.

---

## 8. Ratchet protocol

The governing constraint is that the champion never regresses. Never-degrade applies at
the promotion boundary, not at every intermediate edit, because a macro rewrite does not
decompose into individually-positive steps. Campaign 8 demonstrates the failure mode of
per-edit gating: 16 experiments, 0 promotions.

1. Work on a branch off `phase2-improvements`.
2. Stage 0 invariants and the full pytest suite must pass.
3. Local pool evaluation, gated on win rate against the current champion.
4. On failure: revert, log to the experiment ledger, never commit.
5. On success: commit, snapshot to `versions/`, submit to Kaggle slot 2.
6. On Kaggle confirmation after approximately two days: promote to slot 1 as the new
   champion.
7. Run a ratchet campaign against the newly promoted champion to re-tune constants.

Nothing that fails a gate reaches the champion or a submission. Slot 1 always holds the
best confirmed bot.

---

## 9. Success criteria

- Local: win rate against the diversified pool exceeds the current champion's, measured
  over at least 64 games.
- Kaggle: public score exceeds 1028.8 with the control held in slot 1 across the same
  window.
- Regression: the full pytest suite continues to pass, and Stage 0 invariants hold.
- Stretch: reach a rating above 2000, which corresponds to roughly rank 800 on the
  2026-08-15 leaderboard snapshot.

## 10. Open risks

- Local win rate against synthetic off-lineage opponents may not track Kaggle win rate
  against real ones. Mitigated by treating Kaggle as authoritative and holding a control
  submission.
- Workstreams 2 and 3 are gated atomically, so a bundle that fails yields no partial
  credit and the work is discarded.
- Kaggle readings cost approximately two days each, which bounds the number of
  confirmation cycles available before the 2026-09-30 deadline to roughly fifteen.
