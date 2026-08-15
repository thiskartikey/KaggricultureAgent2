"""KaggriRatchet Controller — autonomous Git-backed optimization loop.

State machine:
  BACKLOG → PROPOSED → TESTING → PROMOTED | REVERTED

Usage:
    python -m src.autoresearch.controller --step          # single iteration
    python -m src.autoresearch.controller --loop --max-exp 10
    python -m src.autoresearch.controller --test-ratchet  # ratchet integrity test
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Resolve project root (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent
POLICY_PATH = PROJECT_ROOT / "policy.py"
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"
LEDGER_PATH = EXPERIMENTS_DIR / "experiments.jsonl"
VERSIONS_DIR = PROJECT_ROOT / "versions"


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _git(args: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Run a git command, raise on non-zero exit."""
    result = subprocess.run(
        ["git"] + args,
        cwd=str(cwd or PROJECT_ROOT),
        capture_output=True, text=True,
    )
    return result


def current_sha() -> str:
    r = _git(["rev-parse", "HEAD"])
    return r.stdout.strip() if r.returncode == 0 else ""


def current_branch() -> str:
    r = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    return r.stdout.strip() if r.returncode == 0 else "HEAD"


def working_tree_clean() -> bool:
    r = _git(["status", "--porcelain"])
    return r.returncode == 0 and r.stdout.strip() == ""


def create_experiment_branch(exp_id: str) -> str:
    branch = f"experiment/{exp_id}"
    _git(["checkout", "-b", branch])
    return branch


def commit_candidate(exp_id: str, diff_summary: str) -> str:
    _git(["add", "-A"])
    msg = f"[KaggriRatchet] {exp_id}: {diff_summary}"
    _git(["commit", "-m", msg])
    return current_sha()


def merge_to_base(branch: str, exp_id: str, base_branch: str) -> None:
    _git(["checkout", base_branch])
    _git(["merge", "--no-ff", branch, "-m", f"[KaggriRatchet] PROMOTE {exp_id}"])
    _git(["tag", f"champion-{exp_id}"])
    _git(["branch", "-d", branch])


def hard_rollback(branch: str, base_branch: str) -> None:
    """Discard the experiment branch and return to base cleanly."""
    _git(["checkout", base_branch])
    _git(["reset", "--hard", "HEAD"])
    _git(["clean", "-fd"])
    r = _git(["branch", "--list", branch])
    if branch in r.stdout:
        _git(["branch", "-D", branch])


# ---------------------------------------------------------------------------
# Experiment ID allocation
# ---------------------------------------------------------------------------

def next_exp_id() -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    from src.autoresearch.memory import load
    existing = {r.get("id", "") for r in load(LEDGER_PATH)}
    n = 1
    while True:
        candidate = f"EXP-{today}-{n:02d}"
        if candidate not in existing:
            return candidate
        n += 1


# ---------------------------------------------------------------------------
# Single experiment iteration
# ---------------------------------------------------------------------------

def run_one_iteration(verbose: bool = True, tried_params: Optional[set] = None) -> dict:
    """Execute one full experiment cycle.

    Returns the result dict from the evaluator.
    tried_params is mutated in-place so the caller can thread it across iterations,
    preventing the same param from being proposed twice in one loop run.
    """
    from src.autoresearch.hypothesis import generate_hypothesis
    from src.autoresearch.mutator import apply_mutation
    from src.autoresearch.evaluator import evaluate
    from src.autoresearch.memory import make_record, append

    if tried_params is None:
        tried_params = set()

    exp_id = next_exp_id()
    sha = current_sha()
    branch = current_branch()

    if verbose:
        print(f"\n{'='*60}")
        print(f"KaggriRatchet — {exp_id}")
        print(f"Branch: {branch}  SHA: {sha[:8]}")
        print(f"{'='*60}")

    # 1. Generate hypothesis (no telemetry in this simplified loop; telemetry
    #    is fed in when replay traces are available)
    hypothesis = generate_hypothesis(report=None, ledger=LEDGER_PATH, tried_params=tried_params)
    if hypothesis is None:
        if verbose:
            print("No novel hypothesis available. Stopping.")
        return {"decision": "ABORT", "reason": "No novel hypothesis"}

    if verbose:
        print(f"\nHypothesis: {hypothesis['rationale']}")
        print(f"Tier: {hypothesis['tier']}  Tags: {hypothesis['tags']}")

    # 2. Apply mutation to a temp copy
    with tempfile.NamedTemporaryFile(
        suffix=".py", prefix=f"candidate_{exp_id}_",
        dir=str(PROJECT_ROOT), delete=False, mode="w"
    ) as tmp:
        candidate_path = tmp.name

    try:
        new_source, diff = apply_mutation(
            POLICY_PATH,
            tier=hypothesis["tier"],
            **hypothesis["mutation"],
        )
        Path(candidate_path).write_text(new_source, encoding="utf-8")

        if verbose:
            print(f"\nMutation applied ({len(diff.splitlines())} diff lines)")

        # 3. Run evaluation cascade
        if verbose:
            print("\nRunning evaluation cascade …")

        baseline_path = str(POLICY_PATH)
        result = evaluate(
            candidate=candidate_path,
            baseline=baseline_path,
            skip_stage0=False,
        )

        if verbose:
            print(f"\nDecision: {result['decision']}")
            print(f"Reason:   {result['reason']}")
            if result.get("stats"):
                s = result["stats"]
                print(
                    f"Stats: delta={s['delta_mean']:+.0f}  "
                    f"p_t={s['p_ttest']:.3f}  "
                    f"p_w={s['p_wilcoxon']:.3f}  "
                    f"d={s['cohens_d']:.2f}"
                )

        # 4. Log to experiment memory
        stats = result.get("stats") or {}
        record = make_record(
            exp_id=exp_id,
            hypothesis=hypothesis["rationale"],
            target_code=hypothesis["target_code"],
            diff_summary=json.dumps(hypothesis["mutation"])[:200],
            tags=hypothesis["tags"],
            decision=result["decision"],
            stage_reached=result.get("stage", 0),
            delta_mean=stats.get("delta_mean", 0.0),
            p_ttest=stats.get("p_ttest", 1.0),
            p_wilcoxon=stats.get("p_wilcoxon", 1.0),
            cohens_d=stats.get("cohens_d", 0.0),
            n_games=stats.get("n", 0),
            parent_commit=sha,
            notes=result["reason"],
        )
        append(record, LEDGER_PATH)

        # 5. Ratchet: KEEP → copy to policy.py + archive; REJECT → discard
        if result["decision"] == "KEEP":
            if verbose:
                print(f"\n✓ PROMOTED — writing new champion to policy.py")
            shutil.copy(candidate_path, str(POLICY_PATH))
            VERSIONS_DIR.mkdir(exist_ok=True)
            archive_path = VERSIONS_DIR / f"{exp_id}_policy.py"
            shutil.copy(str(POLICY_PATH), str(archive_path))
            if verbose:
                print(f"  Archived to {archive_path.name}")
            # On KEEP the policy changed — clear tried_params so next iteration
            # explores from the new baseline.
            tried_params.clear()
        else:
            if verbose:
                print(f"\n✗ REJECTED — policy.py unchanged")
            # Mark this mutation as tried so next iteration skips it.
            # Use a specific key that distinguishes different mutations on
            # the same block (e.g. two different target_hands variants).
            mut = hypothesis.get("mutation", {})
            tags = hypothesis.get("tags", [])
            if "param_name" in mut:
                tried_params.add(mut["param_name"])
            elif "task_name" in mut:
                tried_params.add(mut["task_name"] + "_tier")
            elif "block_name" in mut:
                # Use block_name + second tag (e.g. "target_hands_endgame")
                # for uniqueness across multiple Tier 2 variants on same block
                suffix = tags[1] if len(tags) > 1 else mut["block_name"]
                tried_params.add(f"t2_{mut['block_name']}_{suffix}")

    finally:
        Path(candidate_path).unlink(missing_ok=True)

    return result


# ---------------------------------------------------------------------------
# Ratchet integrity test
# ---------------------------------------------------------------------------

def test_ratchet_integrity() -> bool:
    """Verify that the ratchet does not corrupt git state.

    Runs a mutation that should fail Stage 0/1, checks that git state
    returns to a clean HEAD with no dirty files.
    """
    print("Running ratchet integrity test …")
    initial_sha = current_sha()
    initial_branch = current_branch()

    # Create a deliberately broken candidate (empty file fails Stage 0)
    broken = PROJECT_ROOT / "_test_broken_policy.py"
    broken.write_text("# deliberately empty — should fail all stages\n")

    try:
        from src.autoresearch.evaluator import evaluate
        result = evaluate(
            candidate=str(broken),
            baseline=str(POLICY_PATH),
            skip_stage0=False,
        )
        assert result["decision"] == "REJECT", (
            f"Expected REJECT for broken policy, got {result['decision']}"
        )
        print(f"  ✓ Broken policy correctly rejected at stage {result['stage']}")
    finally:
        broken.unlink(missing_ok=True)

    # Verify git state unchanged
    final_sha = current_sha()
    clean = working_tree_clean()
    final_branch = current_branch()

    ok = (final_sha == initial_sha and clean and final_branch == initial_branch)
    if ok:
        print("  ✓ Git state intact: SHA unchanged, working tree clean")
    else:
        print(
            f"  ✗ Git state corrupted: SHA {initial_sha[:8]}->{final_sha[:8]}, "
            f"clean={clean}, branch={initial_branch}->{final_branch}"
        )
    return ok


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="KaggriRatchet autonomous optimizer")
    ap.add_argument("--step", action="store_true",
                    help="Execute one experiment iteration and exit")
    ap.add_argument("--loop", action="store_true",
                    help="Run continuously until --max-exp is reached")
    ap.add_argument("--max-exp", type=int, default=5,
                    help="Maximum number of experiments to run (default: 5)")
    ap.add_argument("--test-ratchet", action="store_true",
                    help="Run ratchet integrity test and exit")
    ap.add_argument("--quiet", action="store_true", help="Suppress progress output")
    args = ap.parse_args()

    verbose = not args.quiet

    if args.test_ratchet:
        ok = test_ratchet_integrity()
        sys.exit(0 if ok else 1)

    if args.step:
        result = run_one_iteration(verbose=verbose)
        sys.exit(0 if result.get("decision") == "KEEP" else 1)

    if args.loop:
        n_run = 0
        n_promoted = 0
        tried: set = set()
        while n_run < args.max_exp:
            result = run_one_iteration(verbose=verbose, tried_params=tried)
            n_run += 1
            if result.get("decision") == "KEEP":
                n_promoted += 1
            elif result.get("decision") == "ABORT":
                print("No more novel hypotheses. Stopping loop.")
                break
        print(f"\nLoop complete: {n_run} experiments, {n_promoted} promotions.")
        return

    ap.print_help()


if __name__ == "__main__":
    main()
