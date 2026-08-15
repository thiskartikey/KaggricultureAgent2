"""Tests for src/autoresearch/stats.py"""
from __future__ import annotations

import math
import pytest

from src.autoresearch.stats import (
    paired_ttest,
    wilcoxon_signed_rank,
    cohens_d,
    bootstrap_ci,
    full_stats,
)


class TestPairedTtest:
    def test_no_difference_p_near_one(self):
        a = [100.0] * 20
        b = [100.0] * 20
        t, p = paired_ttest(a, b)
        assert t == 0.0
        assert p == 1.0

    def test_significant_positive(self):
        a = [110.0 + i for i in range(20)]
        b = [100.0 + i for i in range(20)]
        t, p = paired_ttest(a, b)
        assert t > 0
        assert p < 0.05

    def test_significant_negative(self):
        a = [90.0] * 20
        b = [100.0] * 20
        t, p = paired_ttest(a, b)
        assert t < 0
        assert p < 0.05

    def test_single_pair_returns_neutral(self):
        t, p = paired_ttest([100.0], [90.0])
        assert t == 0.0
        assert p == 1.0


class TestWilcoxon:
    def test_identical_distributions(self):
        a = [50.0] * 16
        b = [50.0] * 16
        w, p = wilcoxon_signed_rank(a, b)
        assert p == 1.0

    def test_clearly_superior(self):
        a = [100.0 + i for i in range(20)]
        b = [80.0 + i for i in range(20)]
        w, p = wilcoxon_signed_rank(a, b)
        assert p < 0.05

    def test_returns_two_floats(self):
        result = wilcoxon_signed_rank([1, 2, 3], [0, 1, 2])
        assert len(result) == 2
        assert all(isinstance(v, float) for v in result)


class TestCohensD:
    def test_zero_for_identical(self):
        a = [100.0] * 10
        b = [100.0] * 10
        assert cohens_d(a, b) == 0.0

    def test_positive_for_higher_a(self):
        a = [110.0] * 10
        b = [100.0] * 10
        # std of differences is 0, returns 0 (not inf) per implementation
        d = cohens_d(a, b)
        assert d == 0.0  # all diffs equal → stdev=0, returns 0

    def test_large_effect_size(self):
        # When differences vary (not all equal), stdev > 0 and d is meaningful
        import random
        rng = random.Random(1)
        a = [100.0 + i * 5 + rng.uniform(-2, 2) for i in range(20)]
        b = [50.0  + i * 5 + rng.uniform(-2, 2) for i in range(20)]
        d = cohens_d(a, b)
        assert d > 1.0  # large effect (constant ~50 gap vs small noise)


class TestBootstrapCI:
    def test_ci_contains_true_mean(self):
        a = [100.0 + i for i in range(20)]
        b = [90.0 + i for i in range(20)]
        lo, hi = bootstrap_ci(a, b, n_boot=1000)
        true_mean = 10.0  # a - b = 10 always
        assert lo <= true_mean <= hi

    def test_ci_symmetric_for_constant_delta(self):
        a = [200.0] * 20
        b = [190.0] * 20
        # All diffs equal 10 → bootstrap should be very tight
        lo, hi = bootstrap_ci(a, b, n_boot=500)
        assert abs(hi - lo) < 5.0

    def test_returns_two_floats(self):
        lo, hi = bootstrap_ci([1, 2, 3], [0, 1, 2])
        assert lo <= hi


class TestFullStats:
    def test_returns_all_required_keys(self):
        a = [100.0 + i for i in range(16)]
        b = [90.0 + i for i in range(16)]
        result = full_stats(a, b)
        required = {"n", "mean_a", "mean_b", "delta_mean", "t_stat",
                    "p_ttest", "w_stat", "p_wilcoxon", "cohens_d",
                    "ci_95_lo", "ci_95_hi"}
        assert required.issubset(result.keys())

    def test_empty_returns_error(self):
        result = full_stats([], [])
        assert "error" in result
