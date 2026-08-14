"""
Statistics aggregator for Kaggriculture replay analysis.

Reads canonical_turns.csv and computes per-player summary statistics
(means, medians, std-devs) used to populate player_summaries.json.

Usage (standalone):
    python -m src.replay_analysis.statistics \
        --turns data/processed/canonical_turns.csv \
        --output data/processed/player_summaries.json
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schema import PlayerSummary

log = logging.getLogger("replay_statistics")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mean(vals: List[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _median(vals: List[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def _std(vals: List[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = _mean(vals)
    variance = sum((x - m) ** 2 for x in vals) / (len(vals) - 1)
    return math.sqrt(variance)


def _load_turns_csv(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(row)
    return rows


def _parse_json_col(val: str) -> Any:
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return val


# ---------------------------------------------------------------------------
# Per-episode summary extraction
# ---------------------------------------------------------------------------

def _episode_summaries(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Collapse the turn-level rows into one dict per (player_name, episode_id).

    Returns a dict keyed by ``(player_name, episode_id)`` with:
      - final_score, won
      - day_2nd_quad, day_3rd_quad, day_4th_quad (first day each unlock appeared)
      - crew_by_day: {day: [num_hands, …]} → median hands per day
      - seeds_purchased: {crop: total bought across episode}
      - pastures_day15, cows_day20, sheep_day20
    """
    episodes: Dict[str, Dict[str, Any]] = {}

    for row in rows:
        player = row.get("player_name", "")
        ep = row.get("episode_id", "")
        key = f"{player}||{ep}"

        if key not in episodes:
            episodes[key] = {
                "player_name": player,
                "episode_id": ep,
                "final_score": 0.0,
                "won": False,
                "day_2nd_quad": None,
                "day_3rd_quad": None,
                "day_4th_quad": None,
                "crew_by_day": defaultdict(list),
                "seeds_bought": defaultdict(int),
                "pastures_day15": None,
                "cows_day20": None,
                "sheep_day20": None,
            }

        ep_data = episodes[key]

        try:
            day = int(row.get("day", 0))
            step = int(row.get("step", 0))
            hour = int(row.get("hour", 0))
            final_score = float(row.get("final_score", 0))
            won_str = row.get("won", "False")
            won = won_str in ("True", "true", "1")
            num_hands = int(row.get("num_hands", 0))

            ep_data["final_score"] = final_score
            ep_data["won"] = won

            # Crew size by day
            ep_data["crew_by_day"][day].append(num_hands)

            # Quadrant unlock milestones
            quads_raw = row.get("unlocked_quadrants", "[]")
            quads = _parse_json_col(quads_raw) if isinstance(quads_raw, str) else quads_raw
            if isinstance(quads, list):
                nq = len(quads)
                if nq >= 2 and ep_data["day_2nd_quad"] is None:
                    ep_data["day_2nd_quad"] = day
                if nq >= 3 and ep_data["day_3rd_quad"] is None:
                    ep_data["day_3rd_quad"] = day
                if nq >= 4 and ep_data["day_4th_quad"] is None:
                    ep_data["day_4th_quad"] = day

            # Seed purchases from market orders
            orders_raw = row.get("market_orders", "[]")
            orders = _parse_json_col(orders_raw) if isinstance(orders_raw, str) else orders_raw
            if isinstance(orders, list):
                for order in orders:
                    if isinstance(order, list) and len(order) >= 3 and order[0] == "BUY_SEED":
                        crop = order[1]
                        qty = int(order[2]) if order[2] else 1
                        ep_data["seeds_bought"][crop] += qty

            # Snapshot values at milestone days
            structures_raw = row.get("structures", "{}")
            structures = _parse_json_col(structures_raw) if isinstance(structures_raw, str) else structures_raw
            animals_raw = row.get("animal_counts", "{}")
            animals = _parse_json_col(animals_raw) if isinstance(animals_raw, str) else animals_raw

            if isinstance(structures, dict) and isinstance(animals, dict):
                pastures = structures.get("PASTURE", 0)
                cows = animals.get("COW", 0)
                sheep = animals.get("SHEEP", 0)

                if day <= 15:
                    ep_data["pastures_day15"] = pastures
                if day <= 20:
                    ep_data["cows_day20"] = cows
                    ep_data["sheep_day20"] = sheep

        except (ValueError, TypeError):
            continue

    return episodes


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def compute_player_summaries(
    turns_csv: Path,
) -> Dict[str, PlayerSummary]:
    """
    Load canonical_turns.csv and return a dict of PlayerSummary keyed by player name.
    """
    rows = _load_turns_csv(turns_csv)
    if not rows:
        log.warning("No rows found in %s", turns_csv)
        return {}

    episode_data = _episode_summaries(rows)

    # Group episodes by player
    by_player: Dict[str, List[Dict]] = defaultdict(list)
    for ep in episode_data.values():
        by_player[ep["player_name"]].append(ep)

    summaries: Dict[str, PlayerSummary] = {}

    for player_name, eps in by_player.items():
        ps = PlayerSummary(player_name=player_name)
        ps.num_episodes = len(eps)

        scores = [ep["final_score"] for ep in eps]
        wins = [ep for ep in eps if ep["won"]]
        ps.win_rate = len(wins) / len(eps) if eps else 0.0
        ps.mean_final_score = _mean(scores)
        ps.median_final_score = _median(scores)
        ps.std_final_score = _std(scores)

        # Quadrant milestones
        days_2nd = [ep["day_2nd_quad"] for ep in eps if ep["day_2nd_quad"] is not None]
        days_3rd = [ep["day_3rd_quad"] for ep in eps if ep["day_3rd_quad"] is not None]
        days_4th = [ep["day_4th_quad"] for ep in eps if ep["day_4th_quad"] is not None]

        ps.median_day_2nd_quadrant = _median(days_2nd) if days_2nd else None
        ps.median_day_3rd_quadrant = _median(days_3rd) if days_3rd else None
        ps.pct_unlock_4th_quadrant = len(days_4th) / len(eps) if eps else 0.0

        # Crew size per day (median across episodes)
        all_day_hands: Dict[int, List[float]] = defaultdict(list)
        for ep in eps:
            for day, hand_counts in ep["crew_by_day"].items():
                all_day_hands[day].append(_mean(hand_counts))
        ps.mean_crew_size_per_day = {
            str(d): round(_mean(vals), 2) for d, vals in sorted(all_day_hands.items())
        }

        # Seeds per game
        all_crop_seeds: Dict[str, List[float]] = defaultdict(list)
        for ep in eps:
            for crop, qty in ep["seeds_bought"].items():
                all_crop_seeds[crop].append(float(qty))
        ps.mean_seeds_per_game = {
            crop: round(_mean(vals), 1) for crop, vals in sorted(all_crop_seeds.items())
        }

        # Livestock snapshot
        cows20 = [ep["cows_day20"] for ep in eps if ep["cows_day20"] is not None]
        sheep20 = [ep["sheep_day20"] for ep in eps if ep["sheep_day20"] is not None]
        pastures15 = [ep["pastures_day15"] for ep in eps if ep["pastures_day15"] is not None]

        ps.mean_cows_day20 = round(_mean(cows20), 2)
        ps.mean_sheep_day20 = round(_mean(sheep20), 2)
        ps.mean_pastures_day15 = round(_mean(pastures15), 2)

        summaries[player_name] = ps

    return summaries


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Compute per-player strategy statistics from canonical_turns.csv"
    )
    parser.add_argument("--turns", required=True, type=Path,
                        help="Path to canonical_turns.csv")
    parser.add_argument("--output", required=True, type=Path,
                        help="Output path for player_summaries.json")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    summaries = compute_player_summaries(args.turns)
    output_data = {name: ps.to_dict() for name, ps in summaries.items()}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        json.dump(output_data, fh, indent=2)

    print(f"Wrote summaries for {len(summaries)} players to {args.output}")
    for name, ps in sorted(summaries.items()):
        print(f"  {name}: {ps.num_episodes} episodes, "
              f"win_rate={ps.win_rate:.1%}, mean_score={ps.mean_final_score:,.0f}")


if __name__ == "__main__":
    main()
