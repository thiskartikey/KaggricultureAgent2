"""Policy invariant tests — Phase 0, Task 1.

Guarantees that no candidate policy can ever enter evaluation unless it
satisfies all game-engine safety constraints:

  1. test_agent_interface       — returns well-formed action dict
  2. test_no_forbidden_imports  — no ML / heavy framework imports in AST
  3. test_no_unshielded_prints  — stdout stays 100% clean during a full game
  4. test_execution_speed       — 99th-percentile step time < 15 ms
"""
from __future__ import annotations

import ast
import io
import os
import sys
import time
import contextlib
from pathlib import Path
from typing import Any, Dict

import pytest

# ---------------------------------------------------------------------------
# Helper — build a minimal observation dict that mirrors the kaggriculture env
# ---------------------------------------------------------------------------

# Allow the evaluator to override which policy file to test via env var.
# When run directly (pytest tests/test_policy_invariants.py) defaults to policy.py.
import os as _os
POLICY_PATH = Path(
    _os.environ.get("KAGGRI_POLICY_PATH", str(Path(__file__).parent.parent / "policy.py"))
)
TOTAL_DAYS = 30


def _minimal_obs(player: int = 0, day: int = 0, hour: int = 0, step: int = 0) -> Dict[str, Any]:
    """Minimal observation that policy.agent() can execute against."""
    tiles: list = [[None] * 10 for _ in range(10)]
    farm = {
        "money": 3000.0,
        "hands": [],
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
        "farmer": [4, 4],
        "tiles": tiles,
    }
    return {
        "player": player,
        "day": day,
        "hour": hour,
        "step": step,
        "farms": [farm, farm],
        "market": {
            "inventory": {
                "WHEAT": 10000, "STRAWBERRY": 10000, "MILK": 10000,
                "WOOL": 10000, "FERTILIZER": 10000, "MELON": 10000,
                "CARROT": 10000, "TOMATO": 10000, "EGG": 10000,
            },
        },
        "private": {
            "shed": {},
            "seeds": {},
            "inventories": [{}],
        },
    }


def _minimal_config() -> Dict[str, Any]:
    return {"episodeSteps": 720, "turnsPerDay": 24}


# ---------------------------------------------------------------------------
# Import policy fresh for each test (avoids cross-test CLAIM_STATE pollution)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def policy_module():
    import importlib
    import importlib.util

    spec = importlib.util.spec_from_file_location("policy_under_test", str(POLICY_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Test 1: Interface contract
# ---------------------------------------------------------------------------

class TestAgentInterface:
    def test_returns_dict_with_required_keys(self, policy_module):
        obs = _minimal_obs(day=0, hour=0)
        config = _minimal_config()
        result = policy_module.agent(obs, config)

        assert isinstance(result, dict), "agent() must return a dict"
        assert "farmer" in result, "result must have 'farmer' key"
        assert "hands" in result, "result must have 'hands' key"
        assert "market" in result, "result must have 'market' key"

    def test_market_orders_within_simulator_cap(self, policy_module):
        """The simulator silently drops orders > 10; we must never emit more."""
        for day in range(0, 30, 5):
            for hour in [0, 6, 12, 18, 23]:
                obs = _minimal_obs(day=day, hour=hour, step=day * 24 + hour)
                config = _minimal_config()
                result = policy_module.agent(obs, config)
                assert len(result["market"]) <= 10, (
                    f"market orders exceeded 10 on day={day} hour={hour}: "
                    f"{result['market']}"
                )

    def test_farmer_action_is_list(self, policy_module):
        obs = _minimal_obs()
        config = _minimal_config()
        result = policy_module.agent(obs, config)
        assert isinstance(result["farmer"], list), "farmer action must be a list"

    def test_hands_is_list(self, policy_module):
        obs = _minimal_obs()
        config = _minimal_config()
        result = policy_module.agent(obs, config)
        assert isinstance(result["hands"], list), "hands must be a list"

    def test_fallback_on_bad_obs(self, policy_module):
        """Malformed observation triggers the except-clause fallback."""
        result = policy_module.agent(None)
        assert isinstance(result, dict)
        assert result.get("farmer") == ["PASS"]


# ---------------------------------------------------------------------------
# Test 2: No forbidden ML/heavy-framework imports in AST
# ---------------------------------------------------------------------------

FORBIDDEN_PACKAGES = {
    "torch", "tensorflow", "tf", "keras", "sklearn",
    "scipy", "lightgbm", "xgboost", "catboost",
    "transformers", "gym", "stable_baselines3",
}


class TestNoForbiddenImports:
    def _collect_imports(self, source: str) -> set[str]:
        """Walk AST and collect all top-level package names imported."""
        tree = ast.parse(source)
        packages: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    packages.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    packages.add(node.module.split(".")[0])
        return packages

    def test_no_ml_imports(self):
        source = POLICY_PATH.read_text()
        packages = self._collect_imports(source)
        violations = FORBIDDEN_PACKAGES & packages
        assert not violations, (
            f"policy.py imports forbidden packages: {violations}. "
            "ML/heavy framework imports are not permitted."
        )

    def test_syntax_valid(self):
        """policy.py must always parse cleanly."""
        source = POLICY_PATH.read_text()
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"policy.py has a syntax error: {e}")


# ---------------------------------------------------------------------------
# Test 3: No stdout pollution during a full game-length execution
# ---------------------------------------------------------------------------

class TestNoUnshieldedPrints:
    def test_stdout_clean_full_game(self, policy_module):
        """Run 720 synthetic steps; not a single byte must appear on stdout."""
        captured = io.StringIO()
        config = _minimal_config()

        with contextlib.redirect_stdout(captured):
            step = 0
            for day in range(TOTAL_DAYS):
                for hour in range(24):
                    obs = _minimal_obs(player=0, day=day, hour=hour, step=step)
                    policy_module.agent(obs, config)
                    step += 1

        output = captured.getvalue()
        assert output == "", (
            f"policy.agent() wrote {len(output)} bytes to stdout across a full "
            f"game. First 200 chars: {output[:200]!r}"
        )


# ---------------------------------------------------------------------------
# Test 4: Execution speed benchmark
# ---------------------------------------------------------------------------

class TestExecutionSpeed:
    def test_per_step_99th_percentile_under_15ms(self, policy_module):
        """99th-percentile step time must be < 15 ms (Kaggle timeout guard)."""
        config = _minimal_config()
        times_ms: list[float] = []

        step = 0
        for day in range(TOTAL_DAYS):
            for hour in range(24):
                obs = _minimal_obs(player=0, day=day, hour=hour, step=step)
                t0 = time.perf_counter()
                policy_module.agent(obs, config)
                elapsed = (time.perf_counter() - t0) * 1000.0
                times_ms.append(elapsed)
                step += 1

        times_ms.sort()
        p99_idx = int(len(times_ms) * 0.99)
        p99 = times_ms[p99_idx]
        p50 = times_ms[len(times_ms) // 2]
        mean_t = sum(times_ms) / len(times_ms)

        print(
            f"\nSpeed: mean={mean_t:.3f}ms  p50={p50:.3f}ms  p99={p99:.3f}ms  "
            f"(n={len(times_ms)} steps, limit=15ms)"
        )

        assert p99 < 15.0, (
            f"99th-percentile step time {p99:.2f}ms exceeds 15ms Kaggle limit. "
            f"mean={mean_t:.2f}ms p50={p50:.2f}ms"
        )
