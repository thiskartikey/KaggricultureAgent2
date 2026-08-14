"""
Canonical dataclasses for Kaggriculture replay analysis.

Each CanonicalTurn represents the full state-action record for one player
at one step of a replay episode.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------

CROP_TYPES: List[str] = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
ANIMAL_TYPES: List[str] = ["COW", "SHEEP", "GOOSE"]
STRUCTURE_TYPES: List[str] = ["PASTURE", "COOP"]


# ---------------------------------------------------------------------------
# Sub-structures
# ---------------------------------------------------------------------------

@dataclass
class ActionsSummary:
    """Aggregated counts of each operation type from a single step's action."""
    num_plant: int = 0
    num_water: int = 0
    num_harvest: int = 0
    num_care: int = 0
    num_feed: int = 0
    num_build: int = 0   # BUILD_PASTURE + BUILD_COOP
    num_dig: int = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass
class CanonicalTurn:
    """
    One row in the canonical dataset: the state seen by one player at one step,
    paired with the action they took at that step.
    """
    # Episode context
    episode_id: str = ""
    step: int = 0
    day: int = 0
    hour: int = 0

    # Player identity
    player_name: str = ""
    player_index: int = 0
    opponent_name: str = ""

    # Farm state (from farms[player_index])
    money: float = 0.0
    unlocked_quadrants: List[str] = field(default_factory=list)
    num_hands: int = 0

    # Tile-derived counts
    crop_counts: Dict[str, int] = field(default_factory=dict)
    animal_counts: Dict[str, int] = field(default_factory=dict)
    structures: Dict[str, int] = field(default_factory=dict)

    # Action summary for this step
    actions_summary: Dict[str, int] = field(default_factory=dict)

    # Market interaction
    market_orders: List[List[Any]] = field(default_factory=list)
    market_prices: Dict[str, float] = field(default_factory=dict)
    market_inventory: Dict[str, int] = field(default_factory=dict)

    # Town state
    town_shops: List[str] = field(default_factory=list)

    # Shed / seed private state
    shed: Dict[str, int] = field(default_factory=dict)
    seeds: Dict[str, int] = field(default_factory=dict)

    # Outcome (from final step / episode metadata)
    final_score: float = 0.0
    final_reward: float = 0.0
    corpus_player: str = ""
    won: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlayerSummary:
    """
    Aggregated strategy profile for one player across multiple episodes.
    Populated by statistics.py; stored in data/processed/player_summaries.json.
    """
    player_name: str = ""
    num_episodes: int = 0
    win_rate: float = 0.0
    mean_final_score: float = 0.0
    median_final_score: float = 0.0
    std_final_score: float = 0.0

    # Expansion milestones (median day across episodes)
    median_day_2nd_quadrant: Optional[float] = None
    median_day_3rd_quadrant: Optional[float] = None
    pct_unlock_4th_quadrant: float = 0.0

    # Labour
    mean_crew_size_per_day: Dict[str, float] = field(default_factory=dict)

    # Crop portfolio (total lifetime seeds purchased, summed across episodes, normalised per game)
    mean_seeds_per_game: Dict[str, float] = field(default_factory=dict)

    # Livestock
    mean_cows_day20: float = 0.0
    mean_sheep_day20: float = 0.0
    mean_pastures_day15: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
