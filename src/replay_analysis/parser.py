"""
Canonical Replay Parser for Kaggriculture.

Transforms raw JSON replay files into a tabular canonical dataset
(data/processed/canonical_turns.csv).

Usage:
    python -m src.replay_analysis.parser --input replays/ --output data/processed/

Each replay produces one row per step per player (corpus player only,
unless it is self-play in which case both players are emitted).
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from .schema import ActionsSummary, CanonicalTurn

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CROP_TYPES = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
ANIMAL_TYPES = ["COW", "SHEEP", "GOOSE"]
STRUCTURE_TYPES = ["PASTURE", "COOP"]

# Folder name → canonical corpus player name
CORPUS_FOLDERS = {
    "Ezzzzzekki": "Ezzzzzekki",
    "GiovanniCR": "GiovanniCR",
    "HealthStone": "HealthStone",
    "ThunderThunder": "ThunderThunder",
}

# Kaggle display names → folder/corpus player key.
# Some players have a different display name than their folder label.
CORPUS_ALIASES = {
    "THUNDER THUNDER": "ThunderThunder",
}

log = logging.getLogger("replay_parser")


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _count_tile_crops(tiles: List[List[Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {c: 0 for c in CROP_TYPES}
    for row in tiles:
        for cell in row:
            if isinstance(cell, dict) and cell.get("kind") == "PLANT":
                crop = cell.get("crop")
                if crop in counts:
                    counts[crop] += 1
    return counts


def _count_tile_animals(tiles: List[List[Any]]) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Return (animal_counts, structure_counts)."""
    animal_counts: Dict[str, int] = {a: 0 for a in ANIMAL_TYPES}
    structure_counts: Dict[str, int] = {s: 0 for s in STRUCTURE_TYPES}
    for row in tiles:
        for cell in row:
            if not isinstance(cell, dict):
                continue
            kind = cell.get("kind")
            if kind == "PASTURE":
                structure_counts["PASTURE"] += 1
                animal = cell.get("animal")
                if animal in animal_counts:
                    animal_counts[animal] += 1
            elif kind == "COOP":
                structure_counts["COOP"] += 1
                animal = cell.get("animal")
                if animal in animal_counts:
                    animal_counts[animal] += 1
    return animal_counts, structure_counts


def _summarise_action(action: Dict[str, Any]) -> Dict[str, int]:
    """Count operation types across farmer and all hands."""
    summary = ActionsSummary()

    def _tally(ops: List[str]) -> None:
        for op in ops:
            if op == "PLANT":
                summary.num_plant += 1
            elif op == "WATER":
                summary.num_water += 1
            elif op == "HARVEST":
                summary.num_harvest += 1
            elif op == "CARE":
                summary.num_care += 1
            elif op == "FEED":
                summary.num_feed += 1
            elif op in ("BUILD_PASTURE", "BUILD_COOP"):
                summary.num_build += 1
            elif op == "DIG":
                summary.num_dig += 1

    farmer_ops = action.get("farmer") or []
    if isinstance(farmer_ops, list):
        _tally(farmer_ops)

    for hand_ops in (action.get("hands") or []):
        if isinstance(hand_ops, list):
            _tally(hand_ops)

    return summary.to_dict()


# ---------------------------------------------------------------------------
# Per-step extraction
# ---------------------------------------------------------------------------

def _extract_turn(
    episode_id: str,
    step_index: int,
    step_record: Dict[str, Any],
    player_index: int,
    opponent_index: int,
    corpus_player: str,
    final_scores: List[float],
    final_rewards: List[float],
) -> Optional[CanonicalTurn]:
    """
    Extract a CanonicalTurn for ``player_index`` at ``step_index``.

    Returns None if the step record is malformed.
    """
    try:
        player_entry = step_record[player_index]
        obs = player_entry["observation"]
        action = player_entry.get("action") or {}

        day: int = obs["day"]
        hour: int = obs["hour"]
        step_num: int = obs["step"]

        farms: List[Dict] = obs["farms"]  # list of 2 farm dicts
        my_farm = farms[player_index]

        # Money and labour
        money: float = float(my_farm.get("money", 0))
        hands_list = my_farm.get("hands") or []
        num_hands: int = len(hands_list)
        unlocked_quadrants: List[str] = list(my_farm.get("unlocked_quadrants") or [])

        # Tile-derived counts
        tiles = my_farm.get("tiles") or []
        crop_counts = _count_tile_crops(tiles)
        animal_counts, structure_counts = _count_tile_animals(tiles)

        # Action
        actions_summary = _summarise_action(action)
        market_orders: List[List[Any]] = list(action.get("market") or [])

        # Market global state (same for both players at this step)
        market = obs.get("market") or {}
        market_prices: Dict[str, float] = dict(market.get("prices") or {})
        market_inventory: Dict[str, int] = dict(market.get("inventory") or {})

        # Town
        town = obs.get("town") or {}
        town_shops: List[str] = list(town.get("unlocked_shops") or [])

        # Private state (only available for this player's own observation)
        private = obs.get("private") or {}
        shed: Dict[str, int] = dict(private.get("shed") or {})
        seeds: Dict[str, int] = dict(private.get("seeds") or {})

        # Player names: observation['player'] field gives the player index
        # Use TeamNames extracted upstream
        player_name: str = ""    # filled by caller
        opponent_name: str = ""  # filled by caller

        # Outcome
        final_score = float(final_scores[player_index]) if player_index < len(final_scores) else 0.0
        final_reward = float(final_rewards[player_index]) if player_index < len(final_rewards) else 0.0
        opp_score = float(final_scores[opponent_index]) if opponent_index < len(final_scores) else 0.0
        won = final_score > opp_score

        turn = CanonicalTurn(
            episode_id=episode_id,
            step=step_num,
            day=day,
            hour=hour,
            player_name=player_name,      # set after return
            player_index=player_index,
            opponent_name=opponent_name,  # set after return
            money=money,
            unlocked_quadrants=unlocked_quadrants,
            num_hands=num_hands,
            crop_counts=crop_counts,
            animal_counts=animal_counts,
            structures=structure_counts,
            actions_summary=actions_summary,
            market_orders=market_orders,
            market_prices=market_prices,
            market_inventory=market_inventory,
            town_shops=town_shops,
            shed=shed,
            seeds=seeds,
            final_score=final_score,
            final_reward=final_reward,
            corpus_player=corpus_player,
            won=won,
        )
        return turn

    except (KeyError, IndexError, TypeError) as exc:
        log.debug("Malformed step %d player %d in episode %s: %s", step_index, player_index, episode_id, exc)
        return None


# ---------------------------------------------------------------------------
# Replay-level parsing
# ---------------------------------------------------------------------------

def parse_replay(
    path: Path,
    corpus_player: str,
) -> Iterator[CanonicalTurn]:
    """
    Parse a single replay JSON file.  Yields one CanonicalTurn per step
    for every player we should extract (corpus player, or both in self-play).

    ``corpus_player`` is the name of the folder owner (e.g. "Ezzzzzekki").
    """
    try:
        with path.open("r", encoding="utf-8") as fh:
            replay = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        warnings.warn(f"Could not load {path}: {exc}")
        return

    try:
        episode_id = str(replay.get("info", {}).get("EpisodeId") or path.stem)
        team_names: List[str] = replay.get("info", {}).get("TeamNames") or ["Unknown", "Unknown"]
        while len(team_names) < 2:
            team_names.append("Unknown")

        final_rewards: List[float] = list(replay.get("rewards") or [0.0, 0.0])
        while len(final_rewards) < 2:
            final_rewards.append(0.0)

        steps: List[Any] = replay.get("steps") or []
        if not steps:
            warnings.warn(f"No steps in {path}")
            return

        # Determine which players to extract.
        # A player's display name may differ from the folder key (e.g. "THUNDER THUNDER"
        # lives in replays/ThunderThunder/). Resolve via CORPUS_ALIASES first.
        def _resolve(name: str) -> str:
            return CORPUS_ALIASES.get(name, name)

        is_self_play = (_resolve(team_names[0]) == _resolve(team_names[1]))
        target_indices: List[int] = []
        for pi, name in enumerate(team_names):
            if is_self_play or _resolve(name) == corpus_player:
                target_indices.append(pi)

        if not target_indices:
            log.debug("Neither player matches corpus_player=%s in %s (teams=%s)", corpus_player, path.name, team_names)
            return

        # Final scores come from the last valid step for each player
        final_scores = [0.0, 0.0]
        for pi in range(2):
            for step_rec in reversed(steps):
                try:
                    final_scores[pi] = float(step_rec[pi].get("reward") or 0.0)
                    if final_scores[pi] != 0.0:
                        break
                except (IndexError, TypeError):
                    pass
        # Prefer top-level rewards if available
        top_rewards = replay.get("rewards")
        if top_rewards and len(top_rewards) >= 2:
            final_scores = [float(top_rewards[0]), float(top_rewards[1])]

        for step_index, step_rec in enumerate(steps):
            if not isinstance(step_rec, list) or len(step_rec) < 2:
                continue
            for player_index in target_indices:
                opponent_index = 1 - player_index
                turn = _extract_turn(
                    episode_id=episode_id,
                    step_index=step_index,
                    step_record=step_rec,
                    player_index=player_index,
                    opponent_index=opponent_index,
                    corpus_player=corpus_player,
                    final_scores=final_scores,
                    final_rewards=final_rewards,
                )
                if turn is None:
                    continue
                turn.player_name = team_names[player_index]
                turn.opponent_name = team_names[opponent_index]
                yield turn

    except Exception as exc:  # pylint: disable=broad-except
        warnings.warn(f"Error parsing replay {path}: {exc}")
        return


# ---------------------------------------------------------------------------
# CSV serialisation helpers
# ---------------------------------------------------------------------------

# Columns that are JSON-serialised (dicts / lists)
_JSON_COLS = {
    "unlocked_quadrants",
    "crop_counts",
    "animal_counts",
    "structures",
    "actions_summary",
    "market_orders",
    "market_prices",
    "market_inventory",
    "town_shops",
    "shed",
    "seeds",
}

def _turn_to_row(turn: CanonicalTurn) -> Dict[str, Any]:
    d = turn.to_dict()
    for col in _JSON_COLS:
        if col in d:
            d[col] = json.dumps(d[col], separators=(",", ":"))
    return d


def _get_fieldnames(turn: CanonicalTurn) -> List[str]:
    return list(turn.to_dict().keys())


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def run(input_dir: Path, output_dir: Path) -> int:
    """
    Walk ``input_dir`` looking for replay JSON files organised in player
    sub-folders (e.g. replays/Ezzzzzekki/*.json).  Emits all canonical turns
    to ``output_dir/canonical_turns.csv``.

    Returns total number of turns written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "canonical_turns.csv"

    total_turns = 0
    total_replays = 0
    skipped_replays = 0

    writer: Optional[csv.DictWriter] = None
    fh = None

    try:
        fh = out_path.open("w", newline="", encoding="utf-8")

        for folder_name, corpus_player in CORPUS_FOLDERS.items():
            folder = input_dir / folder_name
            if not folder.is_dir():
                log.warning("Folder not found: %s", folder)
                continue

            replay_files = sorted(folder.glob("*.json"))
            log.info("Processing %d replays for %s", len(replay_files), corpus_player)

            for replay_path in replay_files:
                turns_this_replay = 0
                try:
                    for turn in parse_replay(replay_path, corpus_player):
                        row = _turn_to_row(turn)
                        if writer is None:
                            writer = csv.DictWriter(fh, fieldnames=list(row.keys()))
                            writer.writeheader()
                        writer.writerow(row)
                        turns_this_replay += 1
                        total_turns += 1
                    total_replays += 1
                except Exception as exc:  # pylint: disable=broad-except
                    warnings.warn(f"Skipping {replay_path}: {exc}")
                    skipped_replays += 1
                    continue

                if turns_this_replay == 0:
                    log.debug("Zero turns extracted from %s", replay_path.name)

        log.info(
            "Done. Replays: %d parsed, %d skipped. Turns written: %d → %s",
            total_replays,
            skipped_replays,
            total_turns,
            out_path,
        )
    finally:
        if fh is not None:
            fh.close()

    return total_turns


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Parse Kaggriculture replay JSON files into canonical_turns.csv"
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Root directory containing per-player replay sub-folders",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output directory (canonical_turns.csv written here)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG logging",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    total = run(args.input, args.output)
    print(f"Wrote {total:,} canonical turns to {args.output / 'canonical_turns.csv'}")


if __name__ == "__main__":
    main()
