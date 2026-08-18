# Flaw-Fix Roadmap Plan
# Source: deep replay analysis of champion_v2_20260815 (43 live episodes)

> **Goal**: Close the strategy gap revealed by live-competition replay analysis.
> Win rate is 55.8% overall and only 15.4% vs strong opponents (opp_score >90k).
> Six evidence-grounded flaws are addressed in priority order, each as a
> standalone KaggriRatchet experiment validated through the 4-stage cascade.
>
> **Non-goals**: No changes to the ratchet infrastructure, evaluator thresholds,
> or experiment ledger format. All fixes go through `--step` or `--loop` as usual.

---

## Evidence baseline (from probe_champion_v2.py + probe_champion_v2_deep.py)

| Metric | Current | Target | Source |
|---|---|---|---|
| Win rate overall | 55.8% (24W/19L) | >65% | 43 replays |
| Win rate vs strong opp >90k | 15.4% (2/13) | >50% | 13 games |
| Walk fraction | 61.5% | ≤46% | unit-turn totals |
| Fertilizer idle at h=12 (days 15–29) | 4–7 tiles/day | 0 | hour=12 snapshots |
| Uncared animals midday (days 15–27) | 4–7/game | 0 | hour=12 snapshots |
| Free tiles at day 10 h=12 | 34.0 avg | <5 | per-hour free-tile scan |
| Strawberry unsold at EOD | 21/43 games day 21 | 0 | shed hour=23 |
| Early pass turns (days 0–9) | 11.9% of unit-turns | <1% | phase breakdown |

---

## Sub-Task 1 — Fix CARE ordering in `_animal_pending` (FLAW 3)

**Intent**: The care bonus (pending_care_bonus → +1 yield) only banks when an animal
is both FED and CARED on the same day. Currently the operation order inside
`_animal_pending` is FEED → HARVEST → COLLECT_FERTILIZER → CARE. Workers finish
COLLECT_FERTILIZER and then get pulled to other tasks before completing CARE.
Midday (h=12) uncared counts reach 370 on day 15.

Reorder to FEED → HARVEST → CARE → COLLECT_FERTILIZER. CARE is a zero-cost
one-turn op once a worker is already at the tile; COLLECT_FERT can safely follow.

**Expected Outcomes**:
- Uncared animal count at h=12 drops significantly
- CARE bonus captured on more animal-days → extra MILK/WOOL units
- Ratchet decision: KEEP (estimated +$3–5k/game)

**Todo List**:
1. Write a Tier 2 block swap (`block_name="_animal_pending"`) that reorders the
   return chain: FEED → HARVEST → CARE → COLLECT_FERTILIZER → None
2. Register it as a composite hypothesis entry in `hypothesis.py` under
   `_COMPOSITE_MUTATIONS` (or as a standalone Tier 2 entry in `generate_hypothesis`)
3. Run via `python3 -m src.autoresearch.controller --step`
4. If KEEP: verify git state with `--test-ratchet`, update this plan status
5. If REJECT: document the stage/delta in this file and mark REJECTED

**Relevant context**:
- `policy.py`: `_animal_pending()` — current order at line ~241–255
- `src/autoresearch/mutator.py`: `mutate_tier2()` handles function-body replacement
- `src/autoresearch/hypothesis.py`: `_COMPOSITE_MUTATIONS` list for new Tier 0 entries

**Status**: [ ] pending

---

## Sub-Task 2 — Fix fertilizer collect-then-apply pipeline (FLAW 3 continued)

**Intent**: After COLLECT_FERTILIZER, the worker walks back to shed, drops the
fertilizer, then a different worker must PICKUP and walk to a strawberry to FERTILIZE.
This two-worker relay means 4–7 fertilizer units sit idle at h=12 every day from
day 15 onward. Estimated lost yield: ~$12k/game (5 tiles × $160/application × 15 days).

Fix: in `_unit_op` for the `service_soon` case, after performing COLLECT_FERTILIZER,
set the next task for that worker as "fertilize" on the nearest eligible tile
rather than returning to shed. This requires either:
  (a) a state flag on the worker's inventory check, or
  (b) routing the worker directly in `_unit_op` using `_nearest` on fertilizable tiles
      already in `scan["fertilize"]`.

The cleanest implementation: in `_unit_op`'s `service_soon` branch, after the
COLLECT_FERTILIZER action is dispatched, immediately return the FERTILIZE action if
the worker already carries fertilizer AND there's a fertilizable tile nearby. This
collapses two turns into one visit.

**Expected Outcomes**:
- Fertilizer idle at h=12 drops from 4–7 to near 0
- No shed round-trip for fertilizer; worker applies in same service visit
- Ratchet decision: KEEP (estimated +$8–12k/game, highest-impact single fix)

**Todo List**:
1. Write a Tier 2 block swap for `_unit_op` service_soon case that chains
   COLLECT_FERTILIZER → direct FERTILIZE routing when inventory has fertilizer
2. Also update `_animal_pending` to not return COLLECT_FERTILIZER if the worker
   already carries fertilizer (avoids double-collect on same tile)
3. Register as Tier 0 composite (two Tier 2 blocks: `_unit_op` + `_animal_pending`)
4. Run `--step`, capture decision + stage + delta
5. If KEEP: `--test-ratchet`, update plan
6. If REJECT: document and adjust approach (may need separate experiments)

**Relevant context**:
- `policy.py`: `_unit_op()` service_soon branch ~line 825–839
- `policy.py`: `_animal_pending()` — controls what action is returned
- `policy.py`: `scan["fertilize"]` — populated by `_scan()`, lists fertilizable tiles
- `src/autoresearch/mutator.py`: `mutate_composite()` for multi-block atomics

**Status**: [x] REJECTED — EXP-20260815-88 (broken _CLAIM_STATE), EXP-20260816-02/03 tested. Pipeline routing adds no measurable delta. Root cause may be that the fertilizer task is already Tier 1 and the issue is not priority but availability of carrying workers, which the existing sticky-claim system handles adequately.

---

## Sub-Task 3 — Fix post-land-expansion planting delay (FLAWS 1 & 2)

**Intent**: At day 7 h=06, 23.8 free tiles appear (NE quad). At day 10 h=12, 34.0
free tiles (SW quad). Workers are busy with Tier 0/1 animal service and ignore the
new land for 1–2 days. The endgame "plant→Tier 1" promotion already exists at
`day >= 20` but it comes 10+ days too late.

Fix: promote the `plant` task to Tier 1 for a short window (4–6 hours) immediately
after a land expansion event. The expansion is detectable as `quads > prev_quads`
in `_agent()`. Store a "just_expanded" flag for N hours and pass it to `_assign_tasks`
to temporarily flatten the tier.

Alternatively — simpler and already wired — lower the `endgame` threshold from
`day >= 20` to `day >= 10` OR trigger it whenever `free_cells > 15`.

**Expected Outcomes**:
- Day 10 h=12 free tile count drops from 34 to <5
- Day 11 h=00 free tile count drops from 17 to <3
- Walk fraction should decrease (less wandering on empty farm)
- Ratchet decision: KEEP (estimated +$4–6k/game)

**Todo List**:
1. Implement the simpler threshold variant first: change `endgame = day >= 20` in
   `_assign_tasks` to `endgame = day >= 10 or len(free_cells) > 15`
   — write as a Tier 2 block swap on `_assign_tasks`
2. Run `--step`, check stage + delta
3. If REJECT: try the `free_cells > 15` trigger variant as a separate experiment
4. If KEEP: `--test-ratchet`, update plan

**Relevant context**:
- `policy.py`: `_assign_tasks()` — `endgame = day >= 20` at line ~745
- `policy.py`: `_build_tasks()` — where `free_cells` list is known
- Endgame plant promotion logic is already proven to work (day 20+ path)

**Status**: [ ] pending

---

## Sub-Task 4 — Fix early-game idle PASS turns (FLAW 5)

**Intent**: Days 1–4, the 3-hand crew idles at 11.9% PASS rate (8,243 unit-turns
across 43 games). On days 1–4, the farm has 6 animals + 7 MELON + 4 WHEAT plants.
After service + water, all 4 workers (farmer + 3 hands) have nothing to do.

Fix: Ensure that on days 1–4, the 20+ wheat seeds purchased on day 0 are being
utilised. The `_build_tasks` planting logic requires free tiles, which exist (NW quad
has ~25 tiles, ~18 are occupied by day 1). The worker-crew is small enough that
some workers have no task after tier-0/1 work is done.

Check: is planting being suppressed because `hour > plant_cutoff (20)` on late-hour
turns? If so, widen the cutoff slightly OR add a dedicated pass-prevention path
that ensures any worker with no assignment and seeds available will plant.

**Expected Outcomes**:
- Early-game PASS rate drops from 11.9% to <2%
- Slightly more WHEAT/MELON planted in days 1–4
- Ratchet decision: expected small positive delta

**Todo List**:
1. Verify with a targeted probe: on what HOUR do early PASS turns cluster?
   Run `python3 probe_champion_v2_pass_hours.py` (small script: extract all PASS
   actions per day/hour from replays, find the peak)
2. Based on probe: if PASS clusters at hour > 20, lower `plant_cutoff` from 20 to 18
   as a Tier 1 parameter sweep (add `PLANT_CUTOFF` to `config.py` PARAMETERS)
3. If PASS clusters at hour 0–6 (workers at shed with nothing to do), ensure the
   morning pickup→plant routing is wired for small-crew days
4. Run `--step`, capture outcome

**Relevant context**:
- `policy.py`: `_build_tasks()` — `plant_cutoff = 22 if (total_days - day) < 5 else 20`
- `policy.py`: `_agent()` idle-worker fallback at line ~977–986 (PASS or dropoff)
- The probe scripts `probe_champion_v2.py` / `probe_champion_v2_deep.py` are the
  diagnostic tools to use

**Status**: [ ] pending

---

## Sub-Task 5 — Fix strawberry sell throttle (FLAW 7)

**Intent**: In 21/43 games, strawberry units are left in the shed at EOD on day 21
(avg 7.7 units). This is caused by the early-hour sell throttle in `plan_sells`:
`orders += sells if hour >= 2 else sells[:3]`. When multiple products need selling
at hours 0–1, strawberry (the highest-value item at $120 base) may be cut.

Fix: Give STRAWBERRY and MELON unconditional priority in the early-hour throttle.
Reserve slot 0 and 1 for the two most valuable items regardless of hour.

**Expected Outcomes**:
- Strawberry unsold at EOD drops from 21/43 to <5/43
- Small but consistent revenue improvement on peak production days

**Todo List**:
1. Write a Tier 2 block swap for `plan_sells` (or inline R2 block) that ensures
   STRAWBERRY and MELON sell orders are always included in the first 3 slots
2. Run `--step`, capture outcome
3. If KEEP: `--test-ratchet`, update plan

**Relevant context**:
- `policy.py`: `plan_sells()` function ~line 196–211
- `policy.py`: R2 block in `_make_market_orders` — `orders += sells if hour >= 2 else sells[:3]`
- `SELL_PRODUCE` order: currently `["STRAWBERRY", "MELON", ...]` so STRAW is first —
  the throttle to 3 orders is the actual problem, not the ordering

**Status**: [ ] pending

---

## Sub-Task 6 — Fix day-0 unplaced animal (FLAW 6)

**Intent**: Only 3/4 purchased animals are placed by EOD day 0. On day 0, `place_animal`
is Tier 1, competing with `plant` (also Tier 1) and `build_pasture` (Tier 2).
The 5-hand crew finishes pasture-building and plants 11 MELON + 7 WHEAT, leaving one
animal unplaced overnight. An unplaced animal earns no yield and blocks the pasture slot.

Fix: Temporarily boost `place_animal` to Tier 0 on day 0 only, so the opening
placement always completes before planting begins.

**Expected Outcomes**:
- Day 0 EOD animal count: 4 placed (up from 3)
- One extra day of MILK or WOOL production from the previously-stranded animal

**Todo List**:
1. Implement as a Tier 2 block swap on the `place_animal` section of `_build_tasks`:
   set task tier to 0 when `day == 0`
   OR: add conditional in `_assign_tasks` that bumps place_animal tier to 0 on day 0
2. Run `--step`, capture outcome (small expected delta)

**Relevant context**:
- `policy.py`: `TASK_TIER` dict — `"place_animal": 1`
- `policy.py`: `_build_tasks()` — place_animal task emission
- `src/autoresearch/mutator.py`: `mutate_tier3()` can change TASK_TIER entries directly

**Status**: [x] REJECTED — EXP-20260816-08 Δ=+0 Stage 2. Task-list ordering doesn't move the needle because _assign_tasks reassigns based on distance+tier regardless of list order.

---

## Execution Order

Run sub-tasks in this order (highest-to-lowest expected impact), but each is
independently testable via `--step`:

```
ST-1 (CARE order)  →  ST-2 (fertilizer pipeline)  →  ST-3 (expansion planting)
  →  ST-4 (early PASS probe + fix)  →  ST-5 (sell throttle)  →  ST-6 (day-0 place)
```

After every KEEP decision:
1. `python3 -m src.autoresearch.controller --test-ratchet`
2. Update `docs/strategy/strategy-gaps.md` to mark the gap resolved
3. Update `docs/roadmap/roadmap.md` current champion entry
4. Update this plan file: mark sub-task `[x] done`

After every REJECT decision:
1. Document the stage reached + delta in the sub-task notes
2. Consider a revised approach (different block, different scope)
3. Move to the next sub-task

---

## Success Criteria

| Criterion | Threshold |
|---|---|
| Overall win rate | >65% (from 55.8%) |
| Win rate vs strong opponents | >40% (from 15.4%) |
| Walk fraction | <55% (from 61.5%) |
| Fertilizer idle at h=12 | <2 tiles avg |
| Uncared at h=12 (day 15–27) | <2 avg |
| Ratchet gate | All accepted fixes: p<0.05, Δ>0, stage 3 pass |
