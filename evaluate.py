"""Multi-game A/B evaluation harness — removes seat bias and seed variance.

Every pairing is played on N seeds, both seats, so each agent plays the same
seeds from both sides. Reports mean score, win rate, and a paired t-test so
we stop chasing single-game noise.

Usage:
    python evaluate.py main.py v3_good.py --games 8
    python evaluate.py main.py v3_good.py v2.py --games 6      # round-robin
"""
import argparse, os, sys, itertools, statistics, math
from concurrent.futures import ProcessPoolExecutor


def _play(job):
    """Run one game. job = (path_a, path_b, seed). Returns (score_a, score_b)."""
    path_a, path_b, seed = job
    from kaggle_environments import make
    try:
        env = make("kaggriculture", configuration={"seed": int(seed)})
        env.run([path_a, path_b])
        last = env.steps[-1]
        ra = last[0].reward if last[0].reward is not None else 0.0
        rb = last[1].reward if last[1].reward is not None else 0.0
        return float(ra), float(rb)
    except Exception as e:
        return None, None


def head_to_head(a, b, games, workers):
    """Play `games` seeds, each twice (a first, then b first)."""
    seeds = list(range(1000, 1000 + games))
    jobs = [(a, b, s) for s in seeds] + [(b, a, s) for s in seeds]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(_play, jobs))

    a_scores, b_scores, a_wins, ties, failed = [], [], 0, 0, 0
    n = len(seeds)
    for i, (r0, r1) in enumerate(results):
        if r0 is None:
            failed += 1
            continue
        # first half: a is seat 0.  second half: b is seat 0.
        sa, sb = (r0, r1) if i < n else (r1, r0)
        a_scores.append(sa)
        b_scores.append(sb)
        if sa > sb:
            a_wins += 1
        elif sa == sb:
            ties += 1
    return a_scores, b_scores, a_wins, ties, failed


def paired_t(a_scores, b_scores):
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
    ap = argparse.ArgumentParser()
    ap.add_argument("agents", nargs="+", help="agent .py paths (2+ for round-robin)")
    ap.add_argument("--games", type=int, default=8,
                    help="seeds per pairing (each played twice, both seats)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    args = ap.parse_args()

    paths = [os.path.abspath(p) for p in args.agents]
    for p in paths:
        if not os.path.exists(p):
            sys.exit(f"missing agent: {p}")

    print(f"{args.games} seeds x 2 seats = {args.games*2} games per pairing, "
          f"{args.workers} workers\n")

    for a, b in itertools.combinations(paths, 2):
        na, nb = os.path.basename(a), os.path.basename(b)
        print(f"=== {na}  vs  {nb} ===", flush=True)
        A, B, wins, ties, failed = head_to_head(a, b, args.games, args.workers)
        if not A:
            print("  all games failed\n")
            continue
        n = len(A)
        t, p = paired_t(A, B)
        ma, mb = statistics.mean(A), statistics.mean(B)
        print(f"  {na:<20} mean {ma:>9,.0f}   median {statistics.median(A):>9,.0f}")
        print(f"  {nb:<20} mean {mb:>9,.0f}   median {statistics.median(B):>9,.0f}")
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
