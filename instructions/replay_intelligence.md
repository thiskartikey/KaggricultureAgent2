# Kaggriculture Replay Intelligence & Strategy Engineering Protocol

> **Authoritative Operational Instructions for AI Agents**
> **Scope**: Extraction, normalization, behavioral analysis, strategy reconstruction, gap analysis, and evidence-gated implementation from the Top-4 Player Replay Corpus (`Ezzzzzekki`, `GiovanniCR`, `HealthStone`, `ThunderThunder`).
> **Core Mandate**: Evidence-first execution. Zero unverified assumptions. No strategy code modification until full empirical analysis and baseline benchmarking are complete.

---

## 1. High-Level Mission & Execution Philosophy

The goal is to convert the 420+ historical replays of the top 4 leaderboard players into an empirical, mathematically validated, high-performing strategy for `KaggricultureAgent`.

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   THE PIPELINE                                          │
│                                                                                         │
│  420+ Raw Replays ──► Structured Dataset ──► Behavioral Analysis ──► Extracted Rules   │
│                                                                             │           │
│  Evaluation ◄── Agent Implementation ◄── Gated Roadmap ◄── Strategy Model ◄─┘           │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Golden Principles
1. **Never guess what the data contains.** Inspect the actual raw replay keys, types, and values using Python scripts before designing schemas.
2. **Never confuse correlation with causation.** A player winning a game does not prove every micro-action they took was optimal. Look for consistent patterns across dozens of games ($n \ge 30$).
3. **Never modify production strategy code (`policy.py`) before Phase 9C.** All early phases are strictly analytical and observational.
4. **Always benchmark against the frozen control baseline.** Baseline is `versions/Phase2_v1_policy.py` evaluated via `evaluate.py` ($16+$ games, paired $t$-test, $p < 0.05$).
5. **Enforce Zero-Hallucination output discipline.** Every claim must cite concrete replay IDs, sample sizes ($n$), means, medians, standard deviations, and actual command outputs.

---

## 2. Directory & Workspace Standards

All artifacts produced during this initiative must strictly adhere to the following directory layout inside `KaggricultureAgent/`:

```text
KaggricultureAgent/
├── data/
│   ├── raw/                       # Symlinks or read-only references to replays/
│   └── processed/
│       ├── dataset_inventory.csv  # Metadata of all 420 replays
│       ├── canonical_turns.parquet# (or .csv/.jsonl) Normalized per-turn state-action data
│       └── player_summaries.json  # Aggregated per-player strategy profiles
│
├── src/
│   └── replay_analysis/
│       ├── __init__.py
│       ├── schema.py              # Canonical dataclasses & validation models
│       ├── parser.py              # Robust raw JSON -> canonical parser
│       ├── feature_extractor.py   # State-action vectorizer and timeline segmenter
│       ├── statistics.py          # Aggregator, distribution fitter, correlation calculator
│       └── rule_miner.py          # Conditional decision rule extraction engine
│
├── tests/
│   ├── test_replay_parser.py      # Unit tests for malformed & valid replay handling
│   └── test_canonical_schema.py   # Schema integrity tests
│
├── docs/
│   ├── architecture/
│   │   ├── current-agent.md       # Deconstructed audit of current policy.py
│   │   ├── replay-system.md       # Technical design of parser & data pipeline
│   │   └── strategy-integration.md# How mined rules plug into heuristic tiers
│   │
│   ├── analysis/
│   │   ├── replay-schema.md       # Exact JSON structure of raw vs processed data
│   │   ├── data-limitations.md    # Hidden info, missing fields, format quirks
│   │   ├── player_ezzzzzekki.md   # Deep dive on player 1 (91 replays)
│   │   ├── player_giovannicr.md   # Deep dive on player 2
│   │   ├── player_healthstone.md  # Deep dive on player 3
│   │   ├── player_thunder.md      # Deep dive on player 4
│   │   ├── cross-player-matrix.md # Comparative analysis across all 4 players
│   │   ├── decision-rules.md      # Full catalog of extracted conditional rules
│   │   └── strategy-model.md      # Unified 10-pillar strategy blueprint
│   │
│   ├── strategy/
│   │   ├── current-strategy.md    # Baseline A1 heuristic documentation
│   │   ├── strategy-gaps.md       # Prioritized gap analysis (Impact x Conf / Cost)
│   │   └── strategy-changelog.md  # Versioned log of accepted strategy changes
│   │
│   └── roadmap/
│       ├── roadmap.md             # Multi-phase execution schedule
│       ├── todo.md                # Live state-machine task tracker
│       └── experiments.md         # A/B hypothesis testing logs with p-values
│
└── instructions/
    └── replay_intelligence.md     # This authoritative specification
```

---

## 3. Step-by-Step Phase Execution Protocols

### Phase 0: Repository and Environment Audit
**Objective**: Establish complete clarity on how `KaggricultureAgent` functions today and where external strategy blueprints can be introduced without breaking the submission build.

#### Execution Tasks:
1. **Audit Agent Entry Points**:
   - Inspect `main.py` and `ml_main.py`. Confirm standard I/O communication and execution lifecycle.
   - Trace how `obs` is passed to `policy.py` -> `agent(obs)`.
2. **Audit Strategy Engine (`policy.py`)**:
   - Map the task assignment pipeline: `_scan()` -> `_build_tasks()` -> `_assign_tasks()` -> `_make_market_orders()`.
   - Document the existing 7 task tiers (`service`, `water`, `harvest`, `place`, `build`, `plant`, `weed`).
   - Audit the sticky-claim worker state machine and feed-carrier routing logic.
   - Verify disconnected/dead code (e.g. `DecisionTransformer` and `rl_weights.npz`).
3. **Audit Simulation & Testing Harness**:
   - Inspect `evaluate.py`. Verify paired seed execution, seat swapping (Seat 0 vs Seat 1), multi-processing worker pools, and paired $t$-test calculations.
   - Run a 2-game smoke test to confirm environment health:
     ```bash
     python evaluate.py policy.py versions/Phase2_v1_policy.py --games 2
     ```
4. **Deliverables**:
   - `docs/architecture/current-agent.md`
   - `docs/architecture/replay-system.md`
   - `docs/architecture/strategy-integration.md`

---

### Phase 1: Replay Corpus Discovery & Schema Audit
**Objective**: Inventory all 420 downloaded replays across the 4 top players and document the exact JSON structure and observability boundaries.

#### Execution Tasks:
1. **Corpus Inventory**:
   - Traverse `replays/Ezzzzzekki/`, `replays/GiovanniCR/`, `replays/HealthStone/`, `replays/ThunderThunder/`.
   - Extract metadata for every replay: Episode ID, Player 0 name, Player 1 name, Winner, Final Scores, Game Length (steps), File Size, Parse Status.
   - Output to `data/processed/dataset_inventory.csv`.
2. **Raw Schema Inspection**:
   - Inspect the structure of raw replay JSONs (`steps`, `environment`, `configuration`, `rewards`, `info`).
   - Determine what is **OBSERVABLE** in replays:
     - Board tiles for both players (`tiles[10][10]`)
     - Unit positions (`farmer`, `hands`)
     - Market inventory and prices per step
     - Town shops unlocked
     - Per-step actions executed by both players
     - Unlocked quadrants
   - Determine what is **HIDDEN / INFERRED**:
     - Opponent's private shed items and seeds (must be reconstructed from purchase/harvest/sell actions)
     - Unit-level inventory payloads (must be inferred from pickup/drop/harvest/care actions)
3. **Deliverables**:
   - `data/processed/dataset_inventory.csv`
   - `docs/analysis/replay-schema.md`
   - `docs/analysis/data-limitations.md`

---

### Phase 2: Canonical Replay Parser & Dataset Builder
**Objective**: Build a high-performance, deterministic parser in `src/replay_analysis/` that transforms raw JSON replays into a clean tabular/structured dataset with zero information loss.

#### Canonical Turn Record Schema:
Each turn in the processed dataset must capture:
```json
{
  "episode_id": "91449177",
  "step": 144,
  "day": 6,
  "hour": 0,
  "player_name": "Ezzzzzekki",
  "player_index": 0,
  "opponent_name": "OpponentX",
  "money": 3450,
  "unlocked_quadrants": ["NW", "NE"],
  "num_hands": 8,
  "crop_counts": {"WHEAT": 5, "CARROT": 0, "TOMATO": 0, "STRAWBERRY": 12, "MELON": 0},
  "animal_counts": {"COW": 0, "SHEEP": 0, "GOOSE": 0},
  "structures": {"PASTURE": 0, "COOP": 0},
  "actions_summary": {
    "num_plant": 2,
    "num_water": 5,
    "num_harvest": 0,
    "num_care": 0,
    "num_feed": 0,
    "num_build": 0,
    "num_dig": 0
  },
  "market_orders": [["BUY_SEED", "STRAWBERRY", 12], ["HIRE"]],
  "market_prices": {"STRAWBERRY": 120, "WHEAT": 25, "MILK": 160, "WOOL": 200},
  "market_inventory": {"STRAWBERRY": 1000, "WHEAT": 5000},
  "town_shops": ["BAKERY", "YARN_STORE"],
  "final_score": 142500,
  "final_reward": 1.0
}
```

#### Parser Engineering Requirements:
1. **Fault Tolerance**: Safely handle truncated replays or missing optional fields without crashing.
2. **Reproducibility**: Scriptable via `python -m src.replay_analysis.parser --input replays/ --output data/processed/`.
3. **Unit Tests**: Create `tests/test_replay_parser.py` testing against valid, corrupt, and edge-case replay payloads.
4. **Deliverables**:
   - `src/replay_analysis/parser.py`
   - `src/replay_analysis/schema.py`
   - `data/processed/canonical_turns.parquet` (or `.csv`)
   - `tests/test_replay_parser.py`

---

### Phase 3: Individual Player & Phase Analysis
**Objective**: Profile the temporal progression of games for each of the 4 top players across three distinct phases.

#### Temporal Windows:
1. **Opening Phase (Days 0 – 6 / Steps 0 – 167)**:
   - Initial cash allocation (Day 0 seed purchases vs labor hiring).
   - First quadrant unlock timing (Day of NE purchase, money threshold).
   - Starter crop selection (Wheat vs Strawberry vs Carrot vs Melon).
   - Labor ramp curve (hires on Day 0, Day 1..6).
2. **Midgame Engine (Days 7 – 20 / Steps 168 – 503)**:
   - Second and third quadrant unlock timing (Days of SW and SE purchases).
   - Transition to livestock (Pasture count, Cow vs Sheep ratio, placement geometry).
   - Daily maintenance protocol (Feeding wheat supply chain, CARE execution rate, Fertilizer harvesting).
   - Strawberry production rhythm (batch planting cycles, fertilization timing).
   - Melon expansion (planting day windows, watering bonus tracking).
3. **Endgame Liquidation (Days 21 – 29 / Steps 504 – 719)**:
   - Cutoff days: Last planting day for Wheat, Strawberry, Melon, Carrot.
   - Pasture and livestock sunsetting (when does feeding stop, when is milk/wool harvested).
   - Shed emptying and market sale cadence (turn-by-turn volume to minimize price crash).
   - Final money maximization before step 719.
4. **Deliverables**:
   - `docs/analysis/player_ezzzzzekki.md`
   - `docs/analysis/player_giovannicr.md`
   - `docs/analysis/player_healthstone.md`
   - `docs/analysis/player_thunder.md`

---

### Phase 4: Cross-Game Statistical Mining & Invariant Extraction
**Objective**: Aggregate the dataset across all 420 replays to calculate exact mathematical distributions, thresholds, and correlations.

#### Metrics to Compute (Report Mean, Median, StdDev, Min, Max, $n$):
1. **Land Expansion Milestones**:
   - Day of 2nd quadrant unlock (NE): Distribution and win-rate correlation.
   - Day of 3rd quadrant unlock (SW): Distribution and win-rate correlation.
   - Frequency of 4th quadrant unlock (SE, cost 4000): Win-rate comparison (3-quad vs 4-quad).
2. **Daily Labor Trajectory**:
   - Average crew size per day ($d \in [0, 29]$).
   - Marginal ROI of crew sizes (11 vs 12 vs 13 vs 14 hands).
3. **Livestock Economics**:
   - Total pastures built by Day 15, Day 20, Day 25.
   - Cow to Sheep ratio.
   - Percentage of active livestock receiving `CARE` and `FEED` daily.
4. **Crop Portfolio Allocation**:
   - Total lifetime seeds purchased by crop type: `[WHEAT, CARROT, TOMATO, STRAWBERRY, MELON]`.
   - Spatial layout patterns (clustering of animals near shed vs perimeter crops).
5. **Market Liquidation Dynamics**:
   - Average sell order batch size ($n$ units per order).
   - Hourly market transaction distribution.
6. **Deliverables**:
   - `docs/analysis/cross-player-matrix.md`
   - Data summaries in `data/processed/player_summaries.json`

---

### Phase 5: Top-4 Comparative Synthesis
**Objective**: Build a definitive comparison matrix between `Ezzzzzekki`, `GiovanniCR`, `HealthStone`, and `ThunderThunder`.

#### Taxonomy of Strategies:
| Category | Definition | Action for Agent |
| :--- | :--- | :--- |
| **Shared Invariants** | Behaviors exhibited by $\ge 3$ players in $\ge 80\%$ of wins | **MANDATORY ADOPTION** |
| **Player Innovations** | Unique high-efficiency mechanics used by 1 player with superior win rate | **HIGH-PRIORITY EXPERIMENT** |
| **Situational Tactics** | Reactive responses to shop unlocks or market gluts | **CONDITIONAL RULE** |
| **Suboptimal Artifacts** | Actions with negative win-rate correlation or high cost / zero yield | **EXPLICIT BLACKLIST** |

#### Deliverables:
- `docs/analysis/cross-player-matrix.md`

---

### Phase 6: Decision Rule Cataloging
**Objective**: Formalize empirical discoveries into unambiguous, deterministic IF-THEN production rules.

#### Rule Specification Standard:
Every extracted rule must be documented in `docs/analysis/decision-rules.md` using the exact format:

```markdown
### RULE-LIVESTOCK-004: Pasture Cow-to-Sheep Ratio Balancing
- **ID**: `RULE-LIVESTOCK-004`
- **Category**: Livestock / Husbandry
- **Condition Predicate**:
  - `game.day >= 11`
  - `farm.unlocked_quadrants.count >= 3`
  - `farm.structures.pasture.count < 14`
  - `farm.money >= 350` (Pasture build free, Cow 300, Sheep 200)
- **Action**:
  - If `cows.count < 8`: Buy 1 Cow, Place on new Pasture.
  - Else if `sheep.count < 6`: Buy 1 Sheep, Place on new Pasture.
- **Empirical Evidence**:
  - Observed in 88% of Ezzzzzekki wins ($n=80$) and 92% of GiovanniCR wins ($n=75$).
  - Average score with 8 Cow / 6 Sheep: $138,400 \pm 12,200$.
  - Average score with pure Cows (14 Cow): $118,200 \pm 15,100$ (market milk glut causes price collapse to \$1).
- **Confidence**: 95% ($p < 0.001$)
- **Implementation Complexity**: Low (edit `_make_market_orders` in `policy.py`).
- **Expected Score Impact**: $+8,000$ to $+15,000$.
```

#### Deliverables:
- `docs/analysis/decision-rules.md`

---

### Phase 7: Coherent 10-Pillar Strategy Model
**Objective**: Assemble the extracted rules into a non-contradictory, unified master strategy blueprint.

#### The 10 Strategy Pillars:
1. **Pillar 1: Opening Acceleration (Days 0–6)**: Bootstrap economy with high-turnover crops and targeted labor.
2. **Pillar 2: Land Acquisition Blueprint**: Strict quadrant unlock schedule (NE Day 7, SW Day 11, SE evaluation).
3. **Pillar 3: Labor Scaling & Daily Budgeting**: Fibonacci re-hire curve optimized per game phase.
4. **Pillar 4: Dual-Livestock Husbandry Engine**: 8 Cow + 6 Sheep asset engine with daily CARE/FEED synchronization.
5. **Pillar 5: Crop Rotation & Life-Cycle Management**: Strawberry ongoing batching, Melon long-cycle timing, Wheat feed buffer.
6. **Pillar 6: Worker Routing & Sticky Task Allocation**: Zero-oscillation nearest-neighbor dispatch with dedicated cargo roles.
7. **Pillar 7: Market Order Optimization**: Price-curve-aware selling, avoiding gluts, buying wheat buffers before market spikes.
8. **Pillar 8: Town Demands & Dynamic Adaptation**: Exploiting shop demand multipliers.
9. **Pillar 9: Endgame Depletion & Liquidation (Days 22–29)**: Strict planting cutoffs, animal liquidation, orderly produce sell-off.
10. **Pillar 10: Fault Tolerance & Recovery Protocols**: Anti-starvation safeguards, weed clearing, lost worker recovery.

#### Deliverables:
- `docs/analysis/strategy-model.md`

---

### Phase 8: Current Agent Gap Analysis
**Objective**: Audit the current `policy.py` against the 10-Pillar Strategy Model and compute a mathematical priority score for every discrepancy.

#### Prioritization Matrix:
$$\text{Priority Score} = \frac{\text{Expected Impact (points)} \times \text{Evidence Confidence } (0.0 - 1.0)}{\text{Implementation Cost (1 = trivial, 5 = massive refactor)}}$$

#### Deliverables:
- `docs/strategy/strategy-gaps.md`

---

### Phase 9: Phased Engineering Roadmap
**Objective**: Convert prioritized gaps into concrete, gated engineering milestones.

```text
Phase A (Telemetry & Logging) 
      └──► Phase B (Freeze Control Baseline)
                 └──► Phase C (High-Confidence Parameter Tuning)
                            └──► Phase D (Routing & Operational Logic)
                                       └──► Phase E (Market & Liquidation)
                                                  └──► Phase F (Full Validation & Promotion)
```

#### Milestone Gates:
- **Gate 1**: Replay analysis complete with $n \ge 300$ parsed games before any code change.
- **Gate 2**: Baseline `Phase2_v1_policy.py` benchmarked on 16 games ($8$ seeds $\times 2$ seats).
- **Gate 3**: Every strategy PR evaluated with `python evaluate.py policy.py versions/Phase2_v1_policy.py --games 8`.
- **Gate 4**: Promotion to new baseline requires $p < 0.05$ with positive $\Delta\text{mean}$ across $\ge 16$ games.

#### Deliverables:
- `docs/roadmap/roadmap.md`

---

### Phase 10: Task Tracking & State Machine
**Objective**: Maintain an active, machine-readable `docs/roadmap/todo.md` tracking every engineering task.

#### Task State Machine:
$$\text{BACKLOG} \longrightarrow \text{READY} \longrightarrow \text{IN\_PROGRESS} \longrightarrow \text{VALIDATING} \longrightarrow \begin{cases} \text{DONE} \\ \text{REJECTED} \end{cases}$$

#### Task Record Format:
```markdown
- [ ] `TASK-STRAT-001`: Implement Dual-Livestock 8 Cow / 6 Sheep Ratio
  - **Phase**: Phase C
  - **Reason**: Single-species livestock gluts market price to $1. Top players split 8/6.
  - **Evidence**: Replay analysis doc `player_ezzzzzekki.md` (n=80, p<0.001).
  - **Files**: `policy.py` (`_make_market_orders`, `_build_tasks`)
  - **Acceptance Criteria**: Agent purchases max 8 cows and max 6 sheep; milk price stays >$60.
  - **Test Command**: `python evaluate.py policy.py versions/Phase2_v1_policy.py --games 8`
  - **Priority**: High (Score: 2800)
  - **Status**: READY
```

#### Deliverables:
- `docs/roadmap/todo.md`

---

### Phase 11: Scientific Experimentation Framework
**Objective**: Log all strategy mutations as formal scientific experiments in `docs/roadmap/experiments.md`.

#### Experiment Log Template:
```markdown
## EXP-20260814-01: Dual Livestock Split (8 Cow / 6 Sheep)
- **Hypothesis**: Splitting pastures into 8 Cows and 6 Sheep will prevent milk market collapse and increase mean score by $\ge 8,000$ points vs pure cow baseline.
- **Baseline**: `versions/Phase2_v1_policy.py` (Mean: 111,450)
- **Mutation Diff**: Modified `_make_market_orders` in `policy.py` lines 840-865.
- **Test Protocol**: 8 seeds x 2 seats = 16 games head-to-head.
- **Results**:
  - Policy Mean: 122,800
  - Baseline Mean: 111,200
  - $\Delta\text{Mean}$: $+11,600$
  - Paired $t$-stat: 3.42, $p$-value: 0.0038 ($p < 0.05$)
  - Win Rate: 13 / 16 (81.25%)
- **Verdict**: ACCEPT (Promoted to new baseline `versions/Phase2_v2_policy.py`).
```

#### Deliverables:
- `docs/roadmap/experiments.md`

---

### Phase 12: Regression Guard & Submission Verification
**Objective**: Protect against fatal regressions before building final submission packages.

#### Pre-Submission Guard Checklist:
1. **Zero-Dependency Check**: No external ML packages (PyTorch, TensorFlow, Gym) imported in `policy.py` or `ml_main.py`.
2. **Stdout Cleanliness**: Grep for unshielded `print()` statements:
   ```bash
   ! git diff --cached -- '*.py' | grep -n '^\+.*\bprint('
   ```
3. **Execution Speed Check**: Heuristic policy execution time $< 15\text{ ms}$ per step.
4. **Archive Build & Smoke Test**:
   ```bash
   python build_submission.py
   # Verify tarball contains only main.py, heuristic.py, policy.py
   tar -ztvf ml_submission.tar.gz
   ```
5. **Full Regression Evaluation**: $\ge 16$ games against the previous validated release.

#### Deliverables:
- `docs/strategy/strategy-changelog.md`

---

## 4. Subagent Delegation Playbook

When executing complex phases of this protocol, the primary agent MUST spawn specialized subagents to preserve context freshness and prevent reasoning bias:

```text
┌──────────────────────────┬────────────────────────────────────────────────────────┐
│ Task Category            │ Subagent Role & Mandate                                │
├──────────────────────────┼────────────────────────────────────────────────────────┤
│ Replay Parsing & ETL     │ "Parser Subagent" — batch parse 100 replays, validate  │
│ Deep Statistical Mining  │ "Data Mining Subagent" — compute cross-game metrics    │
│ Strategy Synthesis       │ "Architect Subagent" — resolve rule conflicts          │
│ Adversarial Validation   │ "Red Team Subagent" — find flaw/glitch in proposed rule │
│ Code Review & Safety     │ "Diff Review Subagent" — check stdout, imports, leaks  │
└──────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 5. Execution Command Cheatsheet

```bash
# 1. Inspect replay directory
ls -la replays/Ezzzzzekki | head -n 20

# 2. Run parser test suite
pytest tests/test_replay_parser.py -v

# 3. Execute canonical dataset generation
python -m src.replay_analysis.parser --input replays/ --output data/processed/

# 4. Run local head-to-head A/B evaluation (16 games)
python evaluate.py policy.py versions/Phase2_v1_policy.py --games 8

# 5. Build and verify submission tarball
python build_submission.py && tar -ztvf ml_submission.tar.gz
```
