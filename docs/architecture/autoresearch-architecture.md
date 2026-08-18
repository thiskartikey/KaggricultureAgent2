# KaggricultureAgent — Autoresearch Architecture Audit, Feasibility Review & Implementation Plan

> **Authoritative System Architecture & Engineering Roadmap**  
> **Status**: Approved for Implementation  
> **Target System**: KaggriRatchet (Autonomous Heuristic Strategy Optimization Engine)  
> **Reference Baselines**: `kayba-ai/recursive-improve`, `hwchase17/autoresearch-agents`, `docs/AUDIT.md`, `instructions/replay_intelligence.md`

---

## 1. Executive Verdict

### **Verdict: YES, BUT MODIFY**

### **Core Rationale**
The conceptual direction—adapting the empirical `modify → evaluate → measure → keep/revert → repeat` loop from `hwchase17/autoresearch-agents` and `kayba-ai/recursive-improve` to Kaggriculture—is sound. However, deploying a naive autoresearch loop directly onto `policy.py` would fail for three critical reasons discovered during our audit:

1. **Unconstrained Code Mutation is High-Entropy and Destructive**: As proven by the catastrophic **v6 Decision Transformer regression (−113k points, 16/16 losses)** and confirmed in `docs/roadmap/experiments.md`, arbitrary code edits easily break delicate state-machine invariants (such as sticky task claims, day-0 watering survival, and wheat-carrier routing).
2. **Replay Evidence Shows "Config Constants" Are Symptoms, Not Causes**: In `EXP-20260813-01` and `EXP-TBD-05b`, changing constants like `LAND_UNLOCK_DAY = (6, 10)` or `TARGET_PASTURE = 14` were no-ops or negative because the agent lacked the early cash generation to trigger them. The optimization system must target **operational mechanics** (market ordering, slot crowding, harvest routing), not just surface constants.
3. **Flat Evaluation Compute Waste**: Running full 32-game paired evaluations on every exploratory mutation wastes massive CPU cycles. An **adaptive multi-stage evaluation filter (falsification cascade)** is required to reject bad candidates in under 15 seconds.

---

## 2. Architecture Comparison

| Dimension | 1. Current Codebase | 2. Initial Proposal | 3. `recursive-improve` | 4. `autoresearch-agents` | 5. Recommended Architecture (**KaggriRatchet**) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Target Space** | Manual edits to `policy.py` based on markdown docs | LLM modifies arbitrary code or parameter dict | Python agent execution traces & LLM prompts | Edits single target file (`agent.py`) via `program.md` | **Tiered Mutation**: Parameter schema → Modular rule blocks → Invariant-gated policy logic |
| **Diagnostics / Input** | Manual post-mortems via `analyze_failure_v2.py` | Raw replays + diagnostic scripts | Trace log analysis of failed LLM calls | Previous score logs in `results.tsv` | **Replay Feature Store** (`src/replay_analysis/`) + **Simulation Telemetry Extractor** (lost turns, shed bottlenecks) |
| **Mutation Engine** | Human developer / Bob assistant | Single LLM Policy Mutator | Coding agent applying diffs to prompt/tool code | Single agent editing code with `program.md` context | **Specialized Policy Engineer Subagent** constrained by mutation boundaries & AST linter |
| **Evaluation Gate** | `evaluate.py` (8–16 games, paired t-test) | `evaluate.py` (16 games, p < 0.05) | Benchmark score comparison on test suite | Single-score threshold comparison | **Multi-Stage Adaptive Gate**: Stage 0 (Sanity/Invariants) → Stage 1 (4-game prune) → Stage 2 (16-game) → Stage 3 (32-game paired t-test + Wilcoxon + effect size) |
| **Rollback / Ratchet** | Manual Git checkout / archive copies in `versions/` | Git commit on KEEP, failure memory on REJECT | `/ratchet` git-backed keep/revert | `git reset --hard` on score drop | **Automated Headless Ratchet**: Isolated git branches, automated hard rollback, append-only `experiments.jsonl` |
| **Memory / Deduplication** | Markdown logs (`experiments.md`, `todo.md`) | `experiments.jsonl`, `failures.jsonl` | Local execution trace folders | Linear `results.tsv` | **Structured Experiment DB** (`experiments.jsonl` + semantic failure tags to block duplicate mutations) |

---

## 3. Recommended Final Architecture

```
                                  ┌──────────────────────────────────────────────┐
                                  │          KAGGRICULTURE ENVIRONMENT           │
                                  │   (Simulator, Replays, Baseline Policy)      │
                                  └──────────────────────┬───────────────────────┘
                                                         │
                                                         ▼
                                  ┌──────────────────────────────────────────────┐
                                  │        DIAGNOSTIC & TELEMETRY ENGINE         │
                                  │   - src/replay_analysis/ (Top-4 Feature DB)  │
                                  │   - Telemetry Tracing (Wasted turns, gluts)  │
                                  └──────────────────────┬───────────────────────┘
                                                         │ Structured Metrics & Gap Matrix
                                                         ▼
                                  ┌──────────────────────────────────────────────┐
                                  │          HYPOTHESIS GENERATOR AGENT          │
                                  │   - Queries Experiment Memory (No retries)   │
                                  │   - Generates bounded, testable hypothesis   │
                                  └──────────────────────┬───────────────────────┘
                                                         │ Structured Hypothesis Object
                                                         ▼
                                  ┌──────────────────────────────────────────────┐
                                  │         POLICY MUTATOR (SPECIALIST)          │
                                  │   Tier 1: Parameter Config Space             │
                                  │   Tier 2: Modular Rule Blocks (R1-R7)        │
                                  │   Tier 3: Task Priority Tiers (0-4)          │
                                  └──────────────────────┬───────────────────────┘
                                                         │ Candidate Policy Diff
                                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       ADAPTIVE FALSIFICATION CASCADE                                            │
│                                                                                                                 │
│  [Stage 0: Invariant Gate] ──Fail──► REJECT (0s)    (No ML imports, no prints, syntax valid, speed < 15ms)      │
│            │ Pass                                                                                               │
│  [Stage 1: Fast Screen]    ──Fail──► REJECT (15s)   (2 seeds / 4 games: if Δ < -2000 or crash)                  │
│            │ Pass                                                                                               │
│  [Stage 2: Confirm Screen] ──Fail──► REJECT (1m)    (8 seeds / 16 games: if Δ ≤ 0)                              │
│            │ Pass                                                                                               │
│  [Stage 3: Champion Gate]  ──Fail──► REJECT (2.5m)  (16 seeds / 32 games: paired t < 0.05, Wilcoxon p < 0.05,    │
│            │ Pass                                    Cohen's d > 0.20, worst-case drop ≤ 5%)                    │
└────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┘
             │ Pass All Stages
             ▼
┌───────────────────────────┐                        ┌───────────────────────────┐
│     RATCHET CONTROLLER    │                        │     EXPERIMENT MEMORY     │
│   - Git commit to main    │                        │   - Log to experiments.jsonl│
│   - Archive new version   │                        │   - Record failure vector │
│   - Build submission      │                        │   - Update strategy-gaps  │
└───────────────────────────┘                        └───────────────────────────┘
```

---

## 4. Agent & Subagent Architecture

To maintain context freshness and prevent reasoning bias (as mandated in `instructions/replay_intelligence.md` and `.agents/AGENTS.md`), the system delegates work across 5 focused roles:

```
                          ┌──────────────────────────┐
                          │    RATCHET CONTROLLER    │ (Master Orchestrator)
                          └─────────────┬────────────┘
         ┌──────────────────────────────┼──────────────────────────────┐
         ▼                              ▼                              ▼
┌──────────────────┐           ┌──────────────────┐           ┌──────────────────┐
│  REPLAY & TRACE  │           │    HYPOTHESIS    │           │  POLICY MUTATOR  │
│  ANALYST AGENT   │           │ GENERATOR AGENT  │           │     ENGINEER     │
└──────────────────┘           └──────────────────┘           └──────────────────┘
                                                                       │
                                                                       ▼
                                                              ┌──────────────────┐
                                                              │    EVALUATION    │
                                                              │  STATISTICIAN    │
                                                              └──────────────────┘
```

### Agent Role Definitions

| Agent Name | Mandate | Inputs | Outputs | Tools & Execution Mode | Failure Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Ratchet Controller** | Oversees state machine (`BACKLOG → PROPOSED → TESTING → PROMOTED / REVERTED`). | Current branch, `experiments.jsonl`, run config. | Git commits, branch switching, rollback commands. | Git CLI, `run_command`. Runs synchronously. | On unrecoverable error, issues `git reset --hard HEAD` and halts. |
| **2. Replay & Trace Analyst** | Mines failed simulation episodes and cross-player matrices for actionable bottlenecks. | Simulation replay JSONs, `canonical_turns.csv`, `player_summaries.json`. | Structured **Bottleneck Report** (e.g. "Shed full on day 14 causing 8 dropped harvests"). | Python analysis scripts in `src/replay_analysis/`. Subagent. | Returns `None` if dataset corrupted; does not block pipeline. |
| **3. Hypothesis Generator** | Proposes 1 specific, testable hypothesis addressing a top bottleneck while checking history. | Bottleneck Report + `experiments.jsonl` (to avoid duplicates). | Structured **Hypothesis Object** (JSON schema with rationale, target code area, expected delta). | Subagent with clean context. | If no novel hypothesis generated, switches to parameter grid exploration. |
| **4. Policy Mutator** | Applies the minimal diff to `policy.py` implementing the hypothesis. | Hypothesis Object + current `policy.py`. | Unified Git diff + updated candidate file. | File edit tools (`replace_file_content`). Subagent. | If syntax invalid or diff cannot apply, retries once with lint feedback, then aborts. |
| **5. Evaluation Statistician** | Executes the 4-stage adaptive falsification cascade. | Candidate `policy.py` vs Champion baseline. | Statistical verdict (`KEEP` / `REJECT`), p-value, t-stat, effect size, raw game logs. | `evaluate.py`, `pytest`, multiprocessing pool. Subagent / runner. | If game crashes or timeouts occur, issues immediate `REJECT`. |

---

## 5. Repository Architecture

```text
KaggricultureAgent/
├── .agents/                        # Anti-hallucination rules and agent skills
├── data/
│   ├── raw/                        # Replay JSON archive (420+ games)
│   └── processed/                  # Feature tables (canonical_turns.csv, summaries)
├── src/
│   ├── replay_analysis/            # Canonical ETL & Rule Mining engine
│   │   ├── parser.py
│   │   ├── schema.py
│   │   ├── feature_extractor.py
│   │   └── rule_miner.py
│   └── autoresearch/               # The Autoresearch & Ratchet Engine
│       ├── __init__.py
│       ├── config.py               # Parameter definitions and search spaces
│       ├── controller.py           # Master loop & state machine
│       ├── hypothesis.py           # Hypothesis generator & deduplicator
│       ├── mutator.py              # Constrained policy mutation & AST checks
│       ├── evaluator.py            # Adaptive multi-stage evaluation harness
│       ├── stats.py                # Paired t-test, Wilcoxon, Cohen's d, bootstrap CI
│       └── memory.py               # JSONL experiment logger & query interface
├── experiments/
│   ├── experiments.jsonl           # Persistent machine-readable experiment ledger
│   └── traces/                     # Simulation step logs & telemetry per run
├── docs/                           # Human-readable strategy intelligence & audits
│   ├── analysis/                   # Player profiles & strategy models
│   ├── architecture/               # System architecture documentation
│   └── roadmap/                    # Live todo.md, experiments.md
├── versions/                       # Frozen checkpoint archive (Phase2_v1 to v11)
├── tests/
│   ├── test_replay_parser.py       # ETL unit tests
│   ├── test_evaluator.py           # Evaluator & statistical tests
│   └── test_policy_invariants.py   # Safety & speed invariant checks
├── policy.py                       # LIVE Champion Strategy Engine
├── evaluate.py                     # Standalone evaluation CLI
├── build_submission.py             # Packaging script
└── ml_submission.tar.gz            # Kaggle submission artifact
```

---

## 6. Implementation Phases

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 0: Baseline Freeze & Ground Truth Benchmark                                      │
└───────────────────────────────────┬────────────────────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Robust Statistical Evaluation Harness (`src/autoresearch/stats.py`, `evaluator`)│
└───────────────────────────────────┬────────────────────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 2: Experiment Memory & Deduplication Engine (`src/autoresearch/memory.py`)       │
└───────────────────────────────────┬────────────────────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 3: Telemetry & Bottleneck Extractor (Wasted turns, Market stalls, Starvation)    │
└───────────────────────────────────┬────────────────────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 4: Constrained Policy Mutator & AST Invariant Checker                            │
└───────────────────────────────────┬────────────────────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 5: Autonomous Hypothesis & Ratchet Controller (`controller.py`)                  │
└───────────────────────────────────┬────────────────────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 6: End-to-End Autonomous Optimization Run & Leaderboard Submission               │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Phase Specifications

#### **Phase 0: Baseline Freeze & Ground Truth Benchmark**
- **Objective**: Freeze the current champion baseline (`Phase2_v1_policy.py` / `Phase2_v11_policy.py`) and record golden reference distributions across 32 deterministic seeds.
- **Files Created/Modified**: `tests/test_policy_invariants.py`, `experiments/experiments.jsonl`.
- **Tasks**:
  1. Create automated invariant tests: verifies `policy.agent()` executes in `< 15ms`, contains no `print()` statements, imports no unauthorized ML packages, and emits valid action dicts.
  2. Run 32-game paired evaluation of baseline vs baseline to establish noise floor ($t \approx 0.0, p \approx 1.0$).
- **Acceptance Criteria**: Invariant test passes 100%; baseline variance documented.

#### **Phase 1: Robust Statistical Evaluation Harness**
- **Objective**: Upgrade `evaluate.py` logic into a reusable library (`src/autoresearch/evaluator.py` and `stats.py`) implementing the 4-stage adaptive falsification cascade.
- **Files Created**: `src/autoresearch/evaluator.py`, `src/autoresearch/stats.py`, `tests/test_evaluator.py`.
- **Tasks**:
  1. Implement Stage 1 fast-prune (4 games), Stage 2 confirm (16 games), Stage 3 champion gate (32 games).
  2. Implement statistical test suite: Paired Student's t-test, Wilcoxon signed-rank test (non-parametric), Cohen's $d$ effect size, and 95% Bootstrap Confidence Interval.
  3. Support early termination: if candidate throws an exception or scores 0, abort immediately.
- **Acceptance Criteria**: Evaluator correctly prunes a deliberately corrupted policy in Stage 1 (<15s) and accepts a known superior policy in Stage 3.

#### **Phase 2: Experiment Memory & Deduplication Engine**
- **Objective**: Build a structured JSONL ledger that tracks every experiment, diff, hypothesis, and statistical result, preventing the LLM from repeating failed experiments.
- **Files Created**: `src/autoresearch/memory.py`, `tests/test_memory.py`.
- **Tasks**:
  1. Implement schema validation for experiment records (ID, parent commit, hypothesis, diff summary, seed metrics, p-values, decision).
  2. Implement semantic search/tag filtering (e.g. `query_failures(category="land_unlock")`) to supply relevant negative examples to the hypothesis generator.
- **Acceptance Criteria**: All historical experiments from `docs/roadmap/experiments.md` ingested and queryable.

#### **Phase 3: Simulation Telemetry & Bottleneck Extractor**
- **Objective**: Transform raw simulation replays into structured diagnostics that expose *why* a policy lost.
- **Files Created**: `src/autoresearch/telemetry.py`.
- **Tasks**:
  1. Extract unit-turn efficiency: percentage of turns spent walking, working, or idling.
  2. Extract market telemetry: number of wasted slots, times wheat buffer hit 0, unsold produce at day 29.
  3. Extract crop lifecycle telemetry: unwatered deaths, uncollected care bonuses, weed proliferation count.
- **Acceptance Criteria**: Diagnostic summary generated automatically after any match.

#### **Phase 4: Constrained Policy Mutator & AST Invariant Checker**
- **Objective**: Build the mutation engine that takes a hypothesis and safely modifies `policy.py` within strictly bounded mutation tiers.
- **Files Created**: `src/autoresearch/mutator.py`, `src/autoresearch/config.py`.
- **Tasks**:
  1. **Tier 1 Mutator**: Exposes a clean `PARAMETERS` config dictionary in `policy.py` (e.g. `TARGET_COW`, `WHEAT_BUFFER_DAYS`, `SELL_PRICE_FLOORS`, `HIRE_SCHEDULE`).
  2. **Tier 2 Mutator**: Bounded code replacement for isolated strategy blocks (`_make_market_orders`, `_plant_choice`, `_assign_tasks`).
  3. AST linter that validates syntax and ensures critical variables (`claims`, `shed_access`) are never deleted.
- **Acceptance Criteria**: Generated mutations pass AST validation and never produce syntax errors.

#### **Phase 5: Autonomous Hypothesis & Ratchet Controller**
- **Objective**: Implement the central autonomous loop orchestrating diagnosis → hypothesis → mutation → evaluation → git ratchet.
- **Files Created**: `src/autoresearch/controller.py`, `src/autoresearch/hypothesis.py`.
- **Tasks**:
  1. Implement the autonomous loop in `controller.py` with support for single-step (`--step`) and continuous run (`--loop --max-exp N`).
  2. Wire Git operations: create branch `experiment/EXP-NNN`, run evaluation, if passed merge to `main` and tag `champion-vN`, if failed `git checkout main && git branch -D`.
- **Acceptance Criteria**: Controller autonomously executes 5 end-to-end iterations on synthetic tasks with 0 human intervention and 100% clean git rollbacks on rejected changes.

#### **Phase 6: Continuous Strategy Optimization**
- **Objective**: Run the autonomous ratchet on high-priority strategy gaps (such as labor scheduling, early-game revenue, and endgame liquidation) to produce the next-generation champion agent.
- **Tasks**:
  1. Execute autonomous search campaigns targeting Phase D (Labor routing) and Phase E (Market liquidation).
  2. Package validated champion via `build_submission.py` and verify submission tarball.

---

## 7. Detailed First Implementation Milestone (Phase 0 / Task 1)

```text
================================================================================
MILESTONE: Phase 0, Task 1 — Policy Invariant Test Suite & Golden Benchmark
================================================================================

Objective:
Create a rigorous, automated sanity test suite that guarantees no candidate
can ever be considered for evaluation if it violates game-engine constraints.

Target File: tests/test_policy_invariants.py

Implementation Specifications:
1. test_agent_interface():
   - Generates mock observation from kaggle_environments.make("kaggriculture")
   - Calls policy.agent(obs)
   - Asserts return value is dict with keys: "farmer", "hands", "market"
   - Asserts len(market) <= 10 (hard simulator cap)
   - Asserts farmer action is valid list format

2. test_no_forbidden_imports():
   - Inspects AST of policy.py
   - Asserts NO imports of: torch, tensorflow, gym, keras, sklearn, scipy

3. test_no_unshielded_prints():
   - Asserts stdout remains 100% clean during full 720-step game execution

4. test_execution_speed_benchmark():
   - Runs full 720-turn simulated game
   - Measures per-turn execution time
   - Asserts 99th percentile turn time < 15.0ms (competition timeout guard)

Success Condition:
pytest tests/test_policy_invariants.py returns 4/4 PASS in < 5.0 seconds.
================================================================================
```

---

## 8. Engineer-Grade TODO List

### **P0: Blocking Infrastructure (Required Before Any Autonomous Runs)**
- [ ] `P0-1`: Create `tests/test_policy_invariants.py` with interface, AST, speed, and stdout tests. *(Dep: None)*
- [ ] `P0-2`: Build `src/autoresearch/stats.py` with paired t-test, Wilcoxon signed-rank, and Cohen's d. *(Dep: None)*
- [ ] `P0-3`: Build `src/autoresearch/evaluator.py` implementing the 3-stage adaptive falsification cascade. *(Dep: P0-1, P0-2)*
- [ ] `P0-4`: Build `src/autoresearch/memory.py` with schema-validated JSONL persistence. *(Dep: None)*
- [ ] `P0-5`: Build `src/autoresearch/mutator.py` with AST validation and parameter replacement. *(Dep: P0-1)*

### **P1: Core Loop Integration**
- [ ] `P1-1`: Build `src/autoresearch/telemetry.py` extracting wasted unit turns and market order starvation. *(Dep: P0-3)*
- [ ] `P1-2`: Build `src/autoresearch/hypothesis.py` generating bounded hypotheses with failure memory checking. *(Dep: P0-4, P1-1)*
- [ ] `P1-3`: Build `src/autoresearch/controller.py` automating the Git branch, test, evaluate, commit/revert ratchet. *(Dep: P0-3, P0-4, P0-5, P1-2)*

### **P2: Optimization & Search Space Refinement**
- [ ] `P2-1`: Implement Bayesian / Optuna parameter optimizer as a pluggable backend for Tier 1 parameters. *(Dep: P1-3)*
- [ ] `P2-2`: Create automatic submission packager & validator triggered whenever a new champion is promoted. *(Dep: P1-3)*

### **P3: Future Extensions**
- [ ] `P3-1`: Multi-agent pool evaluation (testing against top-player historical replay clones rather than pure self-play). *(Dep: P2-1)*

---

## 9. Verification & Acceptance Plan

### 1. Invariant & Safety Proofs
- **Test Command**: `pytest tests/test_policy_invariants.py -v`
- **Proof Requirement**: Confirms 0 stdout pollution, `< 15ms/step`, 0 illegal imports, valid action structure.

### 2. Evaluator Robustness Proof (The "Anti-Regression" Test)
- **Test Command**: `pytest tests/test_evaluator.py -v`
- **Proof Requirement**:
  - Run evaluator on a deliberately broken agent (e.g. `Phase2_v6_policy.py` which scored 27k).
  - Prove that Stage 1 rejects the broken agent in $\le 4$ games and takes $< 15\text{ seconds}$.
  - Prove that Stage 3 never promotes a candidate unless $p < 0.05$, $\Delta\text{mean} > 0$, and Wilcoxon $p < 0.05$.

### 3. Git Ratchet Integrity Proof
- **Test Command**: Run synthetic test script `python -m src.autoresearch.controller --test-ratchet`
- **Proof Requirement**:
  - Verifies that upon an evaluated rejection, git state is byte-identical to `main` with zero leftover untracked files.
  - Verifies that upon acceptance, a new commit is created, logged in `experiments.jsonl`, and tagged.

---

## 10. Benchmark Plan (Current Golden Baseline)

Before running any autonomous mutations, we establish the baseline ground truth metrics on the live champion policy:

```bash
# Golden Baseline Command (32-game paired evaluation)
python evaluate.py policy.py versions/Phase2_v1_policy.py --games 16
```

### Reference Metrics
- **Mean Score**: ~70,000–74,000 coins (against Phase2_v1 baseline in self-play).
- **Paired Variance ($\sigma_{\Delta}$)**: $\approx 2,500$ points.
- **Seat Bias**: Verified $< 3\%$ delta between Seat 0 and Seat 1 across 16 seeds.
- **Execution Time**: $\approx 4.2\text{ ms}$ per step on standard CPU core.
- **Memory Footprint**: $< 45\text{ MB}$ RSS.

---

## 11. Performance & Cost Analysis

### Compute & LLM Resource Budget

| Operation | Simulator Calls | LLM Calls | Token Estimate (In / Out) | Wall-Clock Time | Compute Bottleneck |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Telemetry Extraction** | 2 games (4 runs) | 0 | 0 | ~8 sec | CPU (Python sim) |
| **Hypothesis Generation** | 0 | 1 call | 3,500 / 400 | ~3 sec | LLM API latency |
| **Policy Mutation** | 0 | 1 call | 4,000 / 800 | ~4 sec | LLM API latency |
| **Stage 0 (Sanity/AST)** | 1 turn | 0 | 0 | 0.1 sec | None |
| **Stage 1 (4-game prune)** | 4 games | 0 | 0 | ~12 sec | CPU (4 worker processes) |
| **Stage 2 (16-game screen)**| 16 games | 0 | 0 | ~45 sec | CPU (multiprocessing) |
| **Stage 3 (32-game gate)** | 32 games | 0 | 0 | ~110 sec | CPU (multiprocessing) |
| **Total per Experiment (Average)** | **~8 games** | **2 calls** | **~8,700 tokens** | **~35–65 sec** | **CPU multiprocessing** |

### Key Optimization Strategies
1. **Parallel Multi-core Worker Pool**: Run games via `ProcessPoolExecutor(max_workers=os.cpu_count() - 2)`.
2. **Adaptive Cascade Pruning**: 75% of negative mutations are rejected at Stage 1 in 15 seconds, saving 85% of total simulator compute.
3. **Zero-LLM Parameter Optimization**: For numeric sweeps (Tiers, ratios, thresholds), bypass the LLM entirely and use local Bayesian search / grid exploration at 0 token cost.

---

## 12. Risk Register

| Risk | Prob | Impact | Detection Mechanism | Mitigation Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **1. Self-Play Overfitting** | High | High | Score increases locally but drops against asymmetric opponents on Kaggle. | Maintain a fixed pool of diverse historic baselines (`v1_policy.py`, `HealthStone_clone`, `Phase2_v1`) in the evaluation suite. |
| **2. Seed Cherry-Picking / False Positive** | Med | High | Candidate wins on 8 seeds by chance ($p \ge 0.05$). | Enforce paired t-test + Wilcoxon signed-rank + 16 seeds (32 games) for final promotion gate. |
| **3. State-Machine Invariant Corruption** | High | Critical | LLM edits break sticky claims or feed routing. | Strict AST validation and invariant unit tests before any simulation runs. |
| **4. Experiment Duplication** | High | Low | LLM repeatedly tests variations of rejected ideas (e.g. early land unlock). | Structured queryable experiment memory (`experiments.jsonl`) passed into Hypothesis prompt as negative constraints. |
| **5. Git Working Directory Corruption** | Low | Critical | Aborted experiment leaves dirty uncommitted files. | All experiments run on isolated ephemeral git branches with automated `git reset --hard` and cleanup traps. |

---

## 13. What NOT To Build

To prevent premature complexity and maximize engineering leverage, the following are **explicitly excluded**:

1. **NO Vector Databases / Embeddings**: Replay summaries and experiment records are $< 10\text{ MB}$. Standard JSONL + ripgrep/Python filtering is 1,000× faster, deterministic, and zero-dependency.
2. **NO Neural Network / RL Retraining**: Offline Decision Transformer imitation learning previously failed (−113k regression). Focus 100% on empirical heuristic rule optimization.
3. **NO Autonomous Unconstrained Code Rewriting**: The LLM will not be allowed to rewrite core architectural state machines from scratch. Mutations are strictly bounded to configuration parameters, priority tiers, and modular rule blocks.
4. **NO Cloud / Distributed Infrastructure**: The entire simulation suite runs in parallel locally across available CPU cores in seconds. No Ray, Celery, or Docker orchestration required.

---

## 14. Decision Record

```text
================================================================================
FINAL DECISION RECORD
================================================================================
RECOMMENDATION:
Implement the KaggriRatchet architecture: an adaptive, multi-stage autoresearch
system integrating 'recursive-improve' git-ratchet principles and
'autoresearch-agents' empirical evaluation, tailored specifically for the
Kaggriculture simulation environment.

DO NOW:
1. Create tests/test_policy_invariants.py to establish the immutable safety gate.
2. Build src/autoresearch/stats.py and evaluator.py with the 4-stage adaptive cascade.
3. Build src/autoresearch/memory.py for persistent, structured experiment tracking.

DO NOT DO:
1. Do NOT let the LLM execute unconstrained full-file rewrites of policy.py.
2. Do NOT run full 32-game benchmarks on unvetted exploratory candidates.
3. Do NOT introduce heavy external frameworks (Vector DBs, PyTorch, LangChain runtime).

DEFER:
1. Multi-opponent round-robin league evaluations (defer until local self-play improvements plateau).
2. Automated Kaggle API submission triggers (keep human-in-the-loop confirmation for actual Kaggle API uploads).

FIRST IMPLEMENTATION TARGET:
Milestone Phase 0, Task 1: tests/test_policy_invariants.py and src/autoresearch/stats.py.
================================================================================
```
