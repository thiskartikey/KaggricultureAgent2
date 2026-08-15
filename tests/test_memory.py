"""Tests for src/autoresearch/memory.py"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.autoresearch.memory import (
    make_record,
    append,
    load,
    query_failures,
    query_successes,
    is_duplicate,
    ingest_markdown_log,
    REQUIRED_KEYS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ledger(tmp_path) -> Path:
    return tmp_path / "experiments.jsonl"


def _sample_record(**overrides) -> dict:
    base = dict(
        exp_id="EXP-20260101-01",
        hypothesis="Increasing TARGET_COW from 8 to 9 will increase milk revenue.",
        target_code="policy.TARGET_COW",
        diff_summary="TARGET_COW = 9",
        tags=["cow", "target_cow"],
        decision="KEEP",
        stage_reached=3,
        delta_mean=800.0,
        p_ttest=0.03,
        p_wilcoxon=0.04,
        cohens_d=0.35,
        n_games=32,
        notes="test",
    )
    base.update(overrides)
    return make_record(**base)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

class TestSchemaValidation:
    def test_valid_record_no_error(self):
        r = _sample_record()
        assert set(REQUIRED_KEYS).issubset(r.keys())

    def test_invalid_decision_raises(self):
        with pytest.raises(ValueError, match="decision must be one of"):
            _sample_record(decision="MAYBE")

    def test_missing_key_raises(self):
        record = _sample_record()
        del record["hypothesis"]
        from src.autoresearch.memory import _validate
        with pytest.raises(ValueError, match="missing keys"):
            _validate(record)

    def test_tags_must_be_list(self):
        with pytest.raises((ValueError, TypeError)):
            make_record(
                exp_id="X", hypothesis="h", target_code="t",
                diff_summary="d", tags="not-a-list",
                decision="KEEP", stage_reached=1,
            )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_append_and_load(self, ledger):
        r = _sample_record()
        append(r, ledger)
        records = load(ledger)
        assert len(records) == 1
        assert records[0]["id"] == "EXP-20260101-01"

    def test_multiple_records(self, ledger):
        for i in range(3):
            r = _sample_record(exp_id=f"EXP-20260101-{i:02d}")
            append(r, ledger)
        assert len(load(ledger)) == 3

    def test_empty_ledger_returns_empty_list(self, ledger):
        assert load(ledger) == []

    def test_bad_json_lines_skipped(self, ledger):
        ledger.write_text('{"id": "ok", "decision": "REJECT"}\n{BROKEN}\n')
        records = load(ledger)
        # The bad line is silently skipped
        assert len(records) == 1

    def test_creates_parent_dirs(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "experiments.jsonl"
        r = _sample_record()
        append(r, deep)
        assert deep.exists()


# ---------------------------------------------------------------------------
# Query interface
# ---------------------------------------------------------------------------

class TestQueryInterface:
    def test_query_failures_by_tag(self, ledger):
        append(_sample_record(exp_id="EXP-01", decision="REJECT",
                               tags=["land_unlock"], hypothesis="land hypothesis"), ledger)
        append(_sample_record(exp_id="EXP-02", decision="REJECT",
                               tags=["wheat"], hypothesis="wheat hypothesis"), ledger)
        append(_sample_record(exp_id="EXP-03", decision="KEEP",
                               tags=["land_unlock"], hypothesis="land keep"), ledger)

        failures = query_failures(tag="land_unlock", ledger=ledger)
        assert len(failures) == 1
        assert failures[0]["id"] == "EXP-01"

    def test_query_successes_sorted(self, ledger):
        append(_sample_record(exp_id="EXP-01", decision="KEEP", delta_mean=100.0), ledger)
        append(_sample_record(exp_id="EXP-02", decision="KEEP", delta_mean=500.0), ledger)
        append(_sample_record(exp_id="EXP-03", decision="REJECT", delta_mean=900.0), ledger)

        successes = query_successes(ledger)
        assert successes[0]["delta_mean"] >= successes[1]["delta_mean"]
        assert all(s["decision"] == "KEEP" for s in successes)

    def test_is_duplicate_detects_similar(self, ledger):
        append(_sample_record(
            exp_id="EXP-01",
            decision="REJECT",
            tags=["land_unlock"],
            hypothesis="Unlocking land on day 6 increases score with higher revenue",
        ), ledger)
        # Very similar hypothesis (many shared words) with same tag
        assert is_duplicate(
            "Unlocking land on day 6 increases score with higher revenue today",
            ["land_unlock"],
            ledger=ledger,
            similarity_threshold=0.7,
        )

    def test_is_duplicate_novel_is_false(self, ledger):
        append(_sample_record(
            exp_id="EXP-01",
            decision="REJECT",
            tags=["land_unlock"],
            hypothesis="Changing land unlock day",
        ), ledger)
        # Completely different hypothesis
        assert not is_duplicate(
            "Increasing wheat buffer days from 3 to 5 reduces animal escapes",
            ["wheat"],
            ledger=ledger,
        )


# ---------------------------------------------------------------------------
# Markdown ingestion
# ---------------------------------------------------------------------------

class TestMarkdownIngestion:
    def test_ingest_experiment_md(self, ledger, tmp_path):
        md_content = """
## EXP-20260813-01: Land Unlock Day Correction (GAP-001)
- **Hypothesis**: Correcting land unlock to NE day 6 / SW day 10 will increase mean score.
- **Baseline**: `versions/Phase2_v1_policy.py`
- **Results**:
  - Policy Mean: 69,251 | Baseline Mean: 69,693 | ΔMean: -441
  - Paired t-stat: -0.55, p=0.582 — NOISE
- **Verdict**: REJECTED
- **Test Protocol**: 16 seeds × 2 seats = 32 games
"""
        md_path = tmp_path / "experiments.md"
        md_path.write_text(md_content)

        added = ingest_markdown_log(md_path, ledger)
        assert added == 1
        records = load(ledger)
        assert records[0]["decision"] == "REJECT"
        assert records[0]["id"] == "EXP-20260813-01"
        assert records[0]["delta_mean"] == -441.0

    def test_ingest_skips_pending(self, ledger, tmp_path):
        md_content = """
## EXP-TBD-04: Combined Land Unlock
- **Hypothesis**: LAND_UNLOCK_DAY = (6, 10) with 32 games.
- **Status**: QUEUED
"""
        md_path = tmp_path / "experiments.md"
        md_path.write_text(md_content)
        added = ingest_markdown_log(md_path, ledger)
        assert added == 0

    def test_ingest_no_duplicates(self, ledger, tmp_path):
        md_content = """
## EXP-20260813-01: Some experiment
- **Hypothesis**: Test hypothesis.
- **Verdict**: REJECTED
- **Test Protocol**: 8 seeds × 2 seats = 16 games
"""
        md_path = tmp_path / "experiments.md"
        md_path.write_text(md_content)
        # Ingest twice
        ingest_markdown_log(md_path, ledger)
        added2 = ingest_markdown_log(md_path, ledger)
        assert added2 == 0  # second call adds nothing
        assert len(load(ledger)) == 1
