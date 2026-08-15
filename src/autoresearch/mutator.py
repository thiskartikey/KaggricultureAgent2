"""Constrained policy mutator for KaggriRatchet.

Implements three mutation tiers with strict safety constraints:

  Tier 1 — Parameter config space:
    Modifies values in the top-level PARAMETERS dict (or equivalent module-level
    constants) without touching any algorithmic code.

  Tier 2 — Modular rule blocks:
    Replaces a single bounded code block (R1–R7, _plant_choice, _assign_tasks,
    _make_market_orders) with a diff provided by the Hypothesis Generator.

  Tier 3 — Task priority tiers:
    Modifies the TASK_TIER dict values only.

  AST Linter:
    Validates that the mutated source:
      - Parses cleanly
      - Defines a top-level agent() function
      - Imports no forbidden ML packages
      - Does not delete critical variables / identifiers
"""
from __future__ import annotations

import ast
import difflib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FORBIDDEN_IMPORTS = {
    "torch", "tensorflow", "keras", "sklearn", "scipy",
    "lightgbm", "xgboost", "catboost", "gym", "transformers",
}

CRITICAL_IDENTIFIERS = {
    "claims", "SHED_CAP", "_CLAIM_STATE",
    "agent", "_assign_tasks", "_make_market_orders",
}

# Top-level numeric constants that Tier 1 is allowed to touch
TIER1_PARAMS = {
    "TARGET_COW", "TARGET_SHEEP", "TARGET_STRAWBERRY", "TARGET_MELON",
    "CASH_FLOOR", "LAND_UNLOCK_DAY", "TARGET_PASTURE_BY_DAY",
    "TARGET_GOOSE",
}

# ---------------------------------------------------------------------------
# AST linter
# ---------------------------------------------------------------------------

class ASTLintError(ValueError):
    """Raised when mutated source fails the invariant lint check."""


def lint(source: str, path: str = "<mutated>") -> None:
    """Parse and validate the mutated source.  Raises ASTLintError on failure."""
    # 1. Syntax
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as e:
        raise ASTLintError(f"Syntax error: {e}") from e

    # 2. agent() function must exist at module level
    top_level_names = {
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and isinstance(node.col_offset, int) and node.col_offset == 0
    }
    if "agent" not in top_level_names:
        raise ASTLintError("agent() function not found at module level")

    # 3. No forbidden ML imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                pkg = alias.name.split(".")[0]
                if pkg in FORBIDDEN_IMPORTS:
                    raise ASTLintError(f"Forbidden import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                pkg = node.module.split(".")[0]
                if pkg in FORBIDDEN_IMPORTS:
                    raise ASTLintError(f"Forbidden import from: {node.module}")

    # 4. Critical identifiers must still be present (as Name references or definitions)
    all_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            all_names.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            all_names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            all_names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if hasattr(node, "targets") else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    all_names.add(t.id)

    for ident in CRITICAL_IDENTIFIERS:
        if ident not in all_names:
            raise ASTLintError(f"Critical identifier deleted or renamed: {ident!r}")


# ---------------------------------------------------------------------------
# Tier 1 mutator — parameter value replacement
# ---------------------------------------------------------------------------

def mutate_tier1(
    source: str,
    param_name: str,
    new_value: Any,
) -> Tuple[str, str]:
    """Replace the value of a top-level constant.

    Handles int, float, tuple, and list literals.
    Returns (new_source, unified_diff).
    Raises ValueError if param_name is not in TIER1_PARAMS or not found.
    """
    if param_name not in TIER1_PARAMS:
        raise ValueError(
            f"{param_name!r} not in TIER1_PARAMS. "
            f"Allowed: {sorted(TIER1_PARAMS)}"
        )

    # Build the new value string
    new_val_str = repr(new_value)

    # Match: PARAM_NAME = <value ending at newline or comment>
    pattern = re.compile(
        rf"^({re.escape(param_name)}\s*=\s*)(.+?)(\s*(?:#[^\n]*)?)$",
        re.MULTILINE,
    )
    match = pattern.search(source)
    if not match:
        raise ValueError(f"Could not locate {param_name!r} assignment in source")

    new_source = pattern.sub(rf"\g<1>{new_val_str}\g<3>", source, count=1)

    diff = "".join(difflib.unified_diff(
        source.splitlines(keepends=True),
        new_source.splitlines(keepends=True),
        fromfile="policy.py (before)",
        tofile="policy.py (after)",
    ))
    return new_source, diff


# ---------------------------------------------------------------------------
# Tier 2 mutator — function/block replacement
# ---------------------------------------------------------------------------

def mutate_tier2(
    source: str,
    block_name: str,
    new_block_source: str,
) -> Tuple[str, str]:
    """Replace the body of a named function or rule comment block.

    `block_name` may be a function name (e.g. '_make_market_orders') or a
    rule-block marker (e.g. 'R5').  Only the first match is replaced.

    Returns (new_source, unified_diff).
    """
    lines = source.splitlines(keepends=True)

    # Try to locate a function definition
    start_line = None
    end_line = None
    indent = ""

    for i, line in enumerate(lines):
        # Match `def block_name(`:
        if re.match(rf"^def {re.escape(block_name)}\s*\(", line):
            start_line = i
            indent = ""
            break
        # Match rule comment blocks like `# ── R5: ...`
        # Require the ── decorator so plain inline comments (e.g. "# R1: ..." in
        # _seed_targets) are not confused with the actual rule-block markers.
        if block_name.startswith("R") and re.match(
            rf"^\s*#\s*──.*{re.escape(block_name)}\b", line
        ):
            start_line = i
            # Indent is the block's indentation level (inside a function)
            indent_m = re.match(r"(\s*)", line)
            indent = indent_m.group(1) if indent_m else ""
            break

    if start_line is None:
        raise ValueError(f"Block {block_name!r} not found in source")

    # Determine end: next def at same indentation, or end of file
    if indent == "":
        # Top-level function: end at the next def/class at col 0
        end_line = len(lines)
        for j in range(start_line + 1, len(lines)):
            if re.match(r"^(def |class )", lines[j]):
                end_line = j
                break
    else:
        # Inline block inside a function: find next comment block or end of parent
        end_line = len(lines)
        for j in range(start_line + 1, len(lines)):
            if re.match(r"\s*#\s*──", lines[j]) and len(re.match(r"(\s*)", lines[j]).group(1)) <= len(indent):
                end_line = j
                break
            # End at dedented code
            stripped = lines[j].rstrip()
            if stripped and not stripped.startswith("#"):
                m = re.match(r"(\s*)", lines[j])
                cur_indent = m.group(1) if m else ""
                if len(cur_indent) < len(indent):
                    end_line = j
                    break

    # Build new source
    replacement_lines = new_block_source.splitlines(keepends=True)
    if not replacement_lines[-1].endswith("\n"):
        replacement_lines[-1] += "\n"

    new_lines = lines[:start_line] + replacement_lines + lines[end_line:]
    new_source = "".join(new_lines)

    diff = "".join(difflib.unified_diff(
        lines, new_lines,
        fromfile="policy.py (before)",
        tofile="policy.py (after)",
    ))
    return new_source, diff


# ---------------------------------------------------------------------------
# Tier 3 mutator — task priority tier values
# ---------------------------------------------------------------------------

def mutate_tier3(
    source: str,
    task_name: str,
    new_tier: int,
) -> Tuple[str, str]:
    """Change one entry in the TASK_TIER dict.

    Returns (new_source, unified_diff).
    """
    if not (0 <= new_tier <= 4):
        raise ValueError(f"new_tier must be 0–4, got {new_tier}")

    pattern = re.compile(
        rf"(\"{re.escape(task_name)}\"\s*:\s*)\d+",
        re.MULTILINE,
    )
    if not pattern.search(source):
        raise ValueError(f"Task {task_name!r} not found in TASK_TIER dict")

    new_source = pattern.sub(rf"\g<1>{new_tier}", source, count=1)
    diff = "".join(difflib.unified_diff(
        source.splitlines(keepends=True),
        new_source.splitlines(keepends=True),
        fromfile="policy.py (before)",
        tofile="policy.py (after)",
    ))
    return new_source, diff


# ---------------------------------------------------------------------------
# Composite mutator — apply several sub-mutations atomically
# ---------------------------------------------------------------------------

def mutate_composite(
    source: str,
    steps: List[Dict[str, Any]],
) -> Tuple[str, str]:
    """Apply a sequence of sub-mutations on the same source in order.

    Each step is a dict with a ``tier`` key plus the tier-specific kwargs:
      {"tier": 1, "param_name": "LAND_UNLOCK_DAY", "new_value": (6, 10)}
      {"tier": 2, "block_name": "R1", "new_block_source": "..."}
      {"tier": 3, "task_name": "plant", "new_tier": 1}

    Returns (final_source, combined_unified_diff).
    """
    original = source
    current = source
    for step in steps:
        tier = step["tier"]
        if tier == 1:
            current, _ = mutate_tier1(current, step["param_name"], step["new_value"])
        elif tier == 2:
            current, _ = mutate_tier2(current, step["block_name"], step["new_block_source"])
        elif tier == 3:
            current, _ = mutate_tier3(current, step["task_name"], step["new_tier"])
        else:
            raise ValueError(f"Unknown sub-mutation tier: {tier}")

    diff = "".join(difflib.unified_diff(
        original.splitlines(keepends=True),
        current.splitlines(keepends=True),
        fromfile="policy.py (before)",
        tofile="policy.py (after)",
    ))
    return current, diff


# ---------------------------------------------------------------------------
# High-level mutation entry point
# ---------------------------------------------------------------------------

def apply_mutation(
    policy_path: Path,
    tier: int,
    **kwargs: Any,
) -> Tuple[str, str]:
    """Apply a Tier 1/2/3 (or composite) mutation and run the AST linter.

    Returns (new_source, diff) or raises ASTLintError on failure.

    Tier 1 kwargs: param_name, new_value
    Tier 2 kwargs: block_name, new_block_source
    Tier 3 kwargs: task_name, new_tier
    Tier 0 (composite) kwargs: steps — list of sub-mutation dicts
    """
    source = Path(policy_path).read_text(encoding="utf-8")

    if tier == 0:
        # Strip metadata keys that are not sub-mutation steps
        new_source, diff = mutate_composite(source, kwargs["steps"])
    elif tier == 1:
        new_source, diff = mutate_tier1(source, kwargs["param_name"], kwargs["new_value"])
    elif tier == 2:
        new_source, diff = mutate_tier2(source, kwargs["block_name"], kwargs["new_block_source"])
    elif tier == 3:
        new_source, diff = mutate_tier3(source, kwargs["task_name"], kwargs["new_tier"])
    else:
        raise ValueError(f"Unknown mutation tier: {tier}")

    lint(new_source, path=str(policy_path))
    return new_source, diff
