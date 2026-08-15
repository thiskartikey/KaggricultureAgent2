"""Tests for src/autoresearch/mutator.py"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from src.autoresearch.mutator import (
    lint,
    ASTLintError,
    mutate_tier1,
    mutate_tier2,
    mutate_tier3,
    TIER1_PARAMS,
)


# ---------------------------------------------------------------------------
# Minimal policy source stub for testing mutations
# ---------------------------------------------------------------------------

_STUB = textwrap.dedent("""\
    import math

    TARGET_COW = 8
    TARGET_SHEEP = 6
    TARGET_STRAWBERRY = 42
    TARGET_MELON = 12
    LAND_UNLOCK_DAY = (7, 11)
    CASH_FLOOR = 350
    TARGET_PASTURE_BY_DAY = ((11, 14), (7, 12), (0, 6))
    SHED_CAP = 100

    TASK_TIER = {
        "service": 0,
        "water": 0,
        "harvest_crop": 1,
        "service_soon": 1,
        "build_pasture": 2,
        "plant": 2,
        "fertilize": 2,
        "water_soon": 3,
        "weed": 4,
        "dropoff": 4,
    }

    _CLAIM_STATE = {}

    def _make_market_orders(obs, player=0, total_days=30):
        claims = {}
        return []

    def _assign_tasks(positions, tasks, invs, board, claims=None, feed_cells=None):
        return {}

    def agent(obs, config=None):
        return {"farmer": ["PASS"], "hands": [], "market": []}
""")


# ---------------------------------------------------------------------------
# AST linter tests
# ---------------------------------------------------------------------------

class TestLint:
    def test_valid_stub_passes(self):
        lint(_STUB)

    def test_syntax_error_raises(self):
        bad = _STUB + "\nif True\n    pass\n"
        with pytest.raises(ASTLintError, match="Syntax error"):
            lint(bad)

    def test_missing_agent_raises(self):
        no_agent = _STUB.replace("def agent(", "def _agnt(")
        with pytest.raises(ASTLintError, match="agent\\(\\)"):
            lint(no_agent)

    def test_forbidden_import_raises(self):
        with_torch = "import torch\n" + _STUB
        with pytest.raises(ASTLintError, match="Forbidden import"):
            lint(with_torch)

    def test_deleted_critical_identifier_raises(self):
        # Remove ALL lines containing "claims" — this also removes the
        # _assign_tasks definition line (which has claims=None in signature),
        # so the linter fires on either "claims" or "_assign_tasks" first.
        stripped = "\n".join(
            line for line in _STUB.splitlines()
            if "claims" not in line
        )
        with pytest.raises(ASTLintError):
            lint(stripped)


# ---------------------------------------------------------------------------
# Tier 1 mutator tests
# ---------------------------------------------------------------------------

class TestTier1:
    def test_mutate_target_cow(self):
        new_source, diff = mutate_tier1(_STUB, "TARGET_COW", 10)
        assert "TARGET_COW = 10" in new_source
        assert "TARGET_COW = 8" not in new_source
        assert "TARGET_COW" in diff

    def test_mutate_land_unlock_day(self):
        new_source, diff = mutate_tier1(_STUB, "LAND_UNLOCK_DAY", (6, 10))
        assert "(6, 10)" in new_source

    def test_mutate_cash_floor(self):
        new_source, diff = mutate_tier1(_STUB, "CASH_FLOOR", 400)
        assert "CASH_FLOOR = 400" in new_source

    def test_invalid_param_raises(self):
        with pytest.raises(ValueError, match="not in TIER1_PARAMS"):
            mutate_tier1(_STUB, "SHED_CAP", 120)

    def test_param_not_in_source_raises(self):
        with pytest.raises(ValueError, match="not locate"):
            mutate_tier1("x = 1\n\ndef agent(o): pass\n", "TARGET_COW", 5)

    def test_diff_is_nonempty(self):
        _, diff = mutate_tier1(_STUB, "TARGET_SHEEP", 8)
        assert len(diff) > 0


# ---------------------------------------------------------------------------
# Tier 2 mutator tests
# ---------------------------------------------------------------------------

class TestTier2:
    def test_replace_function(self):
        new_block = textwrap.dedent("""\
            def _make_market_orders(obs, player=0, total_days=30):
                claims = {}
                shed_access = True
                # New implementation
                return [["HIRE"]]
        """)
        new_source, diff = mutate_tier2(_STUB, "_make_market_orders", new_block)
        assert "New implementation" in new_source
        assert "return [['HIRE']]" in new_source or 'return [["HIRE"]]' in new_source

    def test_block_not_found_raises(self):
        with pytest.raises(ValueError, match="not found"):
            mutate_tier2(_STUB, "nonexistent_function", "def nonexistent_function(): pass\n")

    def test_diff_produced(self):
        new_block = "def _assign_tasks(positions, tasks, invs, board, claims=None, feed_cells=None):\n    return {}\n"
        _, diff = mutate_tier2(_STUB, "_assign_tasks", new_block)
        assert diff  # non-empty


# ---------------------------------------------------------------------------
# Tier 3 mutator tests
# ---------------------------------------------------------------------------

class TestTier3:
    def test_change_fertilize_tier(self):
        new_source, diff = mutate_tier3(_STUB, "fertilize", 1)
        assert '"fertilize": 1' in new_source
        assert '"fertilize": 2' not in new_source

    def test_change_weed_tier(self):
        new_source, diff = mutate_tier3(_STUB, "weed", 2)
        assert '"weed": 2' in new_source

    def test_invalid_tier_value_raises(self):
        with pytest.raises(ValueError, match="0–4"):
            mutate_tier3(_STUB, "fertilize", 9)

    def test_missing_task_raises(self):
        with pytest.raises(ValueError, match="not found"):
            mutate_tier3(_STUB, "nonexistent_task", 1)
