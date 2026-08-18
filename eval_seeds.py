"""Deterministic, seat-balanced evaluation over a fixed seed set.

Features:
- Dual-seat evaluation (eliminates seat 0 / first-player bias)
- Arbitrary agent & opponent resolution (file paths or built-in names like 'starter')
- Multiprocess parallel execution for fast turnaround
- Comprehensive statistical reporting (mean, median, min, max, stdev, win rate)

Usage:
    python eval_seeds.py [agent.py] [opponent.py] [--seeds N] [--workers W]
    python eval_seeds.py policy.py starter --seeds 10
    python eval_seeds.py policy.py versions/Phase2_v1_policy.py --seeds 5
"""
from __future__ import annotations

import argparse
import math
import os
import statistics
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Tuple

SEEDS = [7, 42, 101, 202, 303, 404, 505, 606, 707, 808, 909, 1001, 1111, 1212, 1313, 1414]


def _resolve_agent(agent_arg: str) -> str:
    """Resolve an agent path or built-in keyword."""
    if agent_arg in ("starter", "random"):
        return agent_arg
    p = Path(agent_arg)
    if p.exists():
        return str(p.resolve())
    # Try finding in root or versions/
    root_p = Path(__file__).parent / agent_arg
    if root_p.exists():
        return str(root_p.resolve())
    versions_p = Path(__file__).parent / "versions" / agent_arg
    if versions_p.exists():
        return str(versions_p.resolve())
    return str(p.resolve())


def _play_single_game(job: Tuple[str, str, int, bool]) -> Tuple[int, int, Optional[float], Optional[float], Optional[str]]:
    """
    Run one game.
    job: (agent_a, agent_b, seed, debug)
    Returns: (seed, seat_of_a, score_a, score_b, error_msg)
    """
    agent_a, agent_b, seed, debug = job
    try:
        from kaggle_environments import make
        env = make("kaggriculture", configuration={"seed": int(seed)})
        env.run([agent_a, agent_b])
        last = env.steps[-1]
        ra = last[0].reward if last[0].reward is not None else 0.0
        rb = last[1].reward if last[1].reward is not None else 0.0
        return seed, 0, float(ra), float(rb), None
    except Exception as e:
        err = traceback.format_exc() if debug else str(e)
        return seed, 0, None, None, err


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic seat-balanced seed evaluator.")
    parser.add_argument("agent", nargs="?", default="policy.py", help="Candidate agent path (default: policy.py)")
    parser.add_argument("opponent", nargs="?", default="starter", help="Opponent agent path or 'starter' (default: starter)")
    parser.add_argument("--seeds", type=int, default=10, help="Number of seeds to test (default: 10)")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2), help="Parallel workers")
    parser.add_argument("--single-seat", action="store_true", help="Evaluate candidate only as Seat 0 (not recommended)")
    parser.add_argument("--debug", action="store_true", help="Print full error tracebacks if games fail")
    args = parser.parse_args()

    agent_path = _resolve_agent(args.agent)
    opp_path = _resolve_agent(args.opponent)

    if agent_path != "starter" and not os.path.exists(agent_path):
        sys.exit(f"Error: Candidate agent not found at '{agent_path}'")
    if opp_path != "starter" and not os.path.exists(opp_path):
        sys.exit(f"Error: Opponent agent not found at '{opp_path}'")

    selected_seeds = SEEDS[:args.seeds] if args.seeds <= len(SEEDS) else list(range(100, 100 + args.seeds))
    name_a = os.path.basename(agent_path)
    name_b = os.path.basename(opp_path)

    print(f"=== Running Deterministic Seed Evaluation ===")
    print(f"Candidate : {name_a}")
    print(f"Opponent  : {name_b}")
    print(f"Seeds ({len(selected_seeds)}): {selected_seeds}")
    print(f"Mode      : {'Single-seat (Seat 0 only)' if args.single_seat else 'Dual-seat (Seat 0 & Seat 1 per seed)'}")
    print(f"Workers   : {args.workers}\n", flush=True)

    jobs = []
    for s in selected_seeds:
        jobs.append((agent_path, opp_path, s, args.debug))  # cand is seat 0
        if not args.single_seat:
            jobs.append((opp_path, agent_path, s, args.debug))  # opp is seat 0, cand is seat 1

    cand_scores: List[float] = []
    opp_scores: List[float] = []
    wins = 0
    losses = 0
    ties = 0
    errors = 0

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(_play_single_game, j) for j in jobs]
        for f in as_completed(futures):
            seed, _, sa, sb, err = f.result()
            if err is not None:
                errors += 1
                if args.debug:
                    print(f"[ERROR] Seed {seed}: {err}")
                continue

    # Run in structured sequence for orderly reporting
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        for s in selected_seeds:
            # Seat 0 run
            f0 = executor.submit(_play_single_game, (agent_path, opp_path, s, args.debug))
            _, _, r0_a, r0_b, err0 = f0.result()

            if args.single_seat:
                if r0_a is not None and r0_b is not None:
                    cand_scores.append(r0_a)
                    opp_scores.append(r0_b)
                    if r0_a > r0_b:
                        wins += 1
                    elif r0_a < r0_b:
                        losses += 1
                    else:
                        ties += 1
                    print(f"seed {s:5d} | {name_a:>9,.0f} vs {name_b:>9,.0f} | Δ = {r0_a - r0_b:+9,.0f}")
                continue

            # Seat 1 run
            f1 = executor.submit(_play_single_game, (opp_path, agent_path, s, args.debug))
            _, _, r1_opp, r1_cand, err1 = f1.result()

            if r0_a is not None and r0_b is not None and r1_cand is not None and r1_opp is not None:
                cand_scores.extend([r0_a, r1_cand])
                opp_scores.extend([r0_b, r1_opp])
                if r0_a > r0_b:
                    wins += 1
                elif r0_a < r0_b:
                    losses += 1
                else:
                    ties += 1

                if r1_cand > r1_opp:
                    wins += 1
                elif r1_cand < r1_opp:
                    losses += 1
                else:
                    ties += 1

                pair_cand_avg = (r0_a + r1_cand) / 2.0
                pair_opp_avg = (r0_b + r1_opp) / 2.0
                print(f"seed {s:5d} | S0: {r0_a:>8,.0f} vs {r0_b:>8,.0f} | S1: {r1_cand:>8,.0f} vs {r1_opp:>8,.0f} | Mean Δ: {pair_cand_avg - pair_opp_avg:+8,.0f}")

    if not cand_scores:
        sys.exit(f"\nAll evaluation runs failed with errors ({errors} errors).")

    n_games = len(cand_scores)
    mean_cand = statistics.mean(cand_scores)
    mean_opp = statistics.mean(opp_scores)
    median_cand = statistics.median(cand_scores)
    median_opp = statistics.median(opp_scores)
    stdev_cand = statistics.stdev(cand_scores) if n_games > 1 else 0.0

    print("\n" + "=" * 65)
    print(f"SUMMARY: {name_a} vs {name_b} ({n_games} games)")
    print("=" * 65)
    print(f"Win/Loss/Tie : {wins}W - {losses}L - {ties}T (Win Rate: {wins / n_games * 100:.1f}%)")
    print(f"{name_a:<20} Mean: {mean_cand:>10,.0f} | Median: {median_cand:>10,.0f} | SD: {stdev_cand:>8,.0f}")
    print(f"{name_b:<20} Mean: {mean_opp:>10,.0f} | Median: {median_opp:>10,.0f}")
    print(f"Mean Advantage (Δ)  : {mean_cand - mean_opp:+10,.0f}")
    print(f"Score Range (Min/Max): {min(cand_scores):>10,.0f} .. {max(cand_scores):>10,.0f}")
    if errors > 0:
        print(f"Warnings/Errors     : {errors} game(s) errored")
    print("=" * 65)


if __name__ == "__main__":
    main()
