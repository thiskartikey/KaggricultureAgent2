# Implementation Plan: Subsystem C (Replay Pipeline Unification)

> **Owner**: Subsystem C Lead
> **Target Files**: `parse_replays.py`, `src/replay_analysis/*`, `tests/test_replay_parser.py`

---

## 1. Objectives
1. Maintain strict parity between `parse_replays.py` (trajectory extractor for RL/DT) and `src/replay_analysis/parser.py` (canonical turn extractor for telemetry and rule mining).
2. Unify shop string normalization and product taxonomy across all modules.
3. Validate that 100% of replay parser unit tests and self-tests pass.

---

## 2. Technical Specification

1. **Feature Layout & Dimensions**:
   - `OBS_DIM = 145` in `parse_replays.py`
   - Canonical turn feature count $= 60$ in `src/replay_analysis/feature_extractor.py`
2. **Shop Normalization**:
   - Use `_norm_shop(s) = str(s).strip().upper().replace(" ", "_").replace("-", "_")`
3. **Data Integrity Checks**:
   - `returns_to_go[0] == final_money - starting_money`
   - All extracted action summaries match actual player action records.
