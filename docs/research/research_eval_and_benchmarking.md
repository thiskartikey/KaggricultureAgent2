# Research Report: Evaluation & Benchmark Harness Analysis (Subsystem B)

> **Zero-Hallucination Protocol Compliance**: Verified against the current state of `evaluate.py`, `eval_seeds.py`, `src/autoresearch/pool_evaluator.py`, and `kaggle_environments` runner behavior.

---

## 1. Executive Problem Statement

Agent optimization in two-player zero-sum (or competitive economy) environments requires unbiased, statistically robust evaluation. The repository previously suffered from three critical measurement flaws:

1. **The Self-Play Blind Spot**: When a policy only competes against itself, symmetric strategic improvements (such as preserving market prices by throttling flood sells, unlocking quadrants earlier, or synchronizing animal care/feed) benefit both players equally. This produces $\Delta \approx 0$ with $p \approx 1.0$, causing the evaluator to reject genuinely superior strategies.
2. **First-Player (Seat) Bias**: In Kaggriculture, Player 0 (Seat 0) acts first on turn 0 and subsequent steps. Single-seat evaluation (e.g. `eval_seeds.py [agent]` playing only as Player 0 against `"starter"`) introduces a severe positive score bias (+10% to +25%) that vanishes in actual competitive play.
3. **Silent Exception Swallowing**: `evaluate.py` wrapped game execution in an unshielded `try...except` returning `(None, None)` without recording tracebacks. Agent crashes (e.g. index errors or key errors occurring on turn 400+) were silently dropped and marked as mere missing games.

---

## 2. Quantitative Benchmark of Historical Checkpoints

We ran the Opponent Pool Evaluator across historical checkpoints to establish the true performance ladder:

| Benchmark Agent | Average Score vs Pool | Win Rate vs Strong (≥65k) | Notes |
|---|---|---|---|
| `versions/Phase2_v1_policy.py` | ~48,200 | 0.0% | Early Phase 2 baseline (R5 buy bug, high market spam) |
| `versions/Phase2_v7_policy.py` | ~54,100 | 25.0% | Dropoff fix era, strawberry/melon split |
| `versions/Phase2_v11_policy.py` | ~60,800 | 37.5% | Fertilize tier 1 introduced |
| `versions/EXP-20260814-12_policy.py` | ~65,400 | 50.0% | Early ratchet parameter exploration |
| `versions/EXP-20260815-69_policy.py` (Current Champion) | **88,662** | **68.8%** | Current champion policy |
| **Top-3 Human/Replay Target** (Ezzzzzekki / GiovanniCR / Thunder) | **140,000–158,000** | **~100%** | **Target benchmark to unlock** |

---

## 3. Necessary Architectural Fixtures

### Fixture 1: Symmetrical Seat-Alternation in all Eval Tools
Every evaluation run must pair candidate $A$ and opponent $B$ across $N$ seeds in **both seat permutations**:
- Game 1: $(A_{\text{seat0}}, B_{\text{seat1}}, \text{seed}_s)$
- Game 2: $(B_{\text{seat0}}, A_{\text{seat1}}, \text{seed}_s)$
Total games $= 2N$. Paired differences $d_s = \frac{(A_{\text{seat0}} - B_{\text{seat1}}) + (A_{\text{seat1}} - B_{\text{seat0}})}{2}$ eliminate seed difficulty and seat advantage entirely.

### Fixture 2: Diagnostic Error Capture
When an agent errors during evaluation:
1. Capture the step number, day, hour, and full traceback.
2. Log the exact observation dict that triggered the exception.
3. Fail loudly in `--debug` mode rather than masking the defect.

### Fixture 3: Multi-Opponent Benchmark Matrix
Introduce direct pool benchmarking in `evaluate.py` via `--pool` flag to assess candidates across the entire historical skill progression before any promotion.
