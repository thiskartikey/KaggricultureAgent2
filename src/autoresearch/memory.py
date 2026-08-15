"""Experiment memory — schema-validated JSONL ledger for KaggriRatchet.

Every experiment is logged as one JSON line in `experiments/experiments.jsonl`.
The memory module supports:
  - Appending new experiment records (schema-validated)
  - Loading and filtering the ledger
  - Semantic / tag-based failure queries (e.g. query_failures(tag="land_unlock"))
  - Historical ingestion from the markdown experiments.md log

Schema keys (all required unless marked optional):
    id              str   — unique experiment ID (EXP-YYYYMMDD-NN)
    timestamp       str   — ISO 8601 UTC
    hypothesis      str   — one-sentence hypothesis
    target_code     str   — module/function mutated (e.g. "policy._make_market_orders")
    diff_summary    str   — short description of the change
    tags            list  — semantic category tags (e.g. ["land_unlock", "cash_floor"])
    parent_commit   str   — git SHA of the baseline (optional, "" if unknown)
    stage_reached   int   — highest evaluation stage reached (0-3)
    decision        str   — "KEEP" | "REJECT" | "PENDING"
    delta_mean      float — mean(candidate) - mean(baseline) (0.0 if not reached Stage 2)
    p_ttest         float — paired t-test p-value (1.0 if not reached Stage 3)
    p_wilcoxon      float — Wilcoxon p-value (1.0 if not reached Stage 3)
    cohens_d        float — Cohen's d (0.0 if not reached Stage 3)
    n_games         int   — total games played
    notes           str   — free-form human notes (optional, "" default)
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DEFAULT_LEDGER = Path(__file__).parent.parent.parent / "experiments" / "experiments.jsonl"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

REQUIRED_KEYS = {
    "id", "timestamp", "hypothesis", "target_code", "diff_summary",
    "tags", "parent_commit", "stage_reached", "decision",
    "delta_mean", "p_ttest", "p_wilcoxon", "cohens_d", "n_games", "notes",
}

VALID_DECISIONS = {"KEEP", "REJECT", "PENDING"}


def _validate(record: Dict[str, Any]) -> None:
    """Raise ValueError if the record violates the schema."""
    missing = REQUIRED_KEYS - set(record.keys())
    if missing:
        raise ValueError(f"Experiment record missing keys: {missing}")
    if record["decision"] not in VALID_DECISIONS:
        raise ValueError(
            f"decision must be one of {VALID_DECISIONS}, got {record['decision']!r}"
        )
    if not isinstance(record["tags"], list):
        raise ValueError("tags must be a list")
    if not isinstance(record["stage_reached"], int) or not (0 <= record["stage_reached"] <= 3):
        raise ValueError("stage_reached must be int 0-3")


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def make_record(
    exp_id: str,
    hypothesis: str,
    target_code: str,
    diff_summary: str,
    tags: List[str],  # must be a list
    decision: str,
    stage_reached: int,
    delta_mean: float = 0.0,
    p_ttest: float = 1.0,
    p_wilcoxon: float = 1.0,
    cohens_d: float = 0.0,
    n_games: int = 0,
    parent_commit: str = "",
    notes: str = "",
) -> Dict[str, Any]:
    """Build and validate a new experiment record."""
    if not isinstance(tags, list):
        raise ValueError(f"tags must be a list, got {type(tags).__name__!r}")
    record = {
        "id": exp_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hypothesis": hypothesis,
        "target_code": target_code,
        "diff_summary": diff_summary,
        "tags": list(tags),
        "parent_commit": parent_commit,
        "stage_reached": stage_reached,
        "decision": decision,
        "delta_mean": float(delta_mean),
        "p_ttest": float(p_ttest),
        "p_wilcoxon": float(p_wilcoxon),
        "cohens_d": float(cohens_d),
        "n_games": int(n_games),
        "notes": notes,
    }
    _validate(record)
    return record


def append(record: Dict[str, Any], ledger: Path = DEFAULT_LEDGER) -> None:
    """Validate and append one record to the JSONL ledger."""
    _validate(record)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def load(ledger: Path = DEFAULT_LEDGER) -> List[Dict[str, Any]]:
    """Load all records from the JSONL ledger; silently skip bad lines."""
    if not ledger.exists():
        return []
    records = []
    with ledger.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def query_failures(
    tag: Optional[str] = None,
    target_code: Optional[str] = None,
    ledger: Path = DEFAULT_LEDGER,
) -> List[Dict[str, Any]]:
    """Return all REJECT records, optionally filtered by tag or target_code."""
    records = load(ledger)
    out = [r for r in records if r.get("decision") == "REJECT"]
    if tag:
        out = [r for r in out if tag in r.get("tags", [])]
    if target_code:
        out = [r for r in out if r.get("target_code", "").startswith(target_code)]
    return out


def query_successes(ledger: Path = DEFAULT_LEDGER) -> List[Dict[str, Any]]:
    """Return all KEEP records, sorted by delta_mean descending."""
    records = load(ledger)
    kept = [r for r in records if r.get("decision") == "KEEP"]
    return sorted(kept, key=lambda r: r.get("delta_mean", 0), reverse=True)


def is_duplicate(
    hypothesis: str,
    tags: List[str],
    ledger: Path = DEFAULT_LEDGER,
    similarity_threshold: float = 0.8,
) -> bool:
    """Return True if an experiment with the same tags and a very similar
    hypothesis has already been attempted and REJECTED.

    Uses simple word-overlap (Jaccard) rather than embeddings.
    """
    records = load(ledger)
    h_words = set(hypothesis.lower().split())
    for r in records:
        if r.get("decision") != "REJECT":
            continue
        # Tag overlap check
        r_tags = set(r.get("tags", []))
        if r_tags and set(tags) and r_tags & set(tags):
            prev_words = set(r.get("hypothesis", "").lower().split())
            if not prev_words:
                continue
            jaccard = len(h_words & prev_words) / len(h_words | prev_words)
            if jaccard >= similarity_threshold:
                return True
    return False


# ---------------------------------------------------------------------------
# Historical ingestion from experiments.md
# ---------------------------------------------------------------------------

def ingest_markdown_log(
    md_path: Path,
    ledger: Path = DEFAULT_LEDGER,
) -> int:
    """Parse the existing experiments.md and write records to the JSONL ledger.

    Only ingests experiments that have a final VERDICT (ACCEPTED / REJECTED).
    Returns the number of records added.
    """
    text = md_path.read_text(encoding="utf-8")

    # Map from verdict keywords to decision values
    verdict_map = {
        "ACCEPTED": "KEEP",
        "ACCEPTED (": "KEEP",
        "REJECTED": "REJECT",
    }

    # Find EXP-* blocks
    exp_re = re.compile(r"^## (EXP-\d{8}-\d+): (.+?)$", re.MULTILINE)
    blocks = list(exp_re.finditer(text))

    added = 0
    existing_ids = {r.get("id") for r in load(ledger)}

    for i, match in enumerate(blocks):
        exp_id = match.group(1)
        title = match.group(2).strip()
        if exp_id in existing_ids:
            continue

        # Extract block text up to the next EXP block
        start = match.start()
        end = blocks[i + 1].start() if i + 1 < len(blocks) else len(text)
        block = text[start:end]

        # Extract hypothesis
        hyp_m = re.search(r"\*\*Hypothesis\*\*:\s*(.+?)(?=\n- |\Z)", block, re.DOTALL)
        hypothesis = hyp_m.group(1).strip().replace("\n", " ") if hyp_m else title

        # Extract verdict
        verdict_m = re.search(r"\*\*Verdict\*\*:\s*(ACCEPTED|REJECTED)", block)
        if not verdict_m:
            continue   # skip QUEUED / incomplete experiments
        decision = verdict_map.get(verdict_m.group(1), "REJECT")

        # Extract delta_mean
        delta_m = re.search(r"ΔMean:\s*([+-]?\d[\d,]*)", block)
        delta = float(delta_m.group(1).replace(",", "")) if delta_m else 0.0

        # Extract p-value
        p_m = re.search(r"p\s*=\s*(0\.\d+)", block)
        p_val = float(p_m.group(1)) if p_m else 1.0

        # Extract n_games
        games_m = re.search(r"(\d+)\s*seeds\s*×\s*2\s*seats\s*=\s*(\d+)\s*games", block)
        n_games = int(games_m.group(2)) if games_m else 0

        # Build tags from title keywords
        tags = []
        for kw in ("land_unlock", "land", "wheat", "hands", "opening",
                   "pasture", "market", "endgame", "melon", "strawberry"):
            if kw.replace("_", " ") in title.lower() or kw in title.lower():
                tags.append(kw)

        record = make_record(
            exp_id=exp_id,
            hypothesis=hypothesis[:500],
            target_code="policy",
            diff_summary=title,
            tags=tags,
            decision=decision,
            stage_reached=3 if n_games >= 32 else 2 if n_games >= 16 else 1,
            delta_mean=delta,
            p_ttest=p_val,
            p_wilcoxon=p_val,
            cohens_d=0.0,
            n_games=n_games,
            notes=f"Ingested from experiments.md: {title}",
        )
        append(record, ledger)
        existing_ids.add(exp_id)
        added += 1

    return added
