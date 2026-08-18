"""Stage 4 — Opponent-pool evaluator for KaggriRatchet.

Addresses the self-play evaluation blind spot: the main evaluator tests
candidate vs the current champion only.  Improvements that are invisible in
self-play (e.g. better fertiliser routing, earlier endgame planting) can only
be detected by running against diverse opponents that actually stress-test the
fixed behaviour.

Pool composition (configured in POOL below):
  1. Historical champion archive (versions/ — 5 spread checkpoints)
  2. Opponent clones built from replay decision-rule analysis (opponent_clones/)

Usage — standalone check:
    python -m src.autoresearch.pool_evaluator policy.py

Usage — programmatic (returns a dict, same shape as main evaluator):
    from src.autoresearch.pool_evaluator import evaluate_vs_pool
    result = evaluate_vs_pool("candidate.py")
"""
from __future__ import annotations

import os
import statistics
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Pool configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Historical champion checkpoints — spread across the improvement history.
# These are guaranteed to exist (they are committed to the repo).
_HIST_POOL_RELATIVE = [
    "versions/Phase2_v1_policy.py",          # ~48k  early-phase2 baseline
    "versions/Phase2_v7_policy.py",           # ~54k  dropoff-fix era
    "versions/Phase2_v11_policy.py",          # ~60k  fertilize-tier1 era
    "versions/EXP-20260814-12_policy.py",     # ~65k  early ratchet
    "versions/EXP-20260815-69_policy.py",     # ~73k  current champion
]

# Opponent clones directory — clones built from top-player replay analysis.
# Each file in this directory is auto-added to the pool if it exists.
_CLONES_DIR = PROJECT_ROOT / "opponent_clones"

# Seeds used exclusively for pool evaluation — distinct from self-play seeds
# (1000-1032) so results are never confounded.
_POOL_SEED_OFFSET = 6000
_POOL_SEEDS_PER_OPPONENT = 4   # 8 games/opponent (2 seats); pool of 5 = 40 games

# Thresholds for the pool gate
POOL_MIN_ABSOLUTE_SCORE = 60_000   # candidate must average ≥ 60k across pool games
POOL_MIN_WIN_RATE_VS_STRONG = 0.40 # must win ≥ 40% of games vs strong pool members (≥65k)
POOL_STRONG_THRESHOLD = 65_000     # what counts as a "strong" pool member


def _build_pool() -> List[str]:
    """Return absolute paths for all pool agents that exist on disk."""
    pool: List[str] = []
    for rel in _HIST_POOL_RELATIVE:
        p = PROJECT_ROOT / rel
        if p.exists():
            pool.append(str(p))
    if _CLONES_DIR.exists():
        for f in sorted(_CLONES_DIR.glob("*.py")):
            pool.append(str(f))
    return pool


def _play_one_pool(job: Tuple[str, str, int]) -> Tuple[Optional[float], Optional[float]]:
    """Worker: play one game, return (score_a, score_b) or (None, None)."""
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


def _run_vs_opponent(
    candidate: str,
    opponent: str,
    seeds: List[int],
    workers: int,
) -> Tuple[List[float], List[float], int]:
    """Play candidate vs one opponent in both seats.  Returns (cand, opp, failed)."""
    jobs = (
        [(candidate, opponent, s) for s in seeds]
        + [(opponent, candidate, s) for s in seeds]
    )
    job_result: Dict = {}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_play_one_pool, j): j for j in jobs}
        for fut in as_completed(futures):
            job_result[futures[fut]] = fut.result()

    cand_scores, opp_scores, failed = [], [], 0
    for seed in seeds:
        ra, rb = job_result.get((candidate, opponent, seed), (None, None))
        if ra is None:
            failed += 1
        else:
            cand_scores.append(ra)
            opp_scores.append(rb)
    for seed in seeds:
        ra, rb = job_result.get((opponent, candidate, seed), (None, None))
        if ra is None:
            failed += 1
        else:
            cand_scores.append(rb)
            opp_scores.append(ra)
    return cand_scores, opp_scores, failed


# ---------------------------------------------------------------------------
# Opponent-strength cache (keyed by absolute path)
# ---------------------------------------------------------------------------
_strength_cache: Dict[str, float] = {}


def _estimate_strength(path: str, workers: int) -> float:
    """Estimate opponent strength: play 4 seeds vs Phase2_v1 and return mean score.

    Cached so repeated calls don't re-run games.
    """
    if path in _strength_cache:
        return _strength_cache[path]
    baseline = str(PROJECT_ROOT / "versions/Phase2_v1_policy.py")
    if not Path(baseline).exists() or path == baseline:
        _strength_cache[path] = 0.0
        return 0.0
    seeds = list(range(7000, 7004))
    c, _, _ = _run_vs_opponent(path, baseline, seeds, workers)
    strength = statistics.mean(c) if c else 0.0
    _strength_cache[path] = strength
    return strength


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_vs_pool(
    candidate: str,
    pool: Optional[List[str]] = None,
    seeds_per_opponent: int = _POOL_SEEDS_PER_OPPONENT,
    workers: Optional[int] = None,
    verbose: bool = True,
) -> Dict:
    """Evaluate candidate against every opponent in the pool.

    Returns a dict:
        decision          — "KEEP" | "REJECT"
        reason            — human-readable explanation
        mean_score        — candidate mean score across all pool games
        win_rate_overall  — fraction of pool games candidate wins
        win_rate_vs_strong — fraction of games vs strong opponents won
        per_opponent      — {opponent_name: {delta, win_rate, n}} for each member
        timing            — wall-clock seconds
    """
    t0 = time.perf_counter()
    candidate = str(Path(candidate).absolute())
    workers = workers or max(1, (os.cpu_count() or 4) - 2)

    if pool is None:
        pool = _build_pool()

    if not pool:
        return {
            "decision": "SKIP",
            "reason": "Pool is empty — no opponent files found",
            "mean_score": 0.0,
            "win_rate_overall": 0.0,
            "win_rate_vs_strong": 0.0,
            "per_opponent": {},
            "timing": 0.0,
        }

    all_cand: List[float] = []
    all_wins: List[int] = []
    strong_wins: List[int] = []
    strong_total: int = 0
    per_opp: Dict[str, Dict] = {}
    fail_reasons: List[str] = []

    seeds = list(range(_POOL_SEED_OFFSET, _POOL_SEED_OFFSET + seeds_per_opponent))

    for opp_path in pool:
        opp_name = Path(opp_path).stem
        if verbose:
            print(f"  Pool: vs {opp_name} ...", end=" ", flush=True)

        c_scores, o_scores, failed = _run_vs_opponent(candidate, opp_path, seeds, workers)
        if not c_scores:
            if verbose:
                print("CRASHED")
            per_opp[opp_name] = {"delta": None, "win_rate": None, "n": 0, "failed": failed}
            continue

        delta = statistics.mean(c_scores) - statistics.mean(o_scores)
        win_rate = sum(c > o for c, o in zip(c_scores, o_scores)) / len(c_scores)
        strength = _estimate_strength(opp_path, workers)
        is_strong = strength >= POOL_STRONG_THRESHOLD

        per_opp[opp_name] = {
            "delta": delta,
            "win_rate": win_rate,
            "n": len(c_scores),
            "failed": failed,
            "strength": strength,
        }
        all_cand.extend(c_scores)
        all_wins.extend(1 if c > o else 0 for c, o in zip(c_scores, o_scores))

        if is_strong:
            strong_wins.extend(1 if c > o else 0 for c, o in zip(c_scores, o_scores))
            strong_total += len(c_scores)

        if verbose:
            print(f"Δ={delta:+.0f}  wr={win_rate:.0%}  {'[strong]' if is_strong else ''}")

    mean_score = statistics.mean(all_cand) if all_cand else 0.0
    win_rate_overall = statistics.mean(all_wins) if all_wins else 0.0
    win_rate_vs_strong = (
        sum(strong_wins) / strong_total if strong_total > 0 else None
    )

    # Gate checks
    if mean_score < POOL_MIN_ABSOLUTE_SCORE:
        fail_reasons.append(
            f"mean_score={mean_score:,.0f} < floor {POOL_MIN_ABSOLUTE_SCORE:,}"
        )
    if win_rate_vs_strong is not None and win_rate_vs_strong < POOL_MIN_WIN_RATE_VS_STRONG:
        fail_reasons.append(
            f"win_rate_vs_strong={win_rate_vs_strong:.1%} < {POOL_MIN_WIN_RATE_VS_STRONG:.0%}"
        )

    decision = "REJECT" if fail_reasons else "KEEP"
    reason = (
        "Pool REJECT — " + "; ".join(fail_reasons) if fail_reasons else
        f"Pool PASS — mean={mean_score:,.0f}  wr={win_rate_overall:.1%}"
        + (f"  wr_strong={win_rate_vs_strong:.1%}" if win_rate_vs_strong is not None else "")
    )

    return {
        "decision": decision,
        "reason": reason,
        "mean_score": mean_score,
        "win_rate_overall": win_rate_overall,
        "win_rate_vs_strong": win_rate_vs_strong,
        "per_opponent": per_opp,
        "timing": time.perf_counter() - t0,
    }


def format_pool_summary(result: Dict) -> str:
    """Format a pool evaluation result dict into human-readable summary string."""
    lines = [
        f"\nDecision:          {result['decision']}",
        f"Reason:            {result['reason']}",
        f"Mean score (pool): {result['mean_score']:,.0f}",
        f"Win rate overall:  {result['win_rate_overall']:.1%}",
    ]
    if result["win_rate_vs_strong"] is not None:
        lines.append(f"Win rate vs strong:{result['win_rate_vs_strong']:.1%}")
    lines.append(f"Timing:            {result['timing']:.1f}s")
    lines.append("\nPer-opponent breakdown:")
    for name, d in result["per_opponent"].items():
        if d["delta"] is not None:
            lines.append(f"  {name:<40} Δ={d['delta']:+6.0f}  wr={d['win_rate']:.0%}  n={d['n']}")
        else:
            lines.append(f"  {name:<40} CRASHED")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse, json, sys
    ap = argparse.ArgumentParser(description="Stage 4 opponent-pool evaluator")
    ap.add_argument("candidate", help="Path to candidate policy.py")
    ap.add_argument("--seeds-per-opponent", type=int, default=_POOL_SEEDS_PER_OPPONENT)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--json", action="store_true", help="Output raw JSON")
    args = ap.parse_args()

    result = evaluate_vs_pool(
        args.candidate,
        seeds_per_opponent=args.seeds_per_opponent,
        workers=args.workers,
        verbose=not args.json,
    )

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(format_pool_summary(result))

    sys.exit(0 if result["decision"] == "KEEP" else 1)


if __name__ == "__main__":
    main()
