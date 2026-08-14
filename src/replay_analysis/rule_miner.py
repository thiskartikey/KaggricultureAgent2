"""
Decision rule miner for Kaggriculture replay analysis.

Extracts human-interpretable IF-THEN rules that characterise
the behaviour of top players from the canonical turn dataset.

Rules are frequency / precision-based: a rule is:
  - CONDITION: a conjunction of threshold predicates on turn features
  - ACTION:    a binary outcome derived from that turn (e.g. hired today, sold today)
  - SUPPORT:   fraction of turns where CONDITION is true
  - PRECISION: fraction of those turns where ACTION is also true among winning episodes

Usage (standalone):
    python -m src.replay_analysis.rule_miner \
        --turns data/processed/canonical_turns.csv \
        --output data/processed/decision_rules.json \
        --min-support 0.05 \
        --min-precision 0.70
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

log = logging.getLogger("rule_miner")


# ---------------------------------------------------------------------------
# Rule dataclass
# ---------------------------------------------------------------------------

@dataclass
class DecisionRule:
    """A single extracted conditional rule with evidence metrics."""
    rule_id: str
    category: str
    description: str
    condition_description: str
    action_description: str

    # Quantitative evidence
    support: float          # P(condition)
    precision: float        # P(action | condition, won)
    n_total: int            # Total turns satisfying condition
    n_won: int              # Turns satisfying condition in winning episodes

    # Source context
    player_names: List[str]
    example_episodes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Predicate helpers
# ---------------------------------------------------------------------------

def _int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _parse_json(val: Any) -> Any:
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return {}
    return val or {}


def _num_quadrants(row: Dict) -> int:
    quads = _parse_json(row.get("unlocked_quadrants", "[]"))
    return len(quads) if isinstance(quads, list) else 0


def _num_market_orders(row: Dict) -> int:
    orders = _parse_json(row.get("market_orders", "[]"))
    return len(orders) if isinstance(orders, list) else 0


def _orders_of_type(row: Dict, order_type: str) -> int:
    orders = _parse_json(row.get("market_orders", "[]"))
    if not isinstance(orders, list):
        return 0
    return sum(1 for o in orders if isinstance(o, list) and o and o[0] == order_type)


def _struct_count(row: Dict, kind: str) -> int:
    structs = _parse_json(row.get("structures", "{}"))
    return int(structs.get(kind, 0)) if isinstance(structs, dict) else 0


def _animal_count(row: Dict, animal: str) -> int:
    animals = _parse_json(row.get("animal_counts", "{}"))
    return int(animals.get(animal, 0)) if isinstance(animals, dict) else 0


def _crop_count(row: Dict, crop: str) -> int:
    crops = _parse_json(row.get("crop_counts", "{}"))
    return int(crops.get(crop, 0)) if isinstance(crops, dict) else 0


def _action_count(row: Dict, key: str) -> int:
    acts = _parse_json(row.get("actions_summary", "{}"))
    return int(acts.get(key, 0)) if isinstance(acts, dict) else 0


# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

RuleDef = Tuple[str, str, str, str, Callable[[Dict], bool], Callable[[Dict], bool]]

# Each rule-def is (rule_id, category, description, condition_desc, action_desc, condition_fn, action_fn)
RULE_DEFINITIONS: List[Tuple[str, str, str, str, str, Callable, Callable]] = [
    (
        "RULE-OPEN-001",
        "Opening / Hiring",
        "Hire on Day 0",
        "day == 0",
        "hired at least 1 worker (HIRE order present)",
        lambda r: _int(r.get("day")) == 0,
        lambda r: _orders_of_type(r, "HIRE") >= 1,
    ),
    (
        "RULE-OPEN-002",
        "Opening / Seeds",
        "Buy Strawberry seeds on Day 0",
        "day == 0",
        "bought STRAWBERRY seeds",
        lambda r: _int(r.get("day")) == 0,
        lambda r: any(
            isinstance(o, list) and len(o) >= 2 and o[0] == "BUY_SEED" and o[1] == "STRAWBERRY"
            for o in (_parse_json(r.get("market_orders", "[]")) or [])
        ),
    ),
    (
        "RULE-EXPAND-001",
        "Land Expansion",
        "Unlock 2nd quadrant by Day 7",
        "day <= 7",
        "at least 2 quadrants unlocked",
        lambda r: _int(r.get("day")) <= 7,
        lambda r: _num_quadrants(r) >= 2,
    ),
    (
        "RULE-EXPAND-002",
        "Land Expansion",
        "Unlock 3rd quadrant by Day 11",
        "day <= 11",
        "at least 3 quadrants unlocked",
        lambda r: _int(r.get("day")) <= 11,
        lambda r: _num_quadrants(r) >= 3,
    ),
    (
        "RULE-LIVESTOCK-001",
        "Livestock / Husbandry",
        "Build pastures in opening phase",
        "day <= 6",
        "at least 1 PASTURE structure on farm",
        lambda r: _int(r.get("day")) <= 6,
        lambda r: _struct_count(r, "PASTURE") >= 1,
    ),
    (
        "RULE-LIVESTOCK-002",
        "Livestock / Husbandry",
        "Reach 8+ pastures by midgame",
        "day in [7, 15]",
        "at least 8 PASTURE structures on farm",
        lambda r: 7 <= _int(r.get("day")) <= 15,
        lambda r: _struct_count(r, "PASTURE") >= 8,
    ),
    (
        "RULE-LIVESTOCK-003",
        "Livestock / Husbandry",
        "Mixed livestock (Cows AND Sheep) by midgame",
        "day in [7, 20]",
        "at least 1 COW and at least 1 SHEEP",
        lambda r: 7 <= _int(r.get("day")) <= 20,
        lambda r: _animal_count(r, "COW") >= 1 and _animal_count(r, "SHEEP") >= 1,
    ),
    (
        "RULE-CROPS-001",
        "Crop Management",
        "Maintain Strawberry plots in midgame",
        "day in [7, 20]",
        "at least 5 STRAWBERRY tiles growing",
        lambda r: 7 <= _int(r.get("day")) <= 20,
        lambda r: _crop_count(r, "STRAWBERRY") >= 5,
    ),
    (
        "RULE-CROPS-002",
        "Crop Management",
        "Plant Melon in opening",
        "day <= 3",
        "at least 1 MELON tile growing",
        lambda r: _int(r.get("day")) <= 3,
        lambda r: _crop_count(r, "MELON") >= 1,
    ),
    (
        "RULE-ENDGAME-001",
        "Endgame / Liquidation",
        "Stop planting Melon after Day 22",
        "day >= 22",
        "no PLANT actions at this step",
        lambda r: _int(r.get("day")) >= 22,
        lambda r: _action_count(r, "num_plant") == 0,
    ),
    (
        "RULE-LABOUR-001",
        "Labour Scaling",
        "Maintain 10+ hands by Day 7",
        "day >= 7",
        "at least 10 active hands",
        lambda r: _int(r.get("day")) >= 7,
        lambda r: _int(r.get("num_hands")) >= 10,
    ),
    (
        "RULE-CARE-001",
        "Animal Care",
        "CARE actions present during midgame livestock days",
        "day in [7, 20] and at least 1 PASTURE",
        "at least 1 CARE action this step",
        lambda r: (7 <= _int(r.get("day")) <= 20 and _struct_count(r, "PASTURE") >= 1),
        lambda r: _action_count(r, "num_care") >= 1,
    ),
]


# ---------------------------------------------------------------------------
# Mining engine
# ---------------------------------------------------------------------------

def mine_rules(
    turns_csv: Path,
    min_support: float = 0.01,
    min_precision: float = 0.50,
    players_filter: Optional[List[str]] = None,
) -> List[DecisionRule]:
    """
    Mine decision rules from canonical_turns.csv.

    Only considers turns from winning episodes (won == True) for precision
    calculation; support is measured over ALL turns.

    Returns a list of DecisionRule objects with support >= min_support
    and precision >= min_precision.
    """
    all_rows: List[Dict] = []
    with turns_csv.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if players_filter and row.get("player_name") not in players_filter:
                continue
            all_rows.append(row)

    if not all_rows:
        log.warning("No rows found (filter=%s)", players_filter)
        return []

    winning_rows = [r for r in all_rows if r.get("won") in ("True", "true", "1")]
    n_all = len(all_rows)

    results: List[DecisionRule] = []

    for (rule_id, category, description, cond_desc, act_desc, cond_fn, act_fn) in RULE_DEFINITIONS:
        cond_rows = [r for r in all_rows if _safe_call(cond_fn, r)]
        cond_winning = [r for r in winning_rows if _safe_call(cond_fn, r)]
        n_cond = len(cond_rows)

        support = n_cond / n_all if n_all else 0.0
        if support < min_support:
            continue

        n_act_won = sum(1 for r in cond_winning if _safe_call(act_fn, r))
        precision = n_act_won / len(cond_winning) if cond_winning else 0.0
        if precision < min_precision:
            continue

        # Collect player names and example episodes
        player_set: set = set()
        ep_set: set = set()
        for r in cond_rows:
            player_set.add(r.get("player_name", ""))
            ep_set.add(r.get("episode_id", ""))

        results.append(DecisionRule(
            rule_id=rule_id,
            category=category,
            description=description,
            condition_description=cond_desc,
            action_description=act_desc,
            support=round(support, 4),
            precision=round(precision, 4),
            n_total=n_cond,
            n_won=len(cond_winning),
            player_names=sorted(player_set - {""}),
            example_episodes=sorted(ep_set - {""})[:5],
        ))

    results.sort(key=lambda r: (-r.precision, -r.support))
    return results


def _safe_call(fn: Callable, row: Dict) -> bool:
    try:
        return bool(fn(row))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Mine decision rules from canonical_turns.csv"
    )
    parser.add_argument("--turns", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--min-support", type=float, default=0.01)
    parser.add_argument("--min-precision", type=float, default=0.50)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    rules = mine_rules(args.turns, args.min_support, args.min_precision)
    output_data = [r.to_dict() for r in rules]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        json.dump(output_data, fh, indent=2)

    print(f"Mined {len(rules)} rules (support≥{args.min_support}, precision≥{args.min_precision}) → {args.output}")
    for rule in rules:
        print(f"  {rule.rule_id}: support={rule.support:.1%}, precision={rule.precision:.1%}  [{rule.description}]")


if __name__ == "__main__":
    main()
