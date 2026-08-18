"""Hypothesis generator for KaggriRatchet.

Generates bounded, testable hypotheses addressing top bottlenecks identified
by the telemetry extractor, while checking the experiment memory to avoid
proposing duplicate failed experiments.

Each hypothesis is expressed as a structured JSON object:
  {
    "id": "HYP-<timestamp>",
    "tier": 1|2|3,
    "rationale": "...",
    "bottleneck": "...",
    "target_code": "policy.<function>",
    "mutation": {
      # Tier 1:  {"param_name": "...", "new_value": ...}
      # Tier 2:  {"block_name": "...", "new_block_source": "..."}
      # Tier 3:  {"task_name": "...", "new_tier": ...}
    },
    "expected_delta": <float estimate>,
    "tags": [...],
  }
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.autoresearch.config import PARAMETERS, get_search_space
from src.autoresearch.memory import load as load_memory, DEFAULT_LEDGER
from src.autoresearch.telemetry import BottleneckReport


# ---------------------------------------------------------------------------
# Hypothesis schema helpers
# ---------------------------------------------------------------------------

def _make_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"HYP-{ts}"


def build_hypothesis(
    tier: int,
    rationale: str,
    bottleneck: str,
    target_code: str,
    mutation: Dict[str, Any],
    expected_delta: float,
    tags: List[str],
) -> Dict[str, Any]:
    return {
        "id": _make_id(),
        "tier": tier,
        "rationale": rationale,
        "bottleneck": bottleneck,
        "target_code": target_code,
        "mutation": mutation,
        "expected_delta": expected_delta,
        "tags": tags,
    }


# ---------------------------------------------------------------------------
# Experiment history helpers
# ---------------------------------------------------------------------------

def _already_tried(mutation: Dict[str, Any], experiments: list) -> bool:
    """Return True if an identical mutation (same param + same value) has been
    attempted before — regardless of decision.  Prevents re-running exact same
    config on every loop restart.
    """
    import hashlib
    mut_str = json.dumps(mutation, sort_keys=True)
    mut_hash = hashlib.sha256(mut_str.encode()).hexdigest()[:16]
    for r in experiments:
        stored = r.get("diff_summary", "")
        if not stored:
            continue
        # New-style: hash embedded in diff_summary prefix
        if f'"_hash":"{mut_hash}"' in stored:
            return True
        # Exact match via JSON parse (works for Tier 1 / short mutations)
        try:
            prev = json.loads(stored)
            if json.dumps(prev, sort_keys=True) == mut_str:
                return True
            if prev.get("_hash") == mut_hash:
                return True
        except Exception:
            pass
    return False


def _current_value(param: str) -> Any:
    """Read the current live value of a top-level constant from policy.py."""
    import ast
    from src.autoresearch.controller import POLICY_PATH
    try:
        source = POLICY_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == param:
                        return ast.literal_eval(node.value)
    except Exception:
        pass
    return PARAMETERS[param][0]  # fallback to config default


# ---------------------------------------------------------------------------
# Full candidate generation — Tier 1 bidirectional + categorical + Tier 3
# ---------------------------------------------------------------------------

def _all_tier1_candidates(
    tried_params: set,
    experiments: list,
) -> List[Dict[str, Any]]:
    """Generate all untried Tier 1 mutations across the full search space."""
    candidates = []

    for param, spec in PARAMETERS.items():
        if param in tried_params:
            continue

        current = _current_value(param)
        space = get_search_space(param)

        if space["type"] == "categorical":
            for choice in space["choices"]:
                if choice == current:
                    continue
                mutation = {"param_name": param, "new_value": choice}
                if _already_tried(mutation, experiments):
                    continue
                candidates.append(build_hypothesis(
                    tier=1,
                    rationale=(
                        f"Categorical sweep: try {param} = {choice!r} "
                        f"(currently {current!r})."
                    ),
                    bottleneck="CATEGORICAL_SWEEP",
                    target_code=f"policy.{param}",
                    mutation=mutation,
                    expected_delta=200.0,
                    tags=["categorical_sweep", param.lower()],
                ))

        else:
            lo, hi, step = space["lo"], space["hi"], space["step"]
            # Generate all grid points in both directions from current value
            grid = set()
            v = lo
            while v <= hi + 1e-9:
                grid.add(round(v))
                v += step

            for new_val in sorted(grid):
                if new_val == current:
                    continue
                if not (lo <= new_val <= hi):
                    continue
                mutation = {"param_name": param, "new_value": int(new_val) if isinstance(step, int) or step == int(step) else new_val}
                if _already_tried(mutation, experiments):
                    continue
                direction = "up" if new_val > current else "down"
                candidates.append(build_hypothesis(
                    tier=1,
                    rationale=(
                        f"Grid sweep {direction}: {param} {current} -> {new_val}."
                    ),
                    bottleneck="GRID_SWEEP",
                    target_code=f"policy.{param}",
                    mutation=mutation,
                    expected_delta=100.0,
                    tags=["grid_sweep", param.lower()],
                ))

    return candidates


# ---------------------------------------------------------------------------
# Composite (Tier 0) candidates — multiple coupled sub-mutations, applied
# atomically as a single experiment unit.
# ---------------------------------------------------------------------------

# Each entry:
#   (key, steps, rationale, tags, expected_delta)
# where steps is a list of sub-mutation dicts as consumed by mutate_composite.

_COMPOSITE_MUTATIONS = [
    # ── C1: coupled R1+R4+LAND_UNLOCK rewrite ────────────────────────────────
    # Three changes that MUST move together:
    #   1. R1: day-0 opening → 4 hires + 1 COW + 4 SHEEP + 5 MELON + 5 WHEAT
    #      (replay telemetry: Ezzzzzekki 5 games, HealthStone 5 games)
    #   2. LAND_UNLOCK_DAY → (6, 10) so NE unlock fires on day 6 not day 7
    #      (100% of top players unlock NE on day 6 in replays)
    #   3. R4: lower cash floor for land-buy from $350 to $50
    #      (WOOL revenue ~$1,000-1,700 on day 6 repays within <24 h)
    # Previous isolated R1 attempt (T2-F) failed catastrophically (−118,638)
    # because the low day-0 seed count starved _seed_targets.  Fixing all three
    # together keeps the economy coherent.
    (
        "c1_r1_r4_land_unlock",
        [
            # Sub-mutation 1: LAND_UNLOCK_DAY = (6, 10)
            {
                "tier": 1,
                "param_name": "LAND_UNLOCK_DAY",
                "new_value": (6, 10),
            },
            # Sub-mutation 2: R1 day-0 opening block
            {
                "tier": 2,
                "block_name": "R1",
                "new_block_source": '''\
    # ── R1: day 0 opening -- confirmed from replay telemetry (Ezzzzzekki pattern) ──
    # 4 hires, 1 COW + 4 SHEEP (WOOL engine), 5 MELON + 5 WHEAT seeds.
    # Seeds bought incrementally on days 2-7 — no front-loading.
    if day == 0 and hour == 0:
        return [
            ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"],
            ["BUY_ANIMAL", "COW", 1],
            ["BUY_ANIMAL", "SHEEP", 4],
            ["BUY_SEED", "MELON", 5],
            ["BUY_SEED", "WHEAT", 5],
            ["BUY_PRODUCT", "WHEAT", 5],
        ]

''',
            },
            # Sub-mutation 3: R4 land-unlock cash guard lowered to $50
            {
                "tier": 2,
                "block_name": "R4",
                "new_block_source": '''\
    # ── R4: land -- NE day 6, SW day 10, never the 4th ──────────────────────
    # Lower cash guard for land unlock: $50 floor (not $350) is enough since
    # the WOOL revenue cycle resupplies the treasury within 24 hours.
    if quads - 1 < len(LAND_UNLOCK_DAY) and day >= LAND_UNLOCK_DAY[quads - 1]:
        cost = _land_cost(me)
        land_floor = 50  # lower floor specifically for land: repaid in <1 day
        if money_left >= cost + land_floor and len(orders) < 10:
            orders.append(["BUY_LAND"])
            money_left -= cost

''',
            },
        ],
        (
            "Coupled R1+R4+LAND_UNLOCK: 4-hire/1COW/4SHEEP opening + LAND_UNLOCK_DAY=(6,10) "
            "+ lower land-buy cash guard to $50. All three must move together: isolated R1 "
            "failed (−118k) because seed inventory + land timing were mismatched."
        ),
        ["opening", "R1", "R4", "land_unlock", "coupled"],
        8000.0,
    ),
    # ── C2: LAND_UNLOCK_DAY=(6,10) + R4 lower cash guard only ────────────────
    # Safer version of C1: keep the current R1 opening (2 COW + 2 SHEEP) intact.
    # Only move:
    #   1. LAND_UNLOCK_DAY (7,11) → (6,10): all top players unlock NE on day 6
    #   2. R4 cash guard: $350 → $50 so the unlock actually fires on day 6
    # Without the lower floor the land-unlock was blocked even when LAND_UNLOCK_DAY
    # was changed (CASH_FLOOR $350 + $1000 NE cost requires $1350; day-6 cash ~$500).
    # These two must move together — changing LAND_UNLOCK_DAY alone does nothing.
    (
        "c2_land_unlock_only",
        [
            # Sub-mutation 1: LAND_UNLOCK_DAY = (6, 10)
            {
                "tier": 1,
                "param_name": "LAND_UNLOCK_DAY",
                "new_value": (6, 10),
            },
            # Sub-mutation 2: R4 land-unlock cash guard lowered to $50
            {
                "tier": 2,
                "block_name": "R4",
                "new_block_source": '''\
    # ── R4: land -- NE day 6, SW day 10, never the 4th ──────────────────────
    # Lower cash guard for land unlock: $50 floor (not $350) is enough since
    # the WOOL revenue cycle resupplies the treasury within 24 hours.
    if quads - 1 < len(LAND_UNLOCK_DAY) and day >= LAND_UNLOCK_DAY[quads - 1]:
        cost = _land_cost(me)
        land_floor = 50  # lower floor specifically for land: repaid in <1 day
        if money_left >= cost + land_floor and len(orders) < 10:
            orders.append(["BUY_LAND"])
            money_left -= cost

''',
            },
        ],
        (
            "Coupled LAND_UNLOCK_DAY=(6,10) + R4 cash guard $50: unlock NE on day 6 "
            "like all top players, with a low floor so $500+ clears the gate. "
            "Does NOT change the R1 opening — safer than C1."
        ),
        ["land_unlock", "R4", "coupled", "c2_land_unlock"],
        5000.0,
    ),
    # ── C3: LAND_UNLOCK_DAY=(7,9) — earlier SW unlock only ───────────────────
    # NE unlock stays at day 7 (proven optimal).  SW land normally unlocks day
    # 11, but with CASH_FLOOR=200 the agent has more cash available by day 9.
    # SW costs $2000. At day 9 our agent typically has $3k-5k (from strawberry
    # harvests starting around day 10).  Try unlocking SW 2 days earlier.
    # This is purely Tier 1 (no block change needed — the $200 floor already
    # allows the SW purchase when day >= 9 with ~$3k in hand).
    # Wrapped as composite to test alongside no-other-changes context.
    (
        "c3_sw_land_day9",
        [
            {
                "tier": 1,
                "param_name": "LAND_UNLOCK_DAY",
                "new_value": (7, 9),
            },
        ],
        (
            "LAND_UNLOCK_DAY=(7,9): keep NE at day 7, unlock SW 2 days earlier (day 9 vs 11). "
            "With CASH_FLOOR=200 the agent has $3k+ by day 9 to afford the $2000 SW cost."
        ),
        ["land_unlock", "sw_early", "c3_sw_day9"],
        2000.0,
    ),
    # ── C4: CARE before COLLECT_FERTILIZER in _animal_pending ────────────────
    # Replay analysis (43 live games): midday (h=12) uncared animals average
    # 370 on day 15, in 43/43 games. Root cause: current order is
    #   FEED → HARVEST → COLLECT_FERTILIZER → CARE
    # COLLECT_FERT steals the worker slot; the worker is then reassigned before
    # CARE fires. The care bonus (+1 yield) only banks when BOTH fed AND cared
    # on the same day — skipping CARE voids the bonus.
    # Fix: swap CARE before COLLECT_FERTILIZER.
    (
        "c4_care_before_collect_fert",
        [
            {
                "tier": 2,
                "block_name": "_animal_pending",
                "new_block_source": '''\
def _animal_pending(t, has_wheat=True):
    """Outstanding work on an occupied pasture, in the order it should be done.

    Feeding leads: an animal unfed two days running escapes, taking its 400-500
    purchase price and every future yield with it.

    CARE comes before COLLECT_FERTILIZER: the care bonus (+1 yield) only banks
    when an animal is both fed AND cared on the same day.  COLLECT_FERT can
    safely follow — missing one collection is cheaper than missing the care bonus.
    """
    if not t.get("fed_today") and has_wheat:
        return "FEED"
    if int(t.get("yield_units", 0)) > 0:
        return "HARVEST"
    if not t.get("cared_today"):
        return "CARE"
    if t.get("fertilizer_available"):
        return "COLLECT_FERTILIZER"
    return None
''',
            },
        ],
        (
            "CARE before COLLECT_FERTILIZER in _animal_pending: reorder service ops so "
            "the care bonus (+1 yield/day) is captured before COLLECT_FERT steals the "
            "worker slot. Replay evidence: 370 uncared animals at h=12 on day 15 in "
            "43/43 live games. Estimated +$3-5k/game."
        ),
        ["care_order", "_animal_pending", "c4_care_first"],
        4000.0,
    ),
    # ── C5: fertilizer collect-then-apply in single pasture visit ────────────
    # After COLLECT_FERTILIZER, worker walks to shed, drops, then another worker
    # picks up and applies. Replay: 4-7 fertilizer units idle at h=12 every day
    # from day 15 onward (~$12k/game at 5 tiles × $160/application × 15 days).
    # Fix: after the service_soon visit completes COLLECT_FERTILIZER, if the
    # worker is now carrying fertilizer and there are fertilizable tiles in
    # scan["fertilize"], route directly to FERTILIZE without a shed round-trip.
    # Also incorporates the C4 CARE-before-COLLECT_FERT reorder so both fixes
    # are active together.
    # NOTE: _unit_op signature gains an optional `scan` parameter; the call
    # site in _agent() already passes scan implicitly — but _unit_op must
    # accept it. The call in _agent is updated in this composite too.
    (
        "c5_fert_collect_apply_v3",
        [
            # Step 1 (only): _unit_op — after service_soon COLLECT_FERTILIZER, route
            # directly to nearest fertilizable tile instead of shedward.
            # No call-site change needed: we re-scan `me` inside the function
            # to get the current fertilize list, keeping the existing signature.
            {
                "tier": 2,
                "block_name": "_unit_op",
                "new_block_source": '''\
def _unit_op(pos, task, private, unit_idx, board, me, shed_wheat):
    invs = private.get("inventories") or []
    inv = invs[unit_idx] if unit_idx < len(invs) else {}
    kind = task[0]
    target = task[1] if len(task) > 1 else None
    pos = tuple(pos)
    sheds = shed_adjacent_cells(board, me)
    shed_positions = [tuple(c) for c in sheds]

    def _go(cell, act):
        if pos == tuple(cell):
            return act
        st = step_toward(pos, cell)
        return [st] if st else act

    def _to_shed(act):
        if pos in shed_positions:
            return act
        tgt = min(sheds, key=lambda c: manhattan(pos, c))
        st = step_toward(pos, tgt)
        return [st] if st else act

    def _fetch(item, qty, then_cell, act):
        """Grab `item` from the shed, then head for the job."""
        if int(inv.get(item, 0)) > 0:
            return _go(then_cell, act)
        store = int((private.get("shed") or {}).get(item, 0))
        if store <= 0:
            return ["PASS"]
        return _to_shed(["PICKUP", item, min(store, qty)])

    if kind in ("service", "service_soon"):
        # Work the whole pasture in place: feed, harvest, care, collect.
        tiles = me.get("tiles") or []
        x, y = target
        tile = tiles[y][x] if 0 <= y < len(tiles) and 0 <= x < len(tiles[y]) else None
        if not isinstance(tile, dict):
            return ["PASS"]
        has_wheat = int(inv.get("WHEAT", 0)) > 0
        pend = _animal_pending(tile, has_wheat)
        if pend is None:
            # Only feeding is left and this worker is empty-handed.
            if not tile.get("fed_today"):
                return _fetch("WHEAT", 8, target, ["FEED"])
            # Worker finished all pasture work and is carrying fertilizer.
            # Re-scan the farm to find fertilizable tiles and route directly,
            # collapsing the collect-shed-pickup-apply relay into one visit.
            # _scan is cheap (single tile pass) and avoids a call-site change.
            if int(inv.get("FERTILIZER", 0)) > 0:
                live_scan = _scan(me, 0)  # day=0 is safe: fertilize list ignores day
                fert_tiles = live_scan.get("fertilize") or []
                if fert_tiles:
                    nearest_fert = _nearest(pos, fert_tiles)
                    if nearest_fert is not None:
                        return _go(nearest_fert, ["FERTILIZE"])
            return ["PASS"]
        return _go(target, [pend])
    if kind == "place_animal":
        animal, cell = target
        return _fetch(animal, 1, cell, ["PLACE", animal])
    if kind == "harvest_crop":
        return _go(target, ["HARVEST"])
    if kind in ("water", "water_soon"):
        return _go(target, ["WATER"])
    if kind == "build_pasture":
        return _go(target, ["BUILD_PASTURE"])
    if kind == "build_coop":
        return _go(target, ["BUILD_COOP"])
    if kind == "fertilize":
        return _go(target, ["FERTILIZE"])
    if kind == "plant":
        crop, cell = target
        return _go(cell, ["PLANT", crop])
    if kind == "weed":
        return _go(target, ["DIG"])
    if kind == "dropoff":
        return _to_shed(["DROP"])
    return ["PASS"]


# ── Main agent internal logic ─────────────────────────────────────────────────
# Sticky task claims, kept per seat so self-play in one process cannot cross
# them.  Reset whenever the step counter is not the expected successor (new
# episode, new day, replay) so stale claims never leak between games.
_CLAIM_STATE = {}
''',
            },
        ],
        (
            "Fertilizer collect-then-apply in one visit: after service_soon completes "
            "COLLECT_FERTILIZER, worker re-scans farm and routes directly to the nearest "
            "fertilizable strawberry tile instead of returning to shed. "
            "Eliminates the 2-worker relay (collect->shed->pickup->apply). "
            "Replay evidence: 4-7 fertilizer units idle at h=12 every day from day 15, "
            "estimated ~$12k/game. v3: no CARE reorder, _unit_op only."
        ),
        ["fert_pipeline_v3", "_unit_op", "c5_fert_apply_v3"],
        12000.0,
    ),
]


def _composite_key(key: str) -> str:
    return f"composite_{key}"


def _composite_already_tried(key: str, tags: List[str], experiments: list) -> bool:
    """Check if a composite mutation has been tried before.

    Uses two signals:
    1. The composite_key embedded in diff_summary (new-style records)
    2. Matching tags set (fallback for records logged before composite_key was added)
    """
    tags_set = set(tags)
    for r in experiments:
        r_tags = set(r.get("tags") or [])
        if r_tags == tags_set:
            return True
        try:
            summary = r.get("diff_summary", "")
            if f'"composite_key": "{key}"' in summary:
                return True
        except Exception:
            pass
    return False


def _all_composite_candidates(
    tried_params: set,
    experiments: list,
) -> List[Dict[str, Any]]:
    """Generate all untried composite mutations."""
    candidates = []
    for key, steps, rationale, tags, expected_delta in _COMPOSITE_MUTATIONS:
        ckey = _composite_key(key)
        if ckey in tried_params:
            continue
        if _composite_already_tried(key, tags, experiments):
            continue
        # Embed the composite key in the mutation dict so the controller can
        # reconstruct the tried_params key without relying on tags[-1].
        mutation = {"composite_key": key, "steps": steps}
        candidates.append(build_hypothesis(
            tier=0,
            rationale=rationale,
            bottleneck="COMPOSITE_REWRITE",
            target_code="policy._make_market_orders",
            mutation=mutation,
            expected_delta=expected_delta,
            tags=tags,
        ))
    return candidates


# ---------------------------------------------------------------------------
# Tier 2 block-replacement candidates
# ---------------------------------------------------------------------------

# Each entry: (block_name, new_source, rationale, tags, expected_delta)
# new_source must be the complete replacement function/block with correct indent.

_TIER2_MUTATIONS = [
    # ── T2-A: faster labour ramp ───────────────────────────────────────────
    (
        "target_hands",
        '''\
def target_hands(day, total_days):
    """Faster crew ramp: match top-player labour curve more tightly.

    Top players run 3 hands days 1-4, 8 hands days 5-8, 13 from day 9.
    Original was 3 until day 7, 8 until day 11.
    """
    if day <= 0:
        return 5
    if day < 5:
        return 3
    if day < 9:
        return 8
    if day >= total_days - 2:
        return 10
    return 13
''',
        "Faster labour ramp: ramp to 8 hands at day 5 (not 7) and 13 at day 9 (not 11).",
        ["labour", "target_hands"],
        800.0,
    ),
    # ── T2-B: remove early-hour sell gate ─────────────────────────────────
    # The sells[:3] cap at hour < 2 reserves 7 order slots for hiring on
    # the opening turns.  But R3 (hiring) fires after R2 (sells) so hiring
    # is never blocked by sells.  Removing the cap lets all sell orders fire
    # immediately and frees the next turns for other orders.
    # We target the enclosing R2 comment-block inside _make_market_orders.
    (
        "R2",
        '''\
    # ── R2: sell first so the rest of the turn is funded ─────────────────────
    # Taper the wheat buffer in the final days: animals don't need feed after
    # the game ends, so release held wheat as we approach the last turn.
    days_left = total_days - day
    effective_buffer = max(0, min(2, days_left - 1))
    hold = {"WHEAT": feed_hold(fed_animals, int(shed.get("WHEAT", 0)),
                               days_buffer=effective_buffer)}
    sells = plan_sells(shed, minv, day, hour, total_days, hold)
    # Fire all sell orders every turn: hiring (R3) comes after sells so it
    # is never crowded out, and the extra early-turn sells bank revenue sooner.
    orders += sells
    for o in orders:
        inv = int(minv.get(o[1], 10000))
        rev, _ = sell_revenue(o[1], inv, o[2])
        money_left += rev

''',
        "Remove early-sell gate: let all sell orders fire at hour 0-1, not just 3.",
        ["market", "sell_gate", "r2"],
        600.0,
    ),
    # ── T2-C: endgame crew cutoff one day earlier (applied to faster ramp) ────
    (
        "target_hands",
        '''\
def target_hands(day, total_days):
    """Faster ramp + earlier endgame cutoff.

    Ramps to 8 at day 5, 13 at day 9 (from T2-A), and cuts to 10 one
    day earlier at total_days-3 to save the fib hiring cost on day 27.
    """
    if day <= 0:
        return 5
    if day < 5:
        return 3
    if day < 9:
        return 8
    if day >= total_days - 3:
        return 10
    return 13
''',
        "Endgame crew cutoff: faster ramp + shrink to 10 hands at total_days-3.",
        ["labour", "target_hands", "endgame"],
        400.0,
    ),
    # ── T2-D: tighter wheat seed floor in mid/late game ───────────────────
    # Current wmin=15 early / 20 endgame. Top players plant wheat
    # aggressively; a wmin of 10/25 may better match their seed buffering.
    (
        "_seed_targets",
        '''\
def _seed_targets(day, total_days, planted, free_n, harvest_crop_n=0):
    """Tighter wheat floor: wmin 10 early (was 15), wmin 25 endgame (was 20)."""
    left = total_days - day
    want = {}

    target_free = free_n + harvest_crop_n

    if left >= 13:
        want["MELON"] = max(0, min(TARGET_MELON - planted.get("MELON", 0), target_free))
        want["STRAWBERRY"] = max(
            0, min(TARGET_STRAWBERRY - planted.get("STRAWBERRY", 0),
                   target_free - want["MELON"]))
    if left >= 5:
        rest = target_free - want.get("MELON", 0) - want.get("STRAWBERRY", 0)
        wmax = 60 if left <= 12 else 30
        wmin = 25 if left <= 12 else 10
        want["WHEAT"] = max(wmin, min(max(0, rest), wmax))
    return want
''',
        "Wheat seed floor: wmin 10 early (was 15) and 25 endgame (was 20) to free early cash.",
        ["seeds", "_seed_targets", "wheat"],
        350.0,
    ),
    # ── T2-E: lower feed_hold cap from 45 to 28 ──────────────────────────
    # cap of 45 = 3 days × 15 animals. With effective_buffer already
    # tapering to 2 days in R2, the outer cap of 45 is redundant. Lowering
    # to 28 (2 × 14 animals) releases ~17 extra wheat units for selling.
    (
        "feed_hold",
        '''\
def feed_hold(animal_count, shed_wheat, days_buffer=3):
    """Wheat reserve cap lowered from 45 to 28 units.

    effective_buffer already tapers to 2 days in R2, so the outer cap
    of 45 is never reached under normal conditions and holds wheat
    unnecessarily. Cap at 28 = 2 days × 14 max animals.
    """
    return min(shed_wheat, min(28, animal_count * days_buffer))
''',
        "Lower feed_hold cap 45->28 to release ~17 wheat units for selling.",
        ["wheat", "feed_hold", "endgame"],
        400.0,
    ),
    # ── T2-F: correct day-0 R1 opening to match real top-player blueprint ──
    # Replay telemetry (5 games each) confirms:
    #   Ezzzzzekki: 4 hires, 1 COW + 4 SHEEP, 5 MELON + 5 WHEAT seeds
    #   HealthStone: 3 hires, 1 COW + 4 SHEEP, 5 MELON + 5 WHEAT seeds
    # Our current opening: 5 hires, 2 COW + 2 SHEEP, 11 MELON + 7 WHEAT + 8 WHEAT_PRODUCT
    # The WOOL from 4 SHEEP starts day 6 (~$1,000-1,700) and funds the NE unlock.
    # Seeds are bought incrementally on days 2-7, not front-loaded on day 0.
    (
        "R1",
        '''\
    # ── R1: day 0 opening -- confirmed from replay telemetry (Ezzzzzekki pattern) ──
    # 4 hires, 1 COW + 4 SHEEP (WOOL engine), 5 MELON + 5 WHEAT seeds.
    # Seeds bought incrementally on days 2-7 — no front-loading.
    if day == 0 and hour == 0:
        return [
            ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"],
            ["BUY_ANIMAL", "COW", 1],
            ["BUY_ANIMAL", "SHEEP", 4],
            ["BUY_SEED", "MELON", 5],
            ["BUY_SEED", "WHEAT", 5],
            ["BUY_PRODUCT", "WHEAT", 5],
        ]

''',
        "R1 opening: 4 hires + 1 COW + 4 SHEEP + 5 MELON + 5 WHEAT seeds (matches real replay blueprint).",
        ["opening", "R1", "sheep"],
        5000.0,
    ),
    # ── T2-G: lower LAND_UNLOCK_DAY to (6, 10) with lower CASH_FLOOR guard ─
    # Replays show top players unlock NE on day 6 with ~$500-1700 in hand
    # (funded by WOOL from 4 SHEEP). Current CASH_FLOOR=350 blocks the
    # unlock because $518-350=$168 < $1000 (NE cost). Lower CASH_FLOOR to
    # 50 for the land-unlock check specifically so $518 clears the gate.
    # This is a targeted Tier 1 mutation on LAND_UNLOCK_DAY + CASH_FLOOR.
    (
        "R4",
        '''\
    # ── R4: land -- NE day 6, SW day 10, never the 4th ──────────────────────
    # Lower cash guard for land unlock: $50 floor (not $350) is enough since
    # the WOOL revenue cycle resupplies the treasury within 24 hours.
    if quads - 1 < len(LAND_UNLOCK_DAY) and day >= LAND_UNLOCK_DAY[quads - 1]:
        cost = _land_cost(me)
        land_floor = 50  # lower floor specifically for land: repaid in <1 day
        if money_left >= cost + land_floor and len(orders) < 10:
            orders.append(["BUY_LAND"])
            money_left -= cost

''',
        "R4 land unlock: lower cash guard from $350 to $50 so $518 on day 6 clears the gate.",
        ["land", "R4", "unlock"],
        3000.0,
    ),
    # ── T2-H: early sell gate at hour >= 1 (not >= 2) ─────────────────────
    # Current R2 caps sells to 3 orders at hour 0 and 1. Previous T2-B
    # tried removing ALL caps (fire at any hour) but was rejected. A milder
    # tweak: allow full sells from hour 1 (not hour 2) gains one extra hour
    # of full sell capacity per day without flooding the order queue at hour 0.
    (
        "R2",
        '''\
    # ── R2: sell first so the rest of the turn is funded ─────────────────────
    # Taper the wheat buffer in the final days: animals don't need feed after
    # the game ends, so release held wheat as we approach the last turn.
    days_left = total_days - day
    effective_buffer = max(0, min(2, days_left - 1))
    hold = {"WHEAT": feed_hold(fed_animals, int(shed.get("WHEAT", 0)),
                               days_buffer=effective_buffer)}
    sells = plan_sells(shed, minv, day, hour, total_days, hold)
    # Full sells from hour 1 onwards; at hour 0 keep 3-sell cap for hiring space.
    orders += sells if hour >= 1 else sells[:3]
    for o in orders:
        inv = int(minv.get(o[1], 10000))
        rev, _ = sell_revenue(o[1], inv, o[2])
        money_left += rev

''',
        "Early sell gate at hour>=1 (not >=2): one extra hour of full sell capacity per day.",
        ["market", "R2", "sell_gate_h1"],
        400.0,
    ),
    # ── T2-I: SHEEP-before-COW purchase order in R6 ───────────────────────
    # Currently R6 buys 8 COW first, then 6 SHEEP.  SHEEP yield WOOL every 3
    # days (interval=3, first=6) while COW yield MILK every 2 days (interval=2,
    # first=8).  WOOL starts earlier, so buying SHEEP first may accelerate
    # the early-game income that funds the NE land purchase.
    (
        "R6",
        '''\
    # ── R6: animals -- 6 SHEEP then 8 COW (WOOL comes before MILK) ──────────
    census = _animal_census(me, private)
    empty_pastures = sum(
        1 for row in (me.get("tiles") or []) for t in row
        if isinstance(t, dict) and t.get("kind") == "PASTURE" and not t.get("animal"))
    pending = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    slots = empty_pastures - pending
    if (day < total_days - 8 and slots > 0 and shed_total < SHED_CAP - 5
            and len(orders) < 10):
        for animal, target in (("SHEEP", TARGET_SHEEP), ("COW", TARGET_COW), ("GOOSE", TARGET_GOOSE)):
            if census[animal] >= target or slots <= 0:
                continue
            cost = ANIMAL_SPECS[animal]["cost"]
            want = min(target - census[animal], slots)
            afford = int((money_left - CASH_FLOOR) // cost)
            want = min(want, max(0, afford))
            if want > 0:
                orders.append(["BUY_ANIMAL", animal, want])
                money_left -= cost * want
                slots -= want
                break

''',
        "R6 animal purchase order: SHEEP before COW so WOOL revenue starts at day 6 (before MILK at day 8).",
        ["animals", "R6", "sheep_first"],
        700.0,
    ),
    # ── T2-J: boost early STRAWBERRY seed buying in R7 ───────────────────
    # Currently _seed_targets only buys STRAWBERRY when left >= 13.  But
    # we also need a buffer for day-1 and day-2 seed buying so we can start
    # sowing STRAWBERRY tiles immediately as pastures are built and free
    # tiles open up.  Raise the STRAWBERRY target during the first 5 days.
    (
        "R7",
        '''\
    # ── R7: seeds for the tiles we are about to sow ─────────────────────────
    planted = _crop_census(me)
    harvest_n = len(scan.get('harvest_crop', [])) if scan else 0
    want_seeds = _seed_targets(day, total_days, planted, len(free_cells), harvest_n)
    # Early-game boost: on days 1-5 also buy STRAWBERRY seeds aggressively so
    # newly built pastures' adjacent tiles can be sown immediately.
    if day <= 5 and int(seeds.get("STRAWBERRY", 0)) < 6:
        want_seeds.setdefault("STRAWBERRY", 0)
        want_seeds["STRAWBERRY"] = max(want_seeds.get("STRAWBERRY", 0), 6)
    for crop in ("MELON", "STRAWBERRY", "WHEAT"):
        if len(orders) >= 10:
            break
        deficit = want_seeds.get(crop, 0) - int(seeds.get(crop, 0))
        if deficit <= 0:
            continue
        unit = CROP_SPECS[crop]["seed"]
        afford = int((money_left - CASH_FLOOR) // unit)
        n = min(deficit, max(0, afford))
        if n > 0:
            orders.append(["BUY_SEED", crop, n])
            money_left -= unit * n

    return orders[:10]

''',
        "R7 early STRAWBERRY boost v2 (fixed return): buy up to 6 STRAWBERRY seeds on days 1-5 to sow newly freed tiles immediately.",
        ["seeds", "R7", "strawberry_v2"],
        500.0,
    ),
    # ── T2-K: R7 SW-land seed burst after day 9 unlock ──────────────────────
    # With LAND_UNLOCK_DAY=(7,9) the SW quadrant opens on day 9 (+25 tiles).
    # But _seed_targets uses a fixed TARGET_STRAWBERRY=38. On day 9 when
    # quads==3, bump the effective strawberry target to 50 temporarily to
    # ensure enough seeds are in hand to sow the new SW tiles immediately.
    # This REPLACES R7 (includes the return statement since R7 is the last block).
    (
        "R7",
        '''\
    # ── R7: seeds for the tiles we are about to sow ─────────────────────────
    planted = _crop_census(me)
    harvest_n = len(scan.get('harvest_crop', [])) if scan else 0
    want_seeds = _seed_targets(day, total_days, planted, len(free_cells), harvest_n)
    # SW land burst: on days 9-12 after 3-quadrant unlock, boost STRAWBERRY
    # seed target to fill the ~25 new SW tiles immediately.
    if 9 <= day <= 12 and quads >= 3:
        planted_straw = planted.get("STRAWBERRY", 0)
        sw_boost_target = min(50, planted_straw + len(free_cells) + harvest_n)
        deficit_straw = sw_boost_target - planted_straw
        if deficit_straw > want_seeds.get("STRAWBERRY", 0):
            want_seeds["STRAWBERRY"] = deficit_straw
    for crop in ("MELON", "STRAWBERRY", "WHEAT"):
        if len(orders) >= 10:
            break
        deficit = want_seeds.get(crop, 0) - int(seeds.get(crop, 0))
        if deficit <= 0:
            continue
        unit = CROP_SPECS[crop]["seed"]
        afford = int((money_left - CASH_FLOOR) // unit)
        n = min(deficit, max(0, afford))
        if n > 0:
            orders.append(["BUY_SEED", crop, n])
            money_left -= unit * n

    return orders[:10]

''',
        "R7 SW-land seed burst: on days 9-12 after 3-quad unlock, boost STRAWBERRY seed buying to fill 25 new SW tiles.",
        ["seeds", "R7", "sw_burst"],
        1200.0,
    ),
    # ── T2-N: _plant_choice — raise STRAWBERRY cap after SW land opens ────────
    # With LAND_UNLOCK_DAY=(7,9) the SW quadrant opens day 9 (+25 new tiles).
    # _plant_choice caps STRAWBERRY at TARGET_STRAWBERRY=38, so it ignores the
    # new SW tiles entirely and plants WHEAT instead.  Post-SW, boosting the
    # effective cap to 50 ensures all new tiles are sown with STRAWBERRY (value
    # ~120/harvest × 2+ harvests) rather than WHEAT (value ~25/harvest × 2).
    # Expected gain: ~12 new STRAWBERRY tiles × 2 extra harvests × ~$80 net = $1920.
    (
        "_plant_choice",
        '''\
def _plant_choice(day, total_days, planted, seeds):
    """Pick the crop with the best remaining payback for one free tile.

    After SW land opens on day 9+ (3 quadrants), temporarily raise the
    effective STRAWBERRY cap to 50 to fill the ~25 new SW tiles.
    """
    left = total_days - day
    # Dynamic strawberry cap: raise after SW land opens (day 9+ with many planted)
    straw_cap = TARGET_STRAWBERRY
    if day >= 9 and planted.get("STRAWBERRY", 0) >= TARGET_STRAWBERRY - 2:
        straw_cap = 50
    # MELON: 6 units x base 250 for an 80 seed, but needs maxday(12)+1 in soil.
    if (planted.get("MELON", 0) < TARGET_MELON and left >= 13
            and int(seeds.get("MELON", 0)) > 0):
        return "MELON"
    # STRAWBERRY: ongoing, first yield +10 then every 2 days.
    if (planted.get("STRAWBERRY", 0) < straw_cap and left >= 13
            and int(seeds.get("STRAWBERRY", 0)) > 0):
        return "STRAWBERRY"
    # WHEAT: min viable window = 3 days.
    if left >= 3 and int(seeds.get("WHEAT", 0)) > 0:
        return "WHEAT"
    return None
''',
        "_plant_choice: raise STRAWBERRY cap to 50 after day 9 when SW land opens (day9+ and near cap).",
        ["plant_choice", "sw_straw_cap"],
        1500.0,
    ),
    # ── T2-O: _seed_targets — no MELON seeds after day 17 ───────────────────
    # MELON needs maxday=12 + 1 days minimum in soil = 13 days.  After day 17
    # (i.e. left < 13) the current code already skips MELON seeds.  But the
    # effective cutoff for viable MELON is left >= 16 (to reach max_yield=12
    # before the game ends and cover the seed cost).  Moving the cutoff to
    # left<16 saves ~80 coins/seed on seeds that cannot reach full value, and
    # frees order slots for WHEAT seed buying in the mid-game.
    (
        "_seed_targets",
        '''\
def _seed_targets(day, total_days, planted, free_n, harvest_crop_n=0):
    """Move MELON seed cutoff to left<16 (was left<13); redirect budget to WHEAT."""
    left = total_days - day
    want = {}

    target_free = free_n + harvest_crop_n

    if left >= 16:
        want["MELON"] = max(0, min(TARGET_MELON - planted.get("MELON", 0), target_free))
    if left >= 13:
        want["STRAWBERRY"] = max(
            0, min(TARGET_STRAWBERRY - planted.get("STRAWBERRY", 0),
                   target_free - want.get("MELON", 0)))
    if left >= 5:
        rest = target_free - want.get("MELON", 0) - want.get("STRAWBERRY", 0)
        wmax = 60 if left <= 12 else 30
        wmin = 20 if left <= 12 else 15
        want["WHEAT"] = max(wmin, min(max(0, rest), wmax))
    return want
''',
        "_seed_targets: stop buying MELON seeds when left<16 (was <13) to free cash for WHEAT.",
        ["seeds", "_seed_targets", "melon_cutoff"],
        400.0,
    ),
    # ── T2-L: R5 feed reserve — lower restock threshold to fed_animals//2 ───
    # Currently R5 restocks wheat only when deficit >= fed_animals.  With 14
    # animals, this means we wait until we have < 0 wheat left for the next
    # day.  A deficit of 7+ (half the herd) is already dangerous. Lower
    # threshold to fed_animals // 2 to keep a steadier supply.
    (
        "R5",
        '''\
    # ── R5: feed reserve -- an animal unfed 2 days running escapes ──────────
    # Wheat the workers are already carrying counts: it left the shed but it is
    # still ours.  Ignoring it made this rule re-fire every single turn and buy
    # the same feed a dozen times a day.
    if fed_animals > 0 and day < total_days - 1:
        have = int(shed.get("WHEAT", 0))
        for inv in (private.get("inventories") or []):
            have += int(inv.get("WHEAT", 0))
        need = fed_animals * 3 - have
        room = SHED_CAP - shed_total - 5
        need = min(need, max(0, room), 45)
        # Restock when deficit reaches half the herd (not the full herd) to
        # keep a steadier wheat supply and avoid same-day starvation.
        restock_threshold = max(3, fed_animals // 2)
        if need >= restock_threshold and len(orders) < 10:
            c, _ = buy_cost("WHEAT", int(minv.get("WHEAT", 10000)), need)
            if money_left >= c:
                orders.append(["BUY_PRODUCT", "WHEAT", need])
                money_left -= c

''',
        "R5 feed restock at fed_animals//2 deficit (not full herd): steadier wheat supply.",
        ["wheat", "R5", "feed_threshold"],
        600.0,
    ),
    # ── T2-M: _seed_targets — raise STRAWBERRY target after SW unlock ────────
    # When SW land unlocks on day 9 the farm expands from ~50 to ~75 tiles.
    # The current TARGET_STRAWBERRY=38 cap prevents sowing the new SW tiles
    # with strawberry.  This function variant dynamically raises the effective
    # target based on remaining days and free tiles.
    (
        "_seed_targets",
        '''\
def _seed_targets(day, total_days, planted, free_n, harvest_crop_n=0):
    """Dynamic strawberry target: scales up when SW land opens (day 9+)."""
    left = total_days - day
    want = {}

    target_free = free_n + harvest_crop_n

    # After SW unlock (estimated day 9+), the farm is ~75 tiles.
    # Allow more strawberry if there are many free tiles to fill.
    eff_straw_target = TARGET_STRAWBERRY
    if day >= 9 and target_free >= 20:
        # Raise by up to 10 extra to cover new SW tiles without exceeding 50
        eff_straw_target = min(50, TARGET_STRAWBERRY + 10)

    if left >= 13:
        want["MELON"] = max(0, min(TARGET_MELON - planted.get("MELON", 0), target_free))
        want["STRAWBERRY"] = max(
            0, min(eff_straw_target - planted.get("STRAWBERRY", 0),
                   target_free - want["MELON"]))
    if left >= 5:
        rest = target_free - want.get("MELON", 0) - want.get("STRAWBERRY", 0)
        wmax = 60 if left <= 12 else 30
        wmin = 20 if left <= 12 else 15
        want["WHEAT"] = max(wmin, min(max(0, rest), wmax))
    return want
''',
        "_seed_targets: raise strawberry target by 10 on day 9+ when SW land opens (many free tiles).",
        ["seeds", "_seed_targets", "sw_straw_boost"],
        900.0,
    ),
    # ── T2-P: lower endgame plant-promotion threshold to fix expansion delay ──
    # Replay evidence (43 live games): 34 free tiles at day 10 h=12 after SW
    # land unlock; 17 free at day 11 h=00. The current `endgame = day >= 20`
    # flag in _assign_tasks promotes `plant` to Tier 1, but the post-expansion
    # planting delay starts at day 7 (NE) and day 10 (SW) — 10+ days before
    # the endgame threshold triggers.
    # Fix: lower the threshold to `day >= 10 or len(free_cells) > 15` so the
    # promotion fires whenever there is genuinely a lot of empty land to fill,
    # not only in the final third of the game.
    (
        "_assign_tasks",
        '''\
def _assign_tasks(positions, tasks, invs, board, claims=None, feed_cells=None,
                  day=0, total_days=30):
    """Tier-by-tier greedy nearest-pair matching, with sticky claims.

    Recomputing assignments from scratch every turn made workers oscillate:
    a unit walking to a tile would be swapped onto another job the moment a
    colleague drifted closer, so nobody ever arrived.  A claim is therefore
    kept until the job it points at disappears from the task list.
    """
    assignment = {}
    taken = set()
    free = set(range(len(positions)))

    live = {}
    for t in tasks:
        live.setdefault((t[0], _task_cell(t)), t)

    # 1. Honour existing claims that still correspond to outstanding work.
    for ui, prev in (claims or {}).items():
        if ui not in free:
            continue
        key = (prev[0], _task_cell(prev))
        if key in live and key not in taken:
            assignment[ui] = live[key]
            taken.add(key)
            free.discard(ui)

    # 2. Fill the rest by a global score, strongly preferring d=0 for non-urgent tasks.
    # Promote "plant" to Tier 1 when there are many free tiles (post land-expansion)
    # OR in the classic endgame (day >= 20).  The old threshold of day >= 20 let
    # the NE (day 7) and SW (day 10) expansions idle for 1-2 days.
    free_tile_count = sum(1 for t in tasks if t[0] == "plant")
    endgame = day >= 20 or free_tile_count >= 10
    feed_cells = feed_cells or set()
    have_wheat = any(int((invs[ui] if ui < len(invs) else {}).get("WHEAT", 0)) > 0 for ui in free)
    pairs = []

    for ui in free:
        for t in tasks:
            key = (t[0], _task_cell(t))
            if key in taken:
                continue
            tier = TASK_TIER.get(t[0], 3)
            # Endgame / expansion: plant is now equal priority to service_soon so freed
            # tiles get sown before CARE/COLLECT_FERTILIZER steals every worker slot.
            if endgame and t[0] == "plant":
                tier = 1
            cell = _task_cell(t)
            if cell is None:
                continue
            inv = invs[ui] if ui < len(invs) else {}
            carrying = int(inv.get("WHEAT", 0)) > 0
            if t[0] == "fertilize" and int(inv.get("FERTILIZER", 0)) <= 0:
                continue
            hungry = t[0] in ("service", "service_soon") and cell in feed_cells
            if hungry and have_wheat and not carrying:
                continue

            d = manhattan(positions[ui], cell)
            if hungry and carrying:
                d -= 3

            # Score logic: Tier 0 is absolute priority.
            # If a worker is AT the tile (d=0), they should do the task there instead
            # of walking, UNLESS there\'s a Tier 0 emergency.
            score = tier * 1000 + d
            if d == 0 and tier > 0:
                score -= 1500  # Pulls it below the tier above it, but not below tier 0.

            pairs.append((score, ui, key, t))

    pairs.sort(key=lambda p: (p[0], p[1]))
    for score, ui, key, t in pairs:
        if ui not in free or key in taken:
            continue
        assignment[ui] = t
        taken.add(key)
        free.discard(ui)
    return assignment
''',
        "_assign_tasks: promote plant to Tier 1 when >= 10 plant tasks exist (post land-expansion) not just at day >= 20.",
        ["routing", "_assign_tasks", "expansion_plant"],
        5000.0,
    ),
    # ── T2-Q: ST-3 revised — time-gated expansion planting (days 7–13 only) ──
    # T2-P promoted plant whenever free_tile_count >= 10, which fired mid-game
    # and starved animal feeding (-4760). Revised: only promote plant to Tier 1
    # during the two land-expansion windows (days 7–13) when the NE/SW quads
    # just unlocked. Outside that window, use normal Tier 2. This is narrower
    # and avoids stealing workers from animals during established midgame.
    (
        "_assign_tasks",
        '''\
def _assign_tasks(positions, tasks, invs, board, claims=None, feed_cells=None,
                  day=0, total_days=30):
    """Tier-by-tier greedy nearest-pair matching, with sticky claims.

    Recomputing assignments from scratch every turn made workers oscillate:
    a unit walking to a tile would be swapped onto another job the moment a
    colleague drifted closer, so nobody ever arrived.  A claim is therefore
    kept until the job it points at disappears from the task list.
    """
    assignment = {}
    taken = set()
    free = set(range(len(positions)))

    live = {}
    for t in tasks:
        live.setdefault((t[0], _task_cell(t)), t)

    # 1. Honour existing claims that still correspond to outstanding work.
    for ui, prev in (claims or {}).items():
        if ui not in free:
            continue
        key = (prev[0], _task_cell(prev))
        if key in live and key not in taken:
            assignment[ui] = live[key]
            taken.add(key)
            free.discard(ui)

    # 2. Fill the rest by a global score, strongly preferring d=0 for non-urgent tasks.
    # Promote "plant" to Tier 1 in two cases:
    #   (a) Classic endgame (day >= 20): expired melon/straw tiles free up fast
    #   (b) Land-expansion window (days 7-13): NE unlocks day 7, SW day 10.
    #       Only promote when >=15 plant tasks queued (genuine expansion, not routine).
    free_tile_count = sum(1 for t in tasks if t[0] == "plant")
    expansion_window = 7 <= day <= 13 and free_tile_count >= 15
    endgame = day >= 20 or expansion_window
    feed_cells = feed_cells or set()
    have_wheat = any(int((invs[ui] if ui < len(invs) else {}).get("WHEAT", 0)) > 0 for ui in free)
    pairs = []

    for ui in free:
        for t in tasks:
            key = (t[0], _task_cell(t))
            if key in taken:
                continue
            tier = TASK_TIER.get(t[0], 3)
            if endgame and t[0] == "plant":
                tier = 1
            cell = _task_cell(t)
            if cell is None:
                continue
            inv = invs[ui] if ui < len(invs) else {}
            carrying = int(inv.get("WHEAT", 0)) > 0
            if t[0] == "fertilize" and int(inv.get("FERTILIZER", 0)) <= 0:
                continue
            hungry = t[0] in ("service", "service_soon") and cell in feed_cells
            if hungry and have_wheat and not carrying:
                continue

            d = manhattan(positions[ui], cell)
            if hungry and carrying:
                d -= 3

            score = tier * 1000 + d
            if d == 0 and tier > 0:
                score -= 1500

            pairs.append((score, ui, key, t))

    pairs.sort(key=lambda p: (p[0], p[1]))
    for score, ui, key, t in pairs:
        if ui not in free or key in taken:
            continue
        assignment[ui] = t
        taken.add(key)
        free.discard(ui)
    return assignment
''',
        "_assign_tasks: promote plant to Tier 1 during land-expansion window (days 7-13, >=15 plant tasks) not just day>=20.",
        ["routing", "_assign_tasks", "expansion_plant_v2"],
        4000.0,
    ),
    # ── T2-R: ST-5 — strawberry always in early-hour sells ───────────────────
    # Replay evidence (43 live games): 21/43 games have strawberry unsold at EOD
    # day 21 (avg 7.7 units). The R2 block throttles sells to 3 orders at hours
    # 0-1. When 4+ products need selling simultaneously, strawberry (the first in
    # SELL_PRODUCE, highest value at $120 base) is sometimes cut.
    # Fix: at hours 0-1, always include STRAWBERRY and MELON sells in the first
    # 2 slots before the 3-order cap. This ensures high-value items clear every
    # turn regardless of queue order pressure.
    (
        "R2",
        '''\
    # ── R2: sell first so the rest of the turn is funded ─────────────────────
    # Taper the wheat buffer in the final days: animals don\'t need feed after
    # the game ends, so release held wheat as we approach the last turn.
    days_left = total_days - day
    effective_buffer = max(0, min(2, days_left - 1))
    hold = {"WHEAT": feed_hold(fed_animals, int(shed.get("WHEAT", 0)),
                               days_buffer=effective_buffer)}
    sells = plan_sells(shed, minv, day, hour, total_days, hold)
    # At hours 0-1, ensure STRAWBERRY and MELON are always sold (highest value).
    # Other products fill up to 3 slots; from hour 2 all sells fire normally.
    if hour >= 2:
        orders += sells
    else:
        # Priority sells: STRAWBERRY and MELON first (up to 2 slots), then
        # fill remaining slot(s) from the rest of the sell list.
        priority = [o for o in sells if o[1] in ("STRAWBERRY", "MELON")]
        others   = [o for o in sells if o[1] not in ("STRAWBERRY", "MELON")]
        orders += (priority + others)[:3]
    for o in orders:
        inv = int(minv.get(o[1], 10000))
        rev, _ = sell_revenue(o[1], inv, o[2])
        money_left += rev

''',
        "R2 sell priority: STRAWBERRY+MELON always in first 2 early-hour sell slots. Replay: 21/43 games unsold EOD day 21.",
        ["market", "R2", "sell_priority_straw"],
        1500.0,
    ),
    # ── T2-S: ST-6 — day-0 place_animal boost via _build_tasks ───────────────
    # Replay evidence: only 3/4 purchased animals are placed by EOD day 0.
    # place_animal is Tier 1, competing with plant (also Tier 1). On day 0 the
    # 5-hand crew plants 11 MELON + 7 WHEAT seeds, leaving one animal in shed.
    # Fix: on day 0, emit place_animal tasks before plant tasks in the task list.
    # Since sticky-claim matching is order-stable, earlier tasks get first pick
    # of nearby workers. This is a task-ordering fix, not a tier change.
    # Implementation: in _build_tasks, insert a day==0 guard that moves all
    # place_animal tasks to the top of the task list.
    (
        "_build_tasks",
        '''\
def _build_tasks(scan, me, private, free_cells, day, total_days, hour=0):
    tasks = []
    # One "service" visit per occupied pasture bundles HARVEST + FEED +
    # COLLECT_FERTILIZER + CARE, so a worker pays the walk once and then works
    # the tile for up to four turns instead of being pulled away between each.
    for cell in scan["service"]:
        tasks.append(("service", cell))
    for cell in scan["service_soon"]:
        tasks.append(("service_soon", cell))
    for cell in scan["water"]:
        tasks.append(("water", cell))
    for cell in scan["water_soon"]:
        tasks.append(("water_soon", cell))
    for cell in scan["harvest_crop"]:
        tasks.append(("harvest_crop", cell))

    # Place animals waiting in the shed into empty pastures.
    shed = private.get("shed") or {}
    invs = private.get("inventories") or []
    unplaced = {}
    for a in ("COW", "SHEEP", "GOOSE"):
        n = int(shed.get(a, 0)) + sum(int(i.get(a, 0)) for i in invs)
        if n > 0:
            unplaced[a] = n
    place_tasks = []
    if unplaced:
        for (cell, kind) in scan["structures_empty"]:
            if kind not in ("PASTURE", "COOP"):
                continue
            for a in list(unplaced):
                if unplaced[a] > 0:
                    req_kind = ANIMAL_SPECS[a]["structure"]
                    if kind == req_kind:
                        place_tasks.append(("place_animal", (a, cell)))
                        unplaced[a] -= 1
                        break
    # On day 0: insert place_animal tasks at the front so they get first worker
    # picks before planting — replay shows 1 animal stranded overnight on day 0.
    if day == 0:
        tasks = place_tasks + tasks
    else:
        tasks.extend(place_tasks)

    # Build structures up to the blueprint cap -- never pave over crop land.
    have_pastures = _count_structures(me, "PASTURE")
    deficit_pasture = target_pastures(day) - have_pastures
    if deficit_pasture > 0 and day < total_days - 8:
        for cell in free_cells[:deficit_pasture]:
            tasks.append(("build_pasture", cell))
        free_cells = free_cells[deficit_pasture:]

    have_coops = _count_structures(me, "COOP")
    deficit_coop = target_coops(day) - have_coops
    if deficit_coop > 0 and day < total_days - 8:
        for cell in free_cells[:deficit_coop]:
            tasks.append(("build_coop", cell))
        free_cells = free_cells[deficit_coop:]

    # Sow the remaining free land.  A plant counts its planting day as unwatered
    # already, so anything sown too late to also be watered today dies tonight.
    # In the endgame (< 5 days left) we accept late-day plantings since the tile
    # otherwise just sits empty and we\'ll water it the same turn or next turn.
    plant_cutoff = 22 if (total_days - day) < 5 else 20
    if hour <= plant_cutoff:
        seeds = dict(private.get("seeds") or {})
        planted = _crop_census(me)
        for cell in free_cells:
            crop = _plant_choice(day, total_days, planted, seeds)
            if crop is None:
                break
            seeds[crop] = int(seeds.get(crop, 0)) - 1
            planted[crop] = planted.get(crop, 0) + 1
            tasks.append(("plant", (crop, cell)))

    for cell in scan["fertilize"]:
        tasks.append(("fertilize", cell))
    for cell in scan["weeds"]:
        tasks.append(("weed", cell))
    return tasks
''',
        "_build_tasks day-0 place_animal priority: insert place_animal tasks at front on day 0 so animals are placed before planting begins.",
        ["routing", "_build_tasks", "place_animal_day0"],
        500.0,
    ),
    # ── T2-T: _assign_tasks — endgame plant-promotion with free-tile guard ────
    # Prior attempts (expansion_plant, expansion_plant_v2) failed because the
    # always-on or task-count trigger fired mid-game and starved animal feeding.
    # This variant fires ONLY when BOTH conditions hold:
    #   (a) day >= 7 (post-NE unlock) AND
    #   (b) at least 10 plant tasks currently queued (genuine idle land).
    # Outside this window, endgame = day >= 20 as before.
    # Key difference from prior attempts: the guard is conjunctive (day AND tasks)
    # not disjunctive, so it won't activate on a fully-planted farm.
    (
        "_assign_tasks",
        '''\
def _assign_tasks(positions, tasks, invs, board, claims=None, feed_cells=None,
                  day=0, total_days=30):
    """Tier-by-tier greedy nearest-pair matching, with sticky claims.

    Recomputing assignments from scratch every turn made workers oscillate:
    a unit walking to a tile would be swapped onto another job the moment a
    colleague drifted closer, so nobody ever arrived.  A claim is therefore
    kept until the job it points at disappears from the task list.
    """
    assignment = {}
    taken = set()
    free = set(range(len(positions)))

    live = {}
    for t in tasks:
        live.setdefault((t[0], _task_cell(t)), t)

    # 1. Honour existing claims that still correspond to outstanding work.
    for ui, prev in (claims or {}).items():
        if ui not in free:
            continue
        key = (prev[0], _task_cell(prev))
        if key in live and key not in taken:
            assignment[ui] = live[key]
            taken.add(key)
            free.discard(ui)

    # 2. Fill the rest by a global score, strongly preferring d=0 for non-urgent tasks.
    # Promote "plant" to Tier 1 when BOTH conditions hold:
    #   (a) day >= 7 — post-NE land unlock; new tiles need sowing
    #   (b) at least 10 plant tasks in queue — farm genuinely has idle land
    # The conjunctive guard prevents mid-game activation on a fully-sown farm.
    # Classic endgame (day >= 20) also promotes plant as before.
    n_plant_tasks = sum(1 for t in tasks if t[0] == "plant")
    endgame = day >= 20 or (day >= 7 and n_plant_tasks > 10)
    feed_cells = feed_cells or set()
    have_wheat = any(int((invs[ui] if ui < len(invs) else {}).get("WHEAT", 0)) > 0 for ui in free)
    pairs = []

    for ui in free:
        for t in tasks:
            key = (t[0], _task_cell(t))
            if key in taken:
                continue
            tier = TASK_TIER.get(t[0], 3)
            if endgame and t[0] == "plant":
                tier = 1
            cell = _task_cell(t)
            if cell is None:
                continue
            inv = invs[ui] if ui < len(invs) else {}
            carrying = int(inv.get("WHEAT", 0)) > 0
            if t[0] == "fertilize" and int(inv.get("FERTILIZER", 0)) <= 0:
                continue
            hungry = t[0] in ("service", "service_soon") and cell in feed_cells
            if hungry and have_wheat and not carrying:
                continue

            d = manhattan(positions[ui], cell)
            if hungry and carrying:
                d -= 3

            score = tier * 1000 + d
            if d == 0 and tier > 0:
                score -= 1500

            pairs.append((score, ui, key, t))

    pairs.sort(key=lambda p: (p[0], p[1]))
    for score, ui, key, t in pairs:
        if ui not in free or key in taken:
            continue
        assignment[ui] = t
        taken.add(key)
        free.discard(ui)
    return assignment
''',
        "_assign_tasks: promote plant to Tier 1 when day>=7 AND n_plant_tasks>10 (both conditions conjunctive). Prior attempts failed because they were always-on; this guard only fires on genuinely idle land.",
        ["assign_tasks_endgame", "plant_promotion", "free_tile_guard"],
        2000.0,
    ),
    # ── T2-U: R2 early-hour sell throttle width 3→5 ──────────────────────────
    # Current: `orders += sells if hour >= 2 else sells[:3]`
    # With 9 sellable products the queue can have 4–9 items. At hours 0-1 only 3
    # fire. Increasing the cap to 5 lets MILK, WOOL, FERTILIZER also sell at
    # hours 0–1. Prior experiments changed ORDERING (sell_priority_straw) or
    # removed the cap entirely (sell_gate). This narrows to width=5 only.
    (
        "R2",
        '''\
    # ── R2: sell first so the rest of the turn is funded ─────────────────────
    # Taper the wheat buffer in the final days: animals don't need feed after
    # the game ends, so release held wheat as we approach the last turn.
    days_left = total_days - day
    effective_buffer = max(0, min(2, days_left - 1))
    hold = {"WHEAT": feed_hold(fed_animals, int(shed.get("WHEAT", 0)),
                               days_buffer=effective_buffer)}
    sells = plan_sells(shed, minv, day, hour, total_days, hold)
    # At hours 0-1 allow up to 5 sell orders (up from 3) so MILK+WOOL+FERTILIZER
    # can clear alongside STRAWBERRY/MELON; from hour 2 all sells fire normally.
    orders += sells if hour >= 2 else sells[:5]
    for o in orders:
        inv = int(minv.get(o[1], 10000))
        rev, _ = sell_revenue(o[1], inv, o[2])
        money_left += rev

''',
        "R2 early-hour sell throttle width 3→5: lets MILK/WOOL/FERTILIZER also sell at hours 0-1 without flooding the queue.",
        ["sell_throttle_fix", "early_hour_sell", "high_value_first"],
        600.0,
    ),
    # ── T2-V: _scan fertilize — phase-gate to near-yield tiles only ──────────
    # Currently ALL ongoing-crop tiles with `fertilized_until_day < today` enter
    # the fertilize queue. That's up to 35 strawberry tiles every day, most
    # mid-cycle (yield not due for another 1-2 days). The large list competes
    # with Tier-1 service/harvest tasks in _assign_tasks scoring.
    # Fix: only queue tiles where the next yield is within 3 days of this turn
    # (i.e. the fertilize application will actually pay off before end of game
    # AND before the current crop cycle ends).
    # Proxy: days since planted mod yield_interval ≤ 3 OR (total_days - day) ≤ 5.
    (
        "_scan",
        '''\
def _scan(me, day, total_days=30):
    out = dict(water=[], water_soon=[], service=[], service_soon=[],
               harvest_crop=[], weeds=[], structures_empty=[], fertilize=[],
               feed=[])
    tiles = me.get("tiles") or []
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            if not isinstance(t, dict):
                continue
            kind = t.get("kind")
            if kind == "PLANT":
                if not t.get("watered_today"):
                    if _water_urgent(t, day):
                        out["water"].append((x, y))
                    else:
                        out["water_soon"].append((x, y))
                if _crop_harvestable(t, day, total_days):
                    out["harvest_crop"].append((x, y))
                # Fertilizer gate: only queue tiles that are close to their next
                # yield (within 3 days) OR near end-of-game.  This keeps the list
                # short so _assign_tasks does not over-allocate workers to fertilize
                # at the expense of harvest/care tasks.
                spec = CROP_SPECS.get(t.get("crop"))
                if (spec and spec["ongoing"]
                        and int(t.get("fertilized_until_day", -1)) < day
                        and day - int(t.get("planted_day", day)) >= spec["first"] - 2):
                    days_left = total_days - day
                    cycle = spec.get("interval", 2)
                    days_since_first = day - int(t.get("planted_day", day)) - spec["first"]
                    phase = days_since_first % cycle if days_since_first >= 0 else 0
                    # Queue only if within 3 steps of next yield OR in final 5 days
                    if days_left <= 5 or (cycle - phase) <= 3:
                        out["fertilize"].append((x, y))
            elif kind in ("PASTURE", "COOP"):
                if t.get("animal"):
                    if not t.get("fed_today"):
                        out["feed"].append((x, y))
                    if _animal_pending(t) is not None:
                        if not t.get("fed_today"):
                            out["service"].append((x, y))
                        else:
                            out["service_soon"].append((x, y))
                else:
                    out["structures_empty"].append(((x, y), kind))
            elif kind == "WEED":
                out["weeds"].append((x, y))
    return out
''',
        "_scan fertilize gate: only queue fertilize tasks within 3 days of next yield or in final 5 days, reducing list size from ~35 to ~5-10 daily to free workers for harvest/care.",
        ["scan_fertilize_guard", "fert_lookahead", "ongoing_crop_fert"],
        1500.0,
    ),
    # NOTE: T2-W (R1 opening v2, tags=['opening_r1_v2','healthstone_blueprint','day0_animals'])
    # was tested as EXP-20260816-09 and rejected at Stage 1 with delta=-107k.
    # Reducing to 1 COW + 4 SHEEP + 8 MELON collapsed the early-game seed economy.
    # Do not retest this approach — the current 2 COW + 2 SHEEP + 11 MELON opening is optimal.
]


def _tier2_key(block_name: str, tags: List[str]) -> str:
    """Stable unique key for a Tier 2 mutation, used by tried_params."""
    # Use block_name + last tag for uniqueness across variants on same block
    suffix = tags[-1] if tags else block_name
    return f"t2_{block_name}_{suffix}"


def _tier2_tags_tried(tags: List[str], experiments: list) -> bool:
    """Return True if any experiment has exactly these tags (Tier 2 tag-based dedup).

    Used as a fallback for old records where diff_summary is truncated and
    _already_tried cannot reliably compare the full mutation JSON.
    """
    tags_set = set(tags)
    for r in experiments:
        if set(r.get("tags") or []) == tags_set:
            return True
    return False


def _all_tier2_candidates(
    tried_params: set,
    experiments: list,
) -> List[Dict[str, Any]]:
    """Generate all untried Tier 2 block-replacement mutations."""
    candidates = []
    for block_name, new_source, rationale, tags, expected_delta in _TIER2_MUTATIONS:
        key = _tier2_key(block_name, tags)
        if key in tried_params:
            continue
        mutation = {"block_name": block_name, "new_block_source": new_source}
        # Primary: hash-based dedup (new-style records with _hash field in diff_summary)
        # Fallback: tag-set dedup (for old records where diff_summary is truncated)
        if _already_tried(mutation, experiments) or _tier2_tags_tried(tags, experiments):
            continue
        candidates.append(build_hypothesis(
            tier=2,
            rationale=rationale,
            bottleneck="BLOCK_REPLACEMENT",
            target_code=f"policy.{block_name}",
            mutation=mutation,
            expected_delta=expected_delta,
            tags=tags,
        ))
    return candidates


def _all_tier3_candidates(
    tried_params: set,
    experiments: list,
) -> List[Dict[str, Any]]:
    """Generate all untried Tier 3 task-priority mutations."""
    # Current TASK_TIER values from policy.py
    current_tiers = {
        "service": 0, "water": 0, "harvest_crop": 1, "place_animal": 1,
        "service_soon": 1, "build_pasture": 2, "plant": 2, "fertilize": 2,
        "water_soon": 3, "weed": 4, "dropoff": 4,
    }
    # Only try moves that the architecture doc explicitly considers meaningful
    priority_candidates = [
        # (task_name, new_tier, rationale)
        ("water_soon",    2, "Elevate water_soon: 3->2 to prevent weed deaths one step earlier."),
        ("plant",         1, "Elevate plant: 2->1 so new tiles are sown before service_soon busywork."),
        ("build_pasture", 1, "Elevate build_pasture: 2->1 to build animal capacity faster early-game."),
        ("weed",          3, "Elevate weed: 4->3 to clear weeds before they spread."),
        ("dropoff",       3, "Elevate dropoff: 4->3 so full workers bank produce sooner."),
        # Replay evidence: 4-7 fertilizer units idle at h=12 every day from day 15 in 43/43
        # live games. fertilize is currently Tier 1, same as service_soon — but service_soon
        # has 14 animal tiles dominating the task list and always wins the worker allocation.
        # Moving fertilize to Tier 0 guarantees workers apply fertilizer first each turn.
        ("fertilize",     0, "Elevate fertilize: 1->0 — replay shows 4-7 fert units idle at h=12 daily from day 15; Tier 0 ensures application before service_soon monopolises all workers."),
    ]

    candidates = []
    for task, new_tier, rationale in priority_candidates:
        key = f"{task}_tier"
        if key in tried_params:
            continue
        mutation = {"task_name": task, "new_tier": new_tier}
        if _already_tried(mutation, experiments):
            continue
        current_tier = current_tiers.get(task, 2)
        candidates.append(build_hypothesis(
            tier=3,
            rationale=rationale,
            bottleneck="TASK_PRIORITY",
            target_code="policy.TASK_TIER",
            mutation=mutation,
            expected_delta=300.0,
            tags=["task_priority", task],
        ))

    return candidates


# ---------------------------------------------------------------------------
# Telemetry-driven proposals
# ---------------------------------------------------------------------------

def _propose_from_telemetry(
    report: BottleneckReport,
    tried_params: set,
    experiments: list,
) -> List[Dict[str, Any]]:
    """Generate candidate Tier 1/3 hypotheses directly from telemetry data."""
    proposals = []

    # High walk rate → elevate fertilize task priority (tier 3)
    if report.unit_efficiency.walk_pct > 0.55 and "fertilize_tier" not in tried_params:
        mutation = {"task_name": "fertilize", "new_tier": 1}
        if not _already_tried(mutation, experiments):
            proposals.append(build_hypothesis(
                tier=3,
                rationale=(
                    f"Walk rate is {report.unit_efficiency.walk_pct:.0%}. "
                    "Lowering fertilize task tier from 2->1 keeps fertilizer workers "
                    "closer to productive tiles and reduces cross-farm walks."
                ),
                bottleneck="HIGH_WALK_RATE",
                target_code="policy.TASK_TIER",
                mutation=mutation,
                expected_delta=500.0,
                tags=["walk_rate", "task_priority", "fertilize"],
            ))

    # Wheat starvation → raise CASH_FLOOR
    if report.market.wheat_zero_events > 5 and "CASH_FLOOR" not in tried_params:
        mutation = {"param_name": "CASH_FLOOR", "new_value": 400}
        if not _already_tried(mutation, experiments):
            proposals.append(build_hypothesis(
                tier=1,
                rationale=(
                    f"Wheat starvation occurred {report.market.wheat_zero_events} times. "
                    "Raising CASH_FLOOR by 50 coins keeps more buying power for wheat restocking."
                ),
                bottleneck="WHEAT_STARVATION",
                target_code="policy.CASH_FLOOR",
                mutation=mutation,
                expected_delta=300.0,
                tags=["wheat", "cash_floor", "animal_feed"],
            ))

    return proposals


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_hypothesis(
    report: Optional[BottleneckReport] = None,
    ledger: Path = DEFAULT_LEDGER,
    tried_params: Optional[set] = None,
) -> Optional[Dict[str, Any]]:
    """Generate one novel, testable hypothesis.

    Priority:
      1. Telemetry-driven proposals (if report provided)
      2. Composite (Tier 0) coupled mutations — highest expected delta
      3. Tier 2 block-replacement candidates
      4. Tier 3 task-priority candidates
      5. Tier 1 categorical + numeric grid sweep

    Returns None if no novel hypothesis can be generated.
    """
    if tried_params is None:
        tried_params = set()

    experiments = load_memory(ledger)

    # 1. Telemetry proposals
    if report is not None:
        telem = _propose_from_telemetry(report, tried_params, experiments)
        if telem:
            return max(telem, key=lambda h: h["expected_delta"])

    # 2. Composite (Tier 0) — coupled multi-block mutations, highest priority
    t0 = _all_composite_candidates(tried_params, experiments)
    if t0:
        return max(t0, key=lambda h: h["expected_delta"])

    # 3. Tier 2 block-replacement candidates (highest expected delta)
    t2 = _all_tier2_candidates(tried_params, experiments)
    if t2:
        # Return highest expected_delta first
        return max(t2, key=lambda h: h["expected_delta"])

    # 3. Tier 3 task-priority candidates
    t3 = _all_tier3_candidates(tried_params, experiments)
    if t3:
        return t3[0]

    # 4 + 5. Tier 1: categoricals first, then numeric grid
    t1 = _all_tier1_candidates(tried_params, experiments)
    if not t1:
        return None

    # Sort: categoricals first, then by |delta from current| ascending
    # (test nearby values before large jumps)
    def _sort_key(h: Dict[str, Any]) -> Tuple[int, float]:
        bottleneck = h["bottleneck"]
        order = 0 if bottleneck == "CATEGORICAL_SWEEP" else 1
        mut = h["mutation"]
        param = mut.get("param_name", "")
        try:
            current = _current_value(param)
            new_val = mut.get("new_value")
            if isinstance(current, (int, float)) and isinstance(new_val, (int, float)):
                dist = abs(new_val - current)
            else:
                dist = 0.0
        except Exception:
            dist = 0.0
        return (order, dist)

    t1.sort(key=_sort_key)
    return t1[0]
