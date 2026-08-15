"""Statistical test suite for the KaggriRatchet evaluation harness.

Implements:
  - Paired Student's t-test
  - Wilcoxon signed-rank test (non-parametric, no scipy dependency)
  - Cohen's d effect size
  - 95% Bootstrap confidence interval on mean delta

All functions are pure Python + math; zero external dependencies.
"""
from __future__ import annotations

import math
import random
import statistics
from typing import Sequence, Tuple


# ---------------------------------------------------------------------------
# Paired t-test
# ---------------------------------------------------------------------------

def paired_ttest(a: Sequence[float], b: Sequence[float]) -> Tuple[float, float]:
    """Paired two-sided t-test for H0: mean(a - b) = 0.

    Returns (t_stat, p_value).  p_value uses the normal approximation
    (valid for n >= 8; conservative for small n).
    """
    d = [x - y for x, y in zip(a, b)]
    n = len(d)
    if n < 2:
        return 0.0, 1.0
    m = statistics.mean(d)
    sd = statistics.stdev(d)
    if sd == 0:
        return (math.inf if m > 0 else (-math.inf if m < 0 else 0.0)), (0.0 if m != 0 else 1.0)
    t = m / (sd / math.sqrt(n))
    # Two-sided p via complementary error function (normal approximation)
    p = math.erfc(abs(t) / math.sqrt(2))
    return t, p


# ---------------------------------------------------------------------------
# Wilcoxon signed-rank test
# ---------------------------------------------------------------------------

def wilcoxon_signed_rank(a: Sequence[float], b: Sequence[float]) -> Tuple[float, float]:
    """Non-parametric Wilcoxon signed-rank test (two-sided).

    Returns (W_statistic, p_value).
    Uses the normal approximation for the test statistic (valid for n >= 10).
    Zero differences are excluded per Wilcoxon's original recommendation.
    """
    d = [x - y for x, y in zip(a, b) if x != y]
    n = len(d)
    if n == 0:
        return 0.0, 1.0

    # Rank absolute differences
    abs_d = sorted(range(n), key=lambda i: abs(d[i]))
    ranks = [0.0] * n

    # Assign average ranks for ties
    i = 0
    while i < n:
        j = i + 1
        while j < n and abs(d[abs_d[j]]) == abs(d[abs_d[i]]):
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[abs_d[k]] = avg_rank
        i = j

    # W+ and W-
    w_plus = sum(ranks[i] for i in range(n) if d[i] > 0)
    w_minus = sum(ranks[i] for i in range(n) if d[i] < 0)
    w_stat = float(min(w_plus, w_minus))

    # Normal approximation
    mu = n * (n + 1) / 4.0
    sigma2 = n * (n + 1) * (2 * n + 1) / 24.0
    if sigma2 <= 0:
        return w_stat, 1.0
    z = (w_stat - mu) / math.sqrt(sigma2)
    p = math.erfc(abs(z) / math.sqrt(2))
    return w_stat, p


# ---------------------------------------------------------------------------
# Cohen's d
# ---------------------------------------------------------------------------

def cohens_d(a: Sequence[float], b: Sequence[float]) -> float:
    """Paired Cohen's d: mean difference / pooled SD of differences.

    Effect size conventions: small ~0.2, medium ~0.5, large ~0.8.
    Returns 0.0 when SD is zero (identical distributions).
    """
    d = [x - y for x, y in zip(a, b)]
    if len(d) < 2:
        return 0.0
    m = statistics.mean(d)
    sd = statistics.stdev(d)
    return m / sd if sd > 0 else 0.0


# ---------------------------------------------------------------------------
# Bootstrap 95% CI on mean delta
# ---------------------------------------------------------------------------

def bootstrap_ci(
    a: Sequence[float],
    b: Sequence[float],
    n_boot: int = 2000,
    confidence: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float]:
    """Bootstrap confidence interval on mean(a - b).

    Returns (lower, upper) bounds at the requested confidence level.
    Uses paired resampling (resample pairs together).
    """
    rng = random.Random(seed)
    diffs = [x - y for x, y in zip(a, b)]
    n = len(diffs)
    if n < 2:
        m = statistics.mean(diffs) if diffs else 0.0
        return m, m

    boot_means = []
    for _ in range(n_boot):
        sample = [rng.choice(diffs) for _ in range(n)]
        boot_means.append(statistics.mean(sample))
    boot_means.sort()

    alpha = 1.0 - confidence
    lo_idx = int(math.floor(alpha / 2 * n_boot))
    hi_idx = int(math.ceil((1 - alpha / 2) * n_boot)) - 1
    return boot_means[lo_idx], boot_means[hi_idx]


# ---------------------------------------------------------------------------
# Composite verdict
# ---------------------------------------------------------------------------

def full_stats(a: Sequence[float], b: Sequence[float]) -> dict:
    """Return all statistics for a vs b score lists in one dict."""
    if not a or not b:
        return {"error": "empty score lists"}
    t, p_t = paired_ttest(a, b)
    w, p_w = wilcoxon_signed_rank(a, b)
    d = cohens_d(a, b)
    ci_lo, ci_hi = bootstrap_ci(a, b)
    mean_a = statistics.mean(a)
    mean_b = statistics.mean(b)
    return {
        "n": len(a),
        "mean_a": mean_a,
        "mean_b": mean_b,
        "delta_mean": mean_a - mean_b,
        "t_stat": t,
        "p_ttest": p_t,
        "w_stat": w,
        "p_wilcoxon": p_w,
        "cohens_d": d,
        "ci_95_lo": ci_lo,
        "ci_95_hi": ci_hi,
    }
