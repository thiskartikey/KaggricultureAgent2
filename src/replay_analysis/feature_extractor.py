"""
Feature extractor for Kaggriculture canonical turn records.

Provides:
  - ``vectorize_turn``:  converts a CanonicalTurn into a flat numeric feature vector.
  - ``segment_timeline``: assigns a game-phase label to a day/step value.
  - ``build_feature_matrix``: batch-converts a list of CanonicalTurns into a numpy array.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .schema import CanonicalTurn, CROP_TYPES, ANIMAL_TYPES, STRUCTURE_TYPES

# Re-export constants that callers might need
__all__ = ["vectorize_turn", "segment_timeline", "build_feature_matrix", "FEATURE_NAMES"]

# ---------------------------------------------------------------------------
# Game-phase segmentation
# ---------------------------------------------------------------------------

PHASE_OPENING = "opening"      # Days  0– 6 / Steps   0–167
PHASE_MIDGAME = "midgame"      # Days  7–20 / Steps 168–503
PHASE_ENDGAME = "endgame"      # Days 21–29 / Steps 504–719


def segment_timeline(day: int) -> str:
    """Return the game-phase label for a given day number."""
    if day <= 6:
        return PHASE_OPENING
    elif day <= 20:
        return PHASE_MIDGAME
    return PHASE_ENDGAME


# ---------------------------------------------------------------------------
# Feature vector definition
# ---------------------------------------------------------------------------

# Ordered list of feature names produced by vectorize_turn.
# Keep this stable — downstream models depend on index positions.
FEATURE_NAMES: List[str] = (
    ["step", "day", "hour", "player_index", "money", "num_hands"]
    + [f"quad_{q}" for q in ["NW", "NE", "SW", "SE"]]
    + [f"crop_{c}" for c in CROP_TYPES]
    + [f"animal_{a}" for a in ANIMAL_TYPES]
    + [f"struct_{s}" for s in STRUCTURE_TYPES]
    + ["total_crops", "total_animals", "total_structures"]
    + ["num_plant", "num_water", "num_harvest", "num_care", "num_feed", "num_build", "num_dig"]
    + ["num_market_orders", "num_hire_orders", "num_buy_seed_orders", "num_buy_animal_orders",
       "num_sell_orders", "num_buy_product_orders"]
    + [f"price_{item}" for item in ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
                                     "MILK", "WOOL", "EGG", "FERTILIZER"]]
    + ["num_town_shops"]
    + [f"shed_{item}" for item in ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
                                    "MILK", "WOOL", "EGG", "FERTILIZER", "COW", "SHEEP", "GOOSE"]]
    + [f"seed_{c}" for c in CROP_TYPES]
    + ["final_score", "won"]
)


def vectorize_turn(turn: CanonicalTurn) -> List[float]:
    """
    Convert a CanonicalTurn into a flat, ordered numeric feature vector.

    All values are guaranteed to be plain Python floats (0.0 for missing data).
    The order matches ``FEATURE_NAMES``.
    """
    v: List[float] = []

    # Scalar context
    v += [float(turn.step), float(turn.day), float(turn.hour), float(turn.player_index),
          float(turn.money), float(turn.num_hands)]

    # Quadrant flags
    quads = set(turn.unlocked_quadrants or [])
    v += [1.0 if q in quads else 0.0 for q in ["NW", "NE", "SW", "SE"]]

    # Crops
    cc = turn.crop_counts or {}
    v += [float(cc.get(c, 0)) for c in CROP_TYPES]

    # Animals
    ac = turn.animal_counts or {}
    v += [float(ac.get(a, 0)) for a in ANIMAL_TYPES]

    # Structures
    sc = turn.structures or {}
    v += [float(sc.get(s, 0)) for s in STRUCTURE_TYPES]

    # Totals
    total_crops = float(sum(cc.get(c, 0) for c in CROP_TYPES))
    total_animals = float(sum(ac.get(a, 0) for a in ANIMAL_TYPES))
    total_structures = float(sum(sc.get(s, 0) for s in STRUCTURE_TYPES))
    v += [total_crops, total_animals, total_structures]

    # Action summary
    asumm = turn.actions_summary or {}
    v += [float(asumm.get(k, 0)) for k in
          ["num_plant", "num_water", "num_harvest", "num_care", "num_feed", "num_build", "num_dig"]]

    # Market order counts
    orders = turn.market_orders or []
    num_hire = sum(1 for o in orders if o and o[0] == "HIRE")
    num_buy_seed = sum(1 for o in orders if o and o[0] == "BUY_SEED")
    num_buy_animal = sum(1 for o in orders if o and o[0] == "BUY_ANIMAL")
    num_sell = sum(1 for o in orders if o and o[0] == "SELL")
    num_buy_product = sum(1 for o in orders if o and o[0] == "BUY_PRODUCT")
    v += [float(len(orders)), float(num_hire), float(num_buy_seed),
          float(num_buy_animal), float(num_sell), float(num_buy_product)]

    # Market prices
    prices = turn.market_prices or {}
    v += [float(prices.get(item, 0.0)) for item in
          ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "MILK", "WOOL", "EGG", "FERTILIZER"]]

    # Town
    v += [float(len(turn.town_shops or []))]

    # Shed contents
    shed = turn.shed or {}
    v += [float(shed.get(item, 0)) for item in
          ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "MILK", "WOOL", "EGG",
           "FERTILIZER", "COW", "SHEEP", "GOOSE"]]

    # Seeds
    seeds = turn.seeds or {}
    v += [float(seeds.get(c, 0)) for c in CROP_TYPES]

    # Outcome
    v += [float(turn.final_score), 1.0 if turn.won else 0.0]

    assert len(v) == len(FEATURE_NAMES), f"Vector length mismatch: {len(v)} vs {len(FEATURE_NAMES)}"
    return v


def build_feature_matrix(turns: List[CanonicalTurn]):
    """
    Convert a list of CanonicalTurn objects into a 2-D list of floats
    (one sub-list per turn).  Returns (matrix, FEATURE_NAMES).

    Pass the result to numpy.array() or pandas.DataFrame() as needed.
    """
    matrix = [vectorize_turn(t) for t in turns]
    return matrix, FEATURE_NAMES
