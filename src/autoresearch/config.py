"""Parameter definitions and search spaces for KaggriRatchet Tier 1 optimization.

Defines the bounded search space for numeric constants that can be mutated
without touching algorithmic logic.  The LLM and Bayesian optimizer both
draw from this schema when proposing Tier 1 mutations.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple, Union

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

# A search space entry: (default, min, max, step) for numeric params,
# or (default, [choices]) for categorical params.
ParamSpec = Union[
    Tuple[Any, float, float, float],   # default, lo, hi, step
    Tuple[Any, list],                  # default, choices
]

# ---------------------------------------------------------------------------
# Tier 1 parameter search space
# ---------------------------------------------------------------------------

PARAMETERS: Dict[str, ParamSpec] = {
    # Target animal counts
    "TARGET_COW":         (8,   4,  12, 1),
    "TARGET_SHEEP":       (6,   2,  10, 1),

    # Target crop counts — finer steps around proven winners
    "TARGET_STRAWBERRY":  (38, 28,  48, 1),   # winner=38; sweep ±10 at step 1
    "TARGET_MELON":       (9,   6,  14, 1),   # winner=9; stay around 6-14

    # Land unlock earliest days (NE quadrant, SW quadrant)
    # Added (7,9) and (7,10) — SW land one or two days earlier; NE stays day 7
    "LAND_UNLOCK_DAY":    ((7, 11), [(6, 10), (7, 9), (7, 10), (7, 11), (7, 12), (8, 12)]),

    # Cash safety floor — winner=200; sweep down to 175 with step 25
    # (150 was catastrophic so stay above that)
    "CASH_FLOOR":         (200, 175, 450, 25),

    # Pasture ramp schedule: (day_from, target_count) descending
    "TARGET_PASTURE_BY_DAY": (
        ((11, 14), (7, 12), (0, 6)),
        [
            ((11, 14), (7, 12), (0, 6)),
            ((10, 14), (7, 12), (0, 6)),
            ((11, 14), (7, 10), (0, 6)),
            ((10, 14), (6,  9), (0, 6)),
        ],
    ),
}


def get_default(name: str) -> Any:
    """Return the default value for a parameter."""
    spec = PARAMETERS[name]
    return spec[0]


def get_search_space(name: str) -> Dict[str, Any]:
    """Return the search space descriptor for a named parameter.

    Returns a dict with keys:
      type    — "numeric" or "categorical"
      default — default value
      For numeric: lo, hi, step
      For categorical: choices
    """
    spec = PARAMETERS[name]
    default = spec[0]
    if isinstance(spec[1], list):
        return {"type": "categorical", "default": default, "choices": spec[1]}
    _, lo, hi, step = spec
    return {"type": "numeric", "default": default, "lo": lo, "hi": hi, "step": step}


def enumerate_grid(name: str, n_steps: int = 5) -> List[Any]:
    """Return n_steps evenly spaced values across the search space (numeric only).

    For categorical parameters, returns all choices.
    """
    space = get_search_space(name)
    if space["type"] == "categorical":
        return space["choices"]
    lo, hi, step = space["lo"], space["hi"], space["step"]
    values = []
    v = lo
    while v <= hi and len(values) < n_steps:
        # Round to nearest multiple of step
        rounded = round(v / step) * step
        if rounded not in values:
            values.append(rounded)
        v += (hi - lo) / max(1, n_steps - 1)
    return values
