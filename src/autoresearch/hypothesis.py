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
