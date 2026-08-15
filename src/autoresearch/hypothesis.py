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
    mut_str = json.dumps(mutation, sort_keys=True)
    for r in experiments:
        try:
            prev = json.loads(r.get("diff_summary", "{}"))
            if json.dumps(prev, sort_keys=True) == mut_str:
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
    # ── T2-C: endgame crew cutoff one day earlier ─────────────────────────
    (
        "target_hands",
        '''\
def target_hands(day, total_days):
    """Endgame crew cutoff at total_days - 3 instead of - 2.

    On the last 3 days there is almost no planting left; a smaller crew
    reduces the fib(n) hiring cost and frees cash for final sell orders.
    """
    if day <= 0:
        return 5
    if day < 7:
        return 3
    if day < 11:
        return 8
    if day >= total_days - 3:
        return 10
    return 13
''',
        "Endgame crew cutoff: shrink to 10 hands at total_days-3 instead of total_days-2.",
        ["labour", "target_hands", "endgame"],
        300.0,
    ),
]


def _all_tier2_candidates(
    tried_params: set,
    experiments: list,
) -> List[Dict[str, Any]]:
    """Generate all untried Tier 2 block-replacement mutations."""
    candidates = []
    for block_name, new_source, rationale, tags, expected_delta in _TIER2_MUTATIONS:
        key = f"t2_{block_name}_{tags[1] if len(tags) > 1 else block_name}"
        if key in tried_params:
            continue
        mutation = {"block_name": block_name, "new_block_source": new_source}
        if _already_tried(mutation, experiments):
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
      2. Tier 3 task-priority candidates (fast, no game code changes)
      3. Tier 1 categorical parameter sweep (LAND_UNLOCK_DAY, PASTURE ramp)
      4. Tier 1 numeric grid sweep (bidirectional from current value)

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

    # 2. Tier 2 block-replacement candidates (highest expected delta)
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
