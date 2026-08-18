"""Multi-game A/B evaluation harness — removes seat bias and seed variance.

Every pairing is played on N seeds, both seats, so each agent plays the same
seeds from both sides. Reports mean score, win rate, and a paired t-test so
we stop chasing single-game noise.

Usage:
    python evaluate.py policy.py versions/Phase2_v1_policy.py --games 8
    python evaluate.py policy.py versions/Phase2_v7_policy.py versions/Phase2_v11_policy.py --games 6
    python evaluate.py policy.py --pool
"""
from __future__ import annotations

import argparse
import itertools
import math
import os
import statistics
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import List, Optional, Tuple


def _resolve_path(p: str) -> str:
    if p in ("starter", "random"):
        return p
    if os.path.exists(p):
        return os.path.abspath(p)
    alt = os.path.join(os.path.dirname(__file__), p)
    if os.path.exists(alt):
        return os.path.abspath(alt)
    alt_v = os.path.join(os.path.dirname(__file__), "versions", p)
    if os.path.exists(alt_v):
        return os.path.abspath(alt_v)
    return os.path.abspath(p)


def _play(job: Tuple[str, str, int, bool]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """Run one game. job = (path_a, path_b, seed, debug). Returns (score_a, score_b, error_msg)."""
    path_a, path_b, seed, debug = job
    from kaggle_environments import make
    try:
        env = make("kaggriculture", configuration={"seed": int(seed)})
        env.run([path_a, path_b])
        last = env.steps[-1]
        ra = last[0].reward if last[0].reward is not None else 0.0
        rb = last[1].reward if last[1].reward is not None else 0.0
        return float(ra), float(rb), None
    except Exception as e:
        err = traceback.format_exc() if debug else str(e)
        return None, None, err


def head_to_head(a: str, b: str, games: int, workers: int, debug: bool = False):
    """Play `games` seeds, each twice (a first, then b first)."""
    seeds = list(range(1000, 1000 + games))
    jobs = [(a, b, s, debug) for s in seeds] + [(b, a, s, debug) for s in seeds]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(_play, jobs))

    a_scores, b_scores, a_wins, ties, failed = [], [], 0, 0, 0
    n = len(seeds)
    for i, (r0, r1, err) in enumerate(results):
        if r0 is None:
            failed += 1
            if debug and err:
                print(f"  [ERROR in game {i}]: {err}")
            continue
        # first half: a is seat 0. second half: b is seat 0.
        sa, sb = (r0, r1) if i < n else (r1, r0)
        a_scores.append(sa)
        b_scores.append(sb)
        if sa > sb:
            a_wins += 1
        elif sa == sb:
            ties += 1
    return a_scores, b_scores, a_wins, ties, failed


def paired_t(a_scores: List[float], b_scores: List[float]) -> Tuple[float, float]:
    """Paired t-statistic and rough two-sided p-value for mean(a-b) != 0."""
    d = [x - y for x, y in zip(a_scores, b_scores)]
    n = len(d)
    if n < 2:
        return 0.0, 1.0
    m = statistics.mean(d)
    sd = statistics.stdev(d)
    if sd == 0:
        return (math.inf if m else 0.0), (0.0 if m else 1.0)
    t = m / (sd / math.sqrt(n))
    # normal approximation to the two-sided p-value (fine for n >= 8)
    p = math.erfc(abs(t) / math.sqrt(2))
    return t, p


def main():
    ap = argparse.ArgumentParser(description="Multi-game A/B evaluation harness.")
    ap.add_argument("agents", nargs="*", default=["policy.py"], help="agent .py paths (2+ for round-robin, 1 for pool)")
    ap.add_argument("--games", type=int, default=8, help="seeds per pairing (each played twice, both seats)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument("--pool", action="store_true", help="Evaluate single agent vs historical opponent pool")
    ap.add_argument("--debug", action="store_true", help="Print debug exception tracebacks")
    args = ap.parse_args()

    if args.pool or len(args.agents) == 1:
        target = _resolve_path(args.agents[0] if args.agents else "policy.py")
        if not os.path.exists(target):
            sys.exit(f"Target agent not found: {target}")
        print(f"=== Running Opponent Pool Evaluation for {os.path.basename(target)} ===")
        from src.autoresearch.pool_evaluator import evaluate_vs_pool, format_pool_summary
        result = evaluate_vs_pool(target, workers=args.workers)
        print(format_pool_summary(result))
        return

    paths = [_resolve_path(p) for p in args.agents]
    for p in paths:
        if p not in ("starter", "random") and not os.path.exists(p):
            sys.exit(f"Missing agent: {p}")

    print(f"{args.games} seeds x 2 seats = {args.games*2} games per pairing, "
          f"{args.workers} workers\n")

    for a, b in itertools.combinations(paths, 2):
        na, nb = os.path.basename(a), os.path.basename(b)
        print(f"=== {na}  vs  {nb} ===", flush=True)
        A, B, wins, ties, failed = head_to_head(a, b, args.games, args.workers, debug=args.debug)
        if not A:
            print("  all games failed\n")
            continue
        n = len(A)
        t, p = paired_t(A, B)
        ma, mb = statistics.mean(A), statistics.mean(B)
        print(f"  {na:<25} mean {ma:>9,.0f}   median {statistics.median(A):>9,.0f}")
        print(f"  {nb:<25} mean {mb:>9,.0f}   median {statistics.median(B):>9,.0f}")
        print(f"  diff {ma-mb:+,.0f}   {na} wins {wins}/{n}"
              + (f" ({ties} ties)" if ties else ""))
        verdict = ("SIGNIFICANT" if p < 0.05 else
                   "leaning" if p < 0.20 else "NOISE — no real difference")
        print(f"  paired t={t:+.2f}  p={p:.3f}  ->  {verdict}")
        if failed:
            print(f"  WARNING: {failed} games errored and were dropped")
        print(flush=True)


if __name__ == "__main__":
    main()
