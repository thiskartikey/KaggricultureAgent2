"""Simulation telemetry & bottleneck extractor for KaggriRatchet.

Transforms raw game observation traces into structured diagnostics exposing
*why* the policy lost turns, produce, or score.

Three categories of telemetry:
  1. Unit-turn efficiency  — walking vs. working vs. idling
  2. Market telemetry      — wasted order slots, wheat starvation, unsold produce
  3. Crop lifecycle        — unwatered deaths, missed care bonuses, weed proliferation

Usage:
    trace = []
    # Accumulate (obs_dict, action_dict) pairs during a game
    report = extract_bottlenecks(trace)
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class UnitTurnEfficiency:
    total_turns: int = 0
    walk_turns: int = 0
    work_turns: int = 0
    idle_turns: int = 0
    dropoff_turns: int = 0

    @property
    def walk_pct(self) -> float:
        return self.walk_turns / self.total_turns if self.total_turns else 0.0

    @property
    def work_pct(self) -> float:
        return self.work_turns / self.total_turns if self.total_turns else 0.0

    @property
    def idle_pct(self) -> float:
        return self.idle_turns / self.total_turns if self.total_turns else 0.0


@dataclass
class MarketTelemetry:
    total_order_slots: int = 0
    used_order_slots: int = 0
    wheat_zero_events: int = 0          # turns where shed wheat == 0 and animals present
    unsold_produce_day29: Dict[str, int] = field(default_factory=dict)
    oversell_events: int = 0            # times shed total < 5 after sell orders

    @property
    def wasted_slots(self) -> int:
        return self.total_order_slots - self.used_order_slots

    @property
    def slot_utilisation(self) -> float:
        return self.used_order_slots / self.total_order_slots if self.total_order_slots else 0.0


@dataclass
class CropTelemetry:
    unwatered_deaths: int = 0       # plants that turned to WEED (consecutive_unwatered >= 2)
    missed_care_bonuses: int = 0    # pasture tiles where cared_today == False at end of day
    weed_proliferation: int = 0     # weed tiles counted across the game
    uncollected_harvests: int = 0   # tiles with yield_units > 0 at day 29


@dataclass
class BottleneckReport:
    unit_efficiency: UnitTurnEfficiency = field(default_factory=UnitTurnEfficiency)
    market: MarketTelemetry = field(default_factory=MarketTelemetry)
    crops: CropTelemetry = field(default_factory=CropTelemetry)
    n_steps: int = 0
    final_score: float = 0.0
    top_bottlenecks: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Action classifiers
# ---------------------------------------------------------------------------

_MOVEMENT_ACTIONS = {"NORTH", "SOUTH", "EAST", "WEST"}
_WORK_ACTIONS = {
    "WATER", "PLANT", "HARVEST", "CARE", "FEED", "COLLECT_FERTILIZER",
    "FERTILIZE", "BUILD_PASTURE", "BUILD_COOP", "DIG", "PLACE", "PICKUP", "DROP",
}


def _classify_unit_action(action: Optional[List[str]]) -> str:
    """Return 'walk', 'work', 'idle', or 'dropoff'."""
    if not action:
        return "idle"
    verb = action[0] if action else "PASS"
    if verb in _MOVEMENT_ACTIONS:
        return "walk"
    if verb == "PASS":
        return "idle"
    if verb == "DROP":
        return "dropoff"
    return "work"


# ---------------------------------------------------------------------------
# Core extractor
# ---------------------------------------------------------------------------

def extract_bottlenecks(
    trace: List[Tuple[Dict[str, Any], Dict[str, Any]]],
    player: int = 0,
    total_days: int = 30,
) -> BottleneckReport:
    """Build a BottleneckReport from a list of (obs_dict, action_dict) pairs.

    Parameters
    ----------
    trace : list of (obs, action) tuples collected during one game
    player : which player index to analyse (0 or 1)
    total_days : total days in the episode (default 30)
    """
    report = BottleneckReport()
    n = len(trace)
    report.n_steps = n

    for obs, action in trace:
        day = int(obs.get("day", 0))
        hour = int(obs.get("hour", 0))
        farms = obs.get("farms") or []
        me = farms[player] if len(farms) > player else {}
        private = obs.get("private") or {}
        shed = private.get("shed") or {}
        market_orders = (action or {}).get("market") or []

        # ── Unit-turn efficiency ──────────────────────────────────────────
        units = [action.get("farmer")] + list(action.get("hands") or [])
        for ua in units:
            classification = _classify_unit_action(ua)
            report.unit_efficiency.total_turns += 1
            if classification == "walk":
                report.unit_efficiency.walk_turns += 1
            elif classification == "work":
                report.unit_efficiency.work_turns += 1
            elif classification == "idle":
                report.unit_efficiency.idle_turns += 1
            elif classification == "dropoff":
                report.unit_efficiency.dropoff_turns += 1

        # ── Market telemetry ─────────────────────────────────────────────
        report.market.total_order_slots += 10
        report.market.used_order_slots += len(market_orders)

        # Wheat starvation: animals on tiles but shed wheat == 0
        shed_wheat = int(shed.get("WHEAT", 0))
        animals_on_farm = sum(
            1 for row in (me.get("tiles") or [])
            for t in row
            if isinstance(t, dict) and t.get("animal")
        )
        if animals_on_farm > 0 and shed_wheat == 0:
            report.market.wheat_zero_events += 1

        # ── Crop telemetry ───────────────────────────────────────────────
        for row in (me.get("tiles") or []):
            for t in row:
                if not isinstance(t, dict):
                    continue
                kind = t.get("kind")
                if kind == "WEED":
                    report.crops.weed_proliferation += 1
                elif kind == "PLANT":
                    # Detect imminent weed (already unwatered once, unwatered today too)
                    if (int(t.get("consecutive_unwatered", 0)) >= 2
                            and not t.get("watered_today")):
                        report.crops.unwatered_deaths += 1
                elif kind in ("PASTURE", "COOP"):
                    if t.get("animal") and not t.get("cared_today") and hour == 23:
                        report.crops.missed_care_bonuses += 1

    # Last-step unsold produce
    if trace:
        last_obs, last_action = trace[-1]
        last_private = last_obs.get("private") or {}
        last_shed = last_private.get("shed") or {}
        last_day = int(last_obs.get("day", 0))
        if last_day >= total_days - 1:
            for product in ("STRAWBERRY", "MELON", "MILK", "WOOL", "FERTILIZER",
                            "WHEAT", "EGG", "CARROT", "TOMATO"):
                qty = int(last_shed.get(product, 0))
                if qty > 0:
                    report.crops.uncollected_harvests += qty
                    report.market.unsold_produce_day29[product] = qty
        report.final_score = (
            float(last_obs.get("farms", [{}, {}])[player].get("money", 0.0))
        )

    # ── Rank bottlenecks ─────────────────────────────────────────────────
    bottlenecks = []
    eff = report.unit_efficiency
    if eff.total_turns > 0:
        if eff.walk_pct > 0.50:
            bottlenecks.append(
                f"HIGH_WALK_RATE: {eff.walk_pct:.0%} turns spent walking "
                f"({eff.walk_turns}/{eff.total_turns})"
            )
        if eff.idle_pct > 0.15:
            bottlenecks.append(
                f"HIGH_IDLE_RATE: {eff.idle_pct:.0%} turns idle"
            )

    if report.market.wasted_slots > 50:
        bottlenecks.append(
            f"WASTED_MARKET_SLOTS: {report.market.wasted_slots} unused order slots "
            f"({1 - report.market.slot_utilisation:.0%} waste rate)"
        )

    if report.market.wheat_zero_events > 5:
        bottlenecks.append(
            f"WHEAT_STARVATION: shed empty {report.market.wheat_zero_events} turns"
        )

    if report.crops.unwatered_deaths > 2:
        bottlenecks.append(
            f"CROP_DEATHS: {report.crops.unwatered_deaths} unwatered plant deaths"
        )

    if report.crops.weed_proliferation > 10:
        bottlenecks.append(
            f"WEED_INFESTATION: {report.crops.weed_proliferation} weed-turns observed"
        )

    if report.crops.uncollected_harvests > 20:
        total_unsold = sum(report.market.unsold_produce_day29.values())
        bottlenecks.append(
            f"UNSOLD_ENDGAME: {total_unsold} items in shed at game end"
        )

    report.top_bottlenecks = bottlenecks
    return report
