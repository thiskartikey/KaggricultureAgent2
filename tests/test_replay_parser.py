"""
Unit tests for src/replay_analysis/parser.py

Tests cover:
  - Valid replay parsing (correct field extraction, counts, etc.)
  - Malformed replay handling (truncated, missing keys, bad JSON)
  - Self-play replay handling (both players extracted)
  - Corpus-player filtering (only the folder-owner extracted)
  - Action summary counting (PLANT, WATER, HARVEST, CARE, FEED, BUILD, DIG)
  - Schema completeness (all required fields present)
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.replay_analysis.parser import parse_replay, _summarise_action, _count_tile_crops, _count_tile_animals
from src.replay_analysis.schema import CanonicalTurn


# ---------------------------------------------------------------------------
# Replay fixture factories
# ---------------------------------------------------------------------------

def _make_farm(
    money: float = 3000.0,
    hands: int = 0,
    unlocked_quadrants: List[str] = None,
    tiles: List[List[Any]] = None,
) -> Dict[str, Any]:
    if unlocked_quadrants is None:
        unlocked_quadrants = ["NW"]
    if tiles is None:
        tiles = [[None] * 10 for _ in range(10)]
    return {
        "money": money,
        "hands": [{"pos": [0, 0]} for _ in range(hands)],
        "hires_today": 0,
        "unlocked_quadrants": unlocked_quadrants,
        "farmer": [4, 4],
        "tiles": tiles,
    }


def _make_obs(
    player: int = 0,
    day: int = 0,
    hour: int = 0,
    step: int = 0,
    money: float = 3000.0,
    hands: int = 0,
    unlocked_quadrants: List[str] = None,
    tiles: List[List[Any]] = None,
) -> Dict[str, Any]:
    farms = [
        _make_farm(money=money, hands=hands, unlocked_quadrants=unlocked_quadrants, tiles=tiles),
        _make_farm(),
    ]
    return {
        "player": player,
        "day": day,
        "hour": hour,
        "step": step,
        "farms": farms,
        "market": {
            "prices": {"WHEAT": 25, "STRAWBERRY": 120, "MILK": 160},
            "inventory": {"WHEAT": 5000, "STRAWBERRY": 1000},
        },
        "town": {"unlocked_shops": []},
        "private": {
            "shed": {"WHEAT": 0, "MILK": 0},
            "seeds": {"WHEAT": 5, "STRAWBERRY": 0},
            "inventories": [],
        },
        "remainingOverageTime": 60,
    }


def _make_action(
    farmer: List[str] = None,
    hands: List[List[str]] = None,
    market: List[List[Any]] = None,
) -> Dict[str, Any]:
    return {
        "farmer": farmer or ["PASS"],
        "hands": hands or [],
        "market": market or [],
    }


def _make_step(
    player0_action=None,
    player1_action=None,
    player0_obs_kwargs: Dict = None,
    player1_obs_kwargs: Dict = None,
) -> List[Dict[str, Any]]:
    obs0 = _make_obs(player=0, **(player0_obs_kwargs or {}))
    obs1 = _make_obs(player=1, **(player1_obs_kwargs or {}))
    return [
        {"action": player0_action or _make_action(), "observation": obs0, "reward": 0.0, "status": "ACTIVE", "info": {}},
        {"action": player1_action or _make_action(), "observation": obs1, "reward": 0.0, "status": "ACTIVE", "info": {}},
    ]


def _make_replay(
    episode_id: int = 12345,
    team_names: List[str] = None,
    rewards: List[float] = None,
    steps: List[Any] = None,
) -> Dict[str, Any]:
    if team_names is None:
        team_names = ["Ezzzzzekki", "GiovanniCR"]
    if rewards is None:
        rewards = [50000.0, 45000.0]
    if steps is None:
        steps = [_make_step() for _ in range(5)]
    return {
        "id": episode_id,
        "rewards": rewards,
        "statuses": ["DONE", "DONE"],
        "info": {
            "EpisodeId": episode_id,
            "TeamNames": team_names,
            "seed": 42,
            "Agents": [],
            "LiveVideoPath": "",
        },
        "steps": steps,
    }


def _write_replay(tmp_dir: Path, name: str, data: Dict) -> Path:
    path = tmp_dir / name
    path.write_text(json.dumps(data))
    return path


# ---------------------------------------------------------------------------
# Tests: _summarise_action
# ---------------------------------------------------------------------------

class TestSummariseAction:
    def test_empty_action(self):
        result = _summarise_action({})
        assert result == {"num_plant": 0, "num_water": 0, "num_harvest": 0,
                          "num_care": 0, "num_feed": 0, "num_build": 0, "num_dig": 0}

    def test_farmer_plant(self):
        result = _summarise_action({"farmer": ["PLANT"], "hands": [], "market": []})
        assert result["num_plant"] == 1

    def test_multiple_hands_water(self):
        result = _summarise_action({
            "farmer": ["PASS"],
            "hands": [["WATER"], ["WATER"], ["PASS"]],
            "market": [],
        })
        assert result["num_water"] == 2

    def test_mixed_operations(self):
        result = _summarise_action({
            "farmer": ["CARE"],
            "hands": [["PLANT"], ["WATER"], ["HARVEST"], ["FEED"], ["DIG"], ["BUILD_PASTURE"]],
            "market": [["HIRE"]],
        })
        assert result["num_care"] == 1
        assert result["num_plant"] == 1
        assert result["num_water"] == 1
        assert result["num_harvest"] == 1
        assert result["num_feed"] == 1
        assert result["num_dig"] == 1
        assert result["num_build"] == 1

    def test_build_coop_counted(self):
        result = _summarise_action({"farmer": ["BUILD_COOP"], "hands": [], "market": []})
        assert result["num_build"] == 1

    def test_none_action_tolerant(self):
        result = _summarise_action({"farmer": None, "hands": None, "market": None})
        assert result["num_plant"] == 0


# ---------------------------------------------------------------------------
# Tests: _count_tile_crops
# ---------------------------------------------------------------------------

class TestCountTileCrops:
    def test_empty_tiles(self):
        tiles = [[None] * 5 for _ in range(5)]
        result = _count_tile_crops(tiles)
        assert result == {"WHEAT": 0, "CARROT": 0, "TOMATO": 0, "STRAWBERRY": 0, "MELON": 0}

    def test_wheat_tiles(self):
        tiles = [[{"kind": "PLANT", "crop": "WHEAT"}, {"kind": "PLANT", "crop": "STRAWBERRY"}]]
        result = _count_tile_crops(tiles)
        assert result["WHEAT"] == 1
        assert result["STRAWBERRY"] == 1

    def test_ignores_locked_and_pasture(self):
        tiles = [["LOCKED", {"kind": "PASTURE", "animal": "COW"}, {"kind": "PLANT", "crop": "MELON"}]]
        result = _count_tile_crops(tiles)
        assert result["MELON"] == 1
        assert result["WHEAT"] == 0


# ---------------------------------------------------------------------------
# Tests: _count_tile_animals
# ---------------------------------------------------------------------------

class TestCountTileAnimals:
    def test_pasture_cow(self):
        tiles = [[{"kind": "PASTURE", "animal": "COW"}]]
        animals, structs = _count_tile_animals(tiles)
        assert animals["COW"] == 1
        assert structs["PASTURE"] == 1

    def test_coop_goose(self):
        tiles = [[{"kind": "COOP", "animal": "GOOSE"}]]
        animals, structs = _count_tile_animals(tiles)
        assert animals["GOOSE"] == 1
        assert structs["COOP"] == 1

    def test_mixed(self):
        tiles = [
            [{"kind": "PASTURE", "animal": "COW"}, {"kind": "PASTURE", "animal": "SHEEP"}],
            [{"kind": "PASTURE", "animal": "COW"}],
        ]
        animals, structs = _count_tile_animals(tiles)
        assert animals["COW"] == 2
        assert animals["SHEEP"] == 1
        assert structs["PASTURE"] == 3


# ---------------------------------------------------------------------------
# Tests: parse_replay (file-level)
# ---------------------------------------------------------------------------

class TestParseReplay:
    def test_basic_extraction(self, tmp_path):
        replay = _make_replay(
            episode_id=99999,
            team_names=["Ezzzzzekki", "GiovanniCR"],
            rewards=[50000.0, 45000.0],
            steps=[_make_step(player0_obs_kwargs={"money": 3500.0, "hands": 4})],
        )
        path = _write_replay(tmp_path, "test.json", replay)
        turns = list(parse_replay(path, corpus_player="Ezzzzzekki"))

        assert len(turns) == 1
        t = turns[0]
        assert t.episode_id == "99999"
        assert t.player_name == "Ezzzzzekki"
        assert t.player_index == 0
        assert t.opponent_name == "GiovanniCR"
        assert t.money == 3500.0
        assert t.num_hands == 4
        assert t.final_score == 50000.0
        assert t.won is True

    def test_corpus_player_filtering(self, tmp_path):
        """Only the corpus player's turns are emitted (not the opponent's)."""
        replay = _make_replay(
            team_names=["Ezzzzzekki", "GiovanniCR"],
            rewards=[50000.0, 55000.0],
            steps=[_make_step()],
        )
        path = _write_replay(tmp_path, "test.json", replay)

        turns_ezz = list(parse_replay(path, corpus_player="Ezzzzzekki"))
        assert all(t.player_name == "Ezzzzzekki" for t in turns_ezz)
        assert all(t.player_index == 0 for t in turns_ezz)

        turns_gio = list(parse_replay(path, corpus_player="GiovanniCR"))
        assert all(t.player_name == "GiovanniCR" for t in turns_gio)
        assert all(t.player_index == 1 for t in turns_gio)

    def test_self_play_extracts_both(self, tmp_path):
        """Self-play replays yield turns for both player 0 and player 1."""
        replay = _make_replay(
            team_names=["Ezzzzzekki", "Ezzzzzekki"],
            rewards=[50000.0, 48000.0],
            steps=[_make_step()],
        )
        path = _write_replay(tmp_path, "self.json", replay)
        turns = list(parse_replay(path, corpus_player="Ezzzzzekki"))
        assert len(turns) == 2
        indices = {t.player_index for t in turns}
        assert indices == {0, 1}

    def test_won_flag(self, tmp_path):
        """won == True when this player's final_score > opponent's."""
        replay = _make_replay(
            team_names=["Ezzzzzekki", "GiovanniCR"],
            rewards=[60000.0, 50000.0],
            steps=[_make_step()],
        )
        path = _write_replay(tmp_path, "test.json", replay)
        turns = list(parse_replay(path, corpus_player="Ezzzzzekki"))
        assert turns[0].won is True

        replay2 = _make_replay(
            team_names=["Ezzzzzekki", "GiovanniCR"],
            rewards=[40000.0, 50000.0],
            steps=[_make_step()],
        )
        path2 = _write_replay(tmp_path, "test2.json", replay2)
        turns2 = list(parse_replay(path2, corpus_player="Ezzzzzekki"))
        assert turns2[0].won is False

    def test_malformed_json(self, tmp_path):
        """Bad JSON file yields zero turns without raising."""
        path = tmp_path / "bad.json"
        path.write_text("{not valid json!!!}")
        turns = list(parse_replay(path, corpus_player="Ezzzzzekki"))
        assert turns == []

    def test_empty_steps(self, tmp_path):
        """Replay with empty steps list yields zero turns."""
        replay = _make_replay(steps=[])
        path = _write_replay(tmp_path, "empty.json", replay)
        turns = list(parse_replay(path, corpus_player="Ezzzzzekki"))
        assert turns == []

    def test_missing_keys_in_step(self, tmp_path):
        """Malformed steps are silently skipped."""
        replay = _make_replay(steps=[
            [{"action": {}, "observation": {}, "reward": 0.0, "status": "ACTIVE", "info": {}},
             {"action": {}, "observation": {}, "reward": 0.0, "status": "ACTIVE", "info": {}}],
        ])
        path = _write_replay(tmp_path, "partial.json", replay)
        # Should not raise; some/all steps may be skipped
        turns = list(parse_replay(path, corpus_player="Ezzzzzekki"))
        assert isinstance(turns, list)

    def test_market_orders_captured(self, tmp_path):
        """Market orders in the action are stored on the turn."""
        action = _make_action(
            market=[["HIRE"], ["BUY_SEED", "STRAWBERRY", 12], ["BUY_ANIMAL", "COW", 1]]
        )
        replay = _make_replay(
            team_names=["Ezzzzzekki", "GiovanniCR"],
            steps=[_make_step(player0_action=action)],
        )
        path = _write_replay(tmp_path, "market.json", replay)
        turns = list(parse_replay(path, corpus_player="Ezzzzzekki"))
        assert len(turns) == 1
        orders = turns[0].market_orders
        assert ["HIRE"] in orders
        assert ["BUY_SEED", "STRAWBERRY", 12] in orders

    def test_unlocked_quadrants(self, tmp_path):
        replay = _make_replay(
            team_names=["Ezzzzzekki", "GiovanniCR"],
            steps=[_make_step(player0_obs_kwargs={"unlocked_quadrants": ["NW", "NE"]})],
        )
        path = _write_replay(tmp_path, "quads.json", replay)
        turns = list(parse_replay(path, corpus_player="Ezzzzzekki"))
        assert turns[0].unlocked_quadrants == ["NW", "NE"]

    def test_schema_fields_complete(self, tmp_path):
        """Every field in CanonicalTurn must be present on the parsed result."""
        replay = _make_replay(steps=[_make_step()])
        path = _write_replay(tmp_path, "full.json", replay)
        turns = list(parse_replay(path, corpus_player="Ezzzzzekki"))
        assert len(turns) >= 1
        t = turns[0]
        required_fields = CanonicalTurn.__dataclass_fields__.keys()
        for field_name in required_fields:
            assert hasattr(t, field_name), f"Missing field: {field_name}"

    def test_multiple_steps(self, tmp_path):
        """Parser yields one turn per step (for corpus player)."""
        n_steps = 10
        replay = _make_replay(
            team_names=["Ezzzzzekki", "GiovanniCR"],
            steps=[_make_step() for _ in range(n_steps)],
        )
        path = _write_replay(tmp_path, "multi.json", replay)
        turns = list(parse_replay(path, corpus_player="Ezzzzzekki"))
        assert len(turns) == n_steps

    def test_no_match_corpus_player(self, tmp_path):
        """If corpus_player not in TeamNames, yield zero turns."""
        replay = _make_replay(team_names=["Alice", "Bob"])
        path = _write_replay(tmp_path, "nomatch.json", replay)
        turns = list(parse_replay(path, corpus_player="Ezzzzzekki"))
        assert turns == []


# ---------------------------------------------------------------------------
# Tests: run() (integration — small batch)
# ---------------------------------------------------------------------------

class TestRunIntegration:
    def test_run_writes_csv(self, tmp_path):
        """run() should produce canonical_turns.csv with correct headers."""
        from src.replay_analysis.parser import run, CORPUS_FOLDERS

        # Create a minimal replays directory with one player folder
        replays_dir = tmp_path / "replays"
        player_dir = replays_dir / "Ezzzzzekki"
        player_dir.mkdir(parents=True)

        replay = _make_replay(
            episode_id=11111,
            team_names=["Ezzzzzekki", "GiovanniCR"],
            rewards=[55000.0, 40000.0],
            steps=[_make_step() for _ in range(3)],
        )
        (player_dir / "episode-11111-replay.json").write_text(json.dumps(replay))

        output_dir = tmp_path / "processed"
        total = run(replays_dir, output_dir)

        assert total == 3  # 3 steps × 1 player (corpus player only)
        csv_path = output_dir / "canonical_turns.csv"
        assert csv_path.exists()

        import csv as csv_mod
        with csv_path.open() as fh:
            reader = csv_mod.DictReader(fh)
            rows = list(reader)

        assert len(rows) == 3
        assert rows[0]["player_name"] == "Ezzzzzekki"
        assert rows[0]["episode_id"] == "11111"
