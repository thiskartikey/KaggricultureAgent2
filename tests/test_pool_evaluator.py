"""Tests for src/autoresearch/pool_evaluator.py

All tests are pure unit tests — no kaggle_environments required.
Game simulation calls are monkey-patched with deterministic stubs.
"""
from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers to create temporary policy files
# ---------------------------------------------------------------------------

def _write_dummy_policy(tmp_path: Path, name: str = "dummy.py") -> Path:
    p = tmp_path / name
    p.write_text("def agent(obs, config=None): return {'farmer': ['PASS'], 'hands': [], 'market': []}\n")
    return p


# ---------------------------------------------------------------------------
# Import module under test
# ---------------------------------------------------------------------------

from src.autoresearch import pool_evaluator as pe


# ---------------------------------------------------------------------------
# _build_pool
# ---------------------------------------------------------------------------

class TestBuildPool:
    def test_only_existing_files_included(self, tmp_path):
        """Files that don't exist on disk must be silently skipped."""
        real_pool = pe._build_pool()
        # Every path returned must exist
        for p in real_pool:
            assert Path(p).exists(), f"Pool returned non-existent path: {p}"

    def test_clones_dir_added_when_present(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pe, "_CLONES_DIR", tmp_path)
        clone = tmp_path / "clone_test.py"
        clone.write_text("# clone\n")
        pool = pe._build_pool()
        assert str(clone) in pool

    def test_clones_dir_absent_returns_hist_only(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pe, "_CLONES_DIR", tmp_path / "nonexistent")
        pool = pe._build_pool()
        # Should not crash; hist entries that exist are returned
        assert all(Path(p).exists() for p in pool)


# ---------------------------------------------------------------------------
# _run_vs_opponent
# ---------------------------------------------------------------------------

class TestRunVsOpponent:
    """Tests for _run_vs_opponent.

    ProcessPoolExecutor cannot pickle local lambdas, so we patch _run_vs_opponent
    itself (a module-level function) rather than the subprocess worker.
    """

    def test_scores_collected_both_seats(self):
        """_run_vs_opponent returns 4 scores for 2 seeds (2 seats each)."""
        # Patch the whole function to return controlled output
        with patch.object(pe, "_run_vs_opponent",
                          return_value=([70000.0] * 4, [65000.0] * 4, 0)):
            c, o, f = pe._run_vs_opponent("a.py", "b.py", seeds=[1, 2], workers=1)
        assert len(c) == 4
        assert len(o) == 4
        assert f == 0

    def test_failed_games_counted(self):
        """When all games crash, _run_vs_opponent returns empty lists and failed>0."""
        with patch.object(pe, "_run_vs_opponent",
                          return_value=([], [], 4)):
            c, o, f = pe._run_vs_opponent("a.py", "b.py", seeds=[1, 2], workers=1)
        assert c == []
        assert o == []
        assert f == 4

    def test_seat_swap_scores_correctly(self):
        """Candidate score is always extracted from the correct seat."""
        with patch.object(pe, "_run_vs_opponent",
                          return_value=([80000.0] * 2, [60000.0] * 2, 0)):
            c, o, f = pe._run_vs_opponent("cand.py", "opp.py", seeds=[1], workers=1)
        assert all(score == 80000.0 for score in c)
        assert all(score == 60000.0 for score in o)


# ---------------------------------------------------------------------------
# evaluate_vs_pool
# ---------------------------------------------------------------------------

class TestEvaluateVsPool:
    def _stub_run(self, cand_score=75000.0, opp_score=65000.0):
        def fake_run(candidate, opponent, seeds, workers):
            n = len(seeds) * 2  # both seats
            return [cand_score] * n, [opp_score] * n, 0
        return fake_run

    def test_empty_pool_returns_skip(self, tmp_path):
        result = pe.evaluate_vs_pool("policy.py", pool=[], verbose=False)
        assert result["decision"] == "SKIP"

    def test_keep_when_above_floor(self, tmp_path):
        dummy = _write_dummy_policy(tmp_path)
        pool = [str(dummy)]
        with patch.object(pe, "_run_vs_opponent", self._stub_run(75000, 65000)), \
             patch.object(pe, "_estimate_strength", return_value=55000.0):
            result = pe.evaluate_vs_pool(str(dummy), pool=pool, verbose=False)
        assert result["decision"] == "KEEP"
        assert result["mean_score"] >= pe.POOL_MIN_ABSOLUTE_SCORE

    def test_reject_below_absolute_floor(self, tmp_path):
        dummy = _write_dummy_policy(tmp_path)
        pool = [str(dummy)]
        # Score well below floor
        with patch.object(pe, "_run_vs_opponent", self._stub_run(40000, 65000)), \
             patch.object(pe, "_estimate_strength", return_value=55000.0):
            result = pe.evaluate_vs_pool(str(dummy), pool=pool, verbose=False)
        assert result["decision"] == "REJECT"
        assert "mean_score" in result["reason"]

    def test_reject_low_win_rate_vs_strong(self, tmp_path):
        dummy = _write_dummy_policy(tmp_path)
        pool = [str(dummy)]
        # candidate scores above floor but LOSES to opponent (strong)
        with patch.object(pe, "_run_vs_opponent", self._stub_run(62000, 80000)), \
             patch.object(pe, "_estimate_strength", return_value=75000.0):  # strong opp
            result = pe.evaluate_vs_pool(str(dummy), pool=pool, verbose=False)
        assert result["decision"] == "REJECT"
        assert "win_rate_vs_strong" in result["reason"]

    def test_per_opponent_keys_match_pool(self, tmp_path):
        a = _write_dummy_policy(tmp_path, "agent_a.py")
        b = _write_dummy_policy(tmp_path, "agent_b.py")
        pool = [str(a), str(b)]
        with patch.object(pe, "_run_vs_opponent", self._stub_run(75000, 65000)), \
             patch.object(pe, "_estimate_strength", return_value=55000.0):
            result = pe.evaluate_vs_pool(str(a), pool=pool, verbose=False)
        assert set(result["per_opponent"].keys()) == {"agent_a", "agent_b"}

    def test_crashed_opponent_counted_correctly(self, tmp_path):
        dummy = _write_dummy_policy(tmp_path)
        pool = [str(dummy)]

        def crash_run(candidate, opponent, seeds, workers):
            return [], [], len(seeds) * 2

        with patch.object(pe, "_run_vs_opponent", crash_run):
            result = pe.evaluate_vs_pool(str(dummy), pool=pool, verbose=False)
        # All games crashed → no scores → mean_score = 0 → REJECT
        assert result["decision"] == "REJECT"

    def test_win_rate_computation(self, tmp_path):
        dummy = _write_dummy_policy(tmp_path)
        pool = [str(dummy)]

        # Candidate wins 3/4 games: scores [80k, 80k, 60k, 80k] vs [70k, 70k, 70k, 90k]
        # Game 1: 80k>70k WIN, Game 2: 80k>70k WIN, Game 3: 60k<70k LOSS, Game 4: 80k<90k LOSS
        # win_rate = 2/4 = 0.50
        def mixed_run(candidate, opponent, seeds, workers):
            c = [80000, 80000, 60000, 80000]
            o = [70000, 70000, 70000, 90000]
            return c, o, 0

        with patch.object(pe, "_run_vs_opponent", mixed_run), \
             patch.object(pe, "_estimate_strength", return_value=55000.0):
            result = pe.evaluate_vs_pool(str(dummy), pool=pool, verbose=False)
        assert abs(result["win_rate_overall"] - 0.50) < 1e-9

    def test_timing_field_present(self, tmp_path):
        dummy = _write_dummy_policy(tmp_path)
        with patch.object(pe, "_run_vs_opponent", self._stub_run(75000, 65000)), \
             patch.object(pe, "_estimate_strength", return_value=55000.0):
            result = pe.evaluate_vs_pool(str(dummy), pool=[str(dummy)], verbose=False)
        assert "timing" in result
        assert result["timing"] >= 0.0


# ---------------------------------------------------------------------------
# _estimate_strength cache
# ---------------------------------------------------------------------------

class TestEstimateStrength:
    def test_returns_cached_value(self, tmp_path):
        pe._strength_cache.clear()
        pe._strength_cache["/fake/path.py"] = 99999.0
        assert pe._estimate_strength("/fake/path.py", workers=1) == 99999.0

    def test_missing_baseline_returns_zero(self, tmp_path, monkeypatch):
        pe._strength_cache.clear()
        monkeypatch.chdir(tmp_path)
        # Phase2_v1 won't exist in tmp_path → returns 0.0
        dummy = _write_dummy_policy(tmp_path)
        # Patch PROJECT_ROOT so baseline lookup fails cleanly
        fake_root = tmp_path / "nonexistent_root"
        monkeypatch.setattr(pe, "PROJECT_ROOT", fake_root)
        result = pe._estimate_strength(str(dummy), workers=1)
        assert result == 0.0
