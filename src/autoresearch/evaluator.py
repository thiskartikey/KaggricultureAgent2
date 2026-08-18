"""Adaptive multi-stage falsification cascade for KaggriRatchet.

Stage 0 — Invariant gate   (0 s): AST/syntax/speed check via test_policy_invariants
Stage 1 — Fast screen    (~15 s): 2 seeds / 4 games — reject if Δ < -2000 or crash
Stage 2 — Confirm screen (~45 s): 8 seeds / 16 games — reject if Δ ≤ 0
Stage 3 — Champion gate (~110 s): 16 seeds / 32 games — full stats, strict thresholds

Usage:
    from src.autoresearch.evaluator import evaluate
    verdict = evaluate("candidate_policy.py", "baseline_policy.py")
"""
from __future__ import annotations

import math
import os
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Optional, Tuple

from src.autoresearch.stats import full_stats

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STAGE_CONFIG = {
    1: {"seeds": 2,  "games_per_seed": 2, "reject_delta": -2000, "reject_on_zero": True},
    2: {"seeds": 8,  "games_per_seed": 2, "reject_delta": 0,     "reject_on_zero": True},
    3: {"seeds": 16, "games_per_seed": 2, "reject_delta": None,  "reject_on_zero": False},
}

# Stage 3 champion-gate thresholds
STAGE3_P_TTEST = 0.05
STAGE3_P_WILCOXON = 0.05
STAGE3_COHENS_D = 0.20
STAGE3_WORST_CASE_DROP = 0.05   # candidate's worst game may not be > 5% below baseline min


def _play_one(job: Tuple[str, str, int]) -> Tuple[Optional[float], Optional[float]]:
    """Worker: run one game.  Returns (score_a, score_b) or (None, None) on error."""
    path_a, path_b, seed = job
    try:
        from kaggle_environments import make
        env = make("kaggriculture", configuration={"seed": int(seed)})
        env.run([path_a, path_b])
        last = env.steps[-1]
        ra = last[0].reward if last[0].reward is not None else 0.0
        rb = last[1].reward if last[1].reward is not None else 0.0
        return float(ra), float(rb)
    except Exception:
        return None, None


def _run_games(
    candidate: str,
    baseline: str,
    seeds: list[int],
    workers: int,
) -> Tuple[list[float], list[float], int]:
    """Play every seed in both seats.  Returns (cand_scores, base_scores, n_failed)."""
    jobs = (
        [(candidate, baseline, s) for s in seeds]
        + [(baseline, candidate, s) for s in seeds]
    )
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_play_one, j): j for j in jobs}
        for fut in as_completed(futures):
            results.append((futures[fut], fut.result()))

    n = len(seeds)
    # Re-sort results by (seed, seat) order to keep pairing consistent
    job_result = {j: r for j, r in results}
    cand_scores, base_scores, failed = [], [], 0
    for i, seed in enumerate(seeds):
        # seat 0 = candidate first
        ra, rb = job_result.get((candidate, baseline, seed), (None, None))
        if ra is None:
            failed += 1
            continue
        cand_scores.append(ra)
        base_scores.append(rb)
    for i, seed in enumerate(seeds):
        # seat 1 = baseline first
        ra, rb = job_result.get((baseline, candidate, seed), (None, None))
        if ra is None:
            failed += 1
            continue
        cand_scores.append(rb)
        base_scores.append(ra)
    return cand_scores, base_scores, failed


# ---------------------------------------------------------------------------
# Stage 0: Invariant gate — runs pytest test_policy_invariants on the candidate
# ---------------------------------------------------------------------------

def stage0_invariant_gate(candidate_path: str) -> Tuple[bool, str]:
    """Run the policy invariant tests against the candidate.

    Returns (passed: bool, message: str).
    """
    test_file = Path(__file__).parent.parent.parent / "tests" / "test_policy_invariants.py"
    if not test_file.exists():
        return False, f"test_policy_invariants.py not found at {test_file}"

    # Pass candidate path via env var so the test module can pick it up
    # without needing a conftest.py or custom pytest plugin.
    import os as _os
    env = {**_os.environ, "KAGGRI_POLICY_PATH": candidate_path}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file),
         "--tb=short", "-q"],
        capture_output=True, text=True, timeout=60,
        cwd=str(Path(__file__).parent.parent.parent),
        env=env,
    )
    passed = result.returncode == 0
    msg = result.stdout + result.stderr
    return passed, msg


# ---------------------------------------------------------------------------
# Multi-stage evaluation
# ---------------------------------------------------------------------------

def evaluate(
    candidate: str,
    baseline: str,
    skip_stage0: bool = False,
    workers: Optional[int] = None,
    seed_offset: int = 1000,
) -> Dict:
    """Run the adaptive falsification cascade.

    Returns a result dict with keys:
      decision    — "KEEP" | "REJECT"
      stage       — last stage reached (0-3)
      reason      — human-readable rejection/acceptance reason
      stats       — full_stats() dict (if Stage 3 reached)
      timings     — wall-clock seconds per stage
    """
    t_start = time.perf_counter()
    candidate = str(Path(candidate).absolute())
    baseline = str(Path(baseline).absolute())
    workers = workers or max(1, (os.cpu_count() or 4) - 2)

    result = {
        "candidate": candidate,
        "baseline": baseline,
        "decision": "REJECT",
        "stage": 0,
        "reason": "",
        "stats": None,
        "timings": {},
        "game_data": {},
    }

    # ── Stage 0 ──────────────────────────────────────────────────────────────
    t0 = time.perf_counter()
    if not skip_stage0:
        passed, msg = stage0_invariant_gate(candidate)
        result["timings"]["stage0"] = time.perf_counter() - t0
        if not passed:
            result["reason"] = f"Stage 0 FAIL — invariant tests failed:\n{msg[:500]}"
            return result
    else:
        result["timings"]["stage0"] = 0.0

    # ── Stages 1-3 ───────────────────────────────────────────────────────────
    all_cand: list[float] = []
    all_base: list[float] = []

    for stage_n in (1, 2, 3):
        cfg = STAGE_CONFIG[stage_n]
        n_seeds = cfg["seeds"]
        new_seeds = list(range(seed_offset + len(all_cand) // 2, seed_offset + n_seeds))

        ts = time.perf_counter()
        cand_s, base_s, failed = _run_games(candidate, baseline, new_seeds, workers)
        result["timings"][f"stage{stage_n}"] = time.perf_counter() - ts

        all_cand += cand_s
        all_base += base_s

        result["stage"] = stage_n
        result["game_data"][f"stage{stage_n}"] = {
            "cand_scores": list(all_cand),
            "base_scores": list(all_base),
            "failed": failed,
        }

        if not all_cand:
            result["reason"] = f"Stage {stage_n} FAIL — all games crashed or timed out"
            return result

        delta = statistics.mean(all_cand) - statistics.mean(all_base)

        if stage_n in (1, 2):
            threshold = cfg["reject_delta"]
            if delta <= threshold:
                result["reason"] = (
                    f"Stage {stage_n} REJECT — Δmean={delta:+.0f} ≤ threshold {threshold}"
                )
                return result

        if stage_n == 3:
            stats = full_stats(all_cand, all_base)
            result["stats"] = stats

            fail_reasons = []
            if stats["p_ttest"] >= STAGE3_P_TTEST:
                fail_reasons.append(
                    f"p_ttest={stats['p_ttest']:.3f} ≥ {STAGE3_P_TTEST}"
                )
            if stats["p_wilcoxon"] >= STAGE3_P_WILCOXON:
                fail_reasons.append(
                    f"p_wilcoxon={stats['p_wilcoxon']:.3f} ≥ {STAGE3_P_WILCOXON}"
                )
            if stats["cohens_d"] < STAGE3_COHENS_D:
                fail_reasons.append(
                    f"cohens_d={stats['cohens_d']:.3f} < {STAGE3_COHENS_D}"
                )
            if stats["delta_mean"] <= 0:
                fail_reasons.append(
                    f"delta_mean={stats['delta_mean']:+.0f} ≤ 0"
                )
            # Worst-case drop guard: candidate's worst game vs baseline's worst game.
            # Guards against catastrophic crashes/regressions, not normal seed variance.
            if all_cand and all_base:
                base_min = min(all_base)
                cand_min = min(all_cand)
                if base_min > 0 and (base_min - cand_min) / base_min > STAGE3_WORST_CASE_DROP:
                    fail_reasons.append(
                        f"worst-case drop {(base_min-cand_min)/base_min:.1%} > "
                        f"{STAGE3_WORST_CASE_DROP:.0%} vs baseline worst"
                    )

            if fail_reasons:
                result["reason"] = "Stage 3 REJECT — " + "; ".join(fail_reasons)
                return result

            result["decision"] = "KEEP"
            result["reason"] = (
                f"Stage 3 PASS — Δmean={delta:+.0f}  "
                f"p_t={stats['p_ttest']:.3f}  "
                f"p_w={stats['p_wilcoxon']:.3f}  "
                f"d={stats['cohens_d']:.2f}"
            )

    result["timings"]["total"] = time.perf_counter() - t_start
    return result
