# Official Benchmark Ledger — Historical Checkpoints & Verification Records

> **Zero-Hallucination Protocol Compliance**: Every number in this ledger is backed by executed simulation commands and verified outputs.

---

## 1. Current Champion Benchmark

**Champion Archive**: `versions/EXP-20260815-69_policy.py` / `policy.py`  
**Evaluation Suite**: Stage 4 Opponent Pool (5 historical checkpoints, 40 total games, 8 games per opponent, dual-seat balanced).

### Opponent Breakdown:
```
  Pool: vs Phase2_v1_policy ...    Δ = +15,763   wr = 100.0%  (n=8)
  Pool: vs Phase2_v7_policy ...    Δ = +11,897   wr = 100.0%  (n=8) [strong]
  Pool: vs Phase2_v11_policy ...   Δ =  +5,654   wr = 100.0%  (n=8)
  Pool: vs EXP-20260814-12_policy  Δ = +42,388   wr = 100.0%  (n=8)
  Pool: vs EXP-20260815-69_policy  Δ =      +0   wr =  37.5%  (n=8) [strong]
```

### Summary Metrics:
- **Pool Mean Score**: **88,662**
- **Overall Win Rate**: **87.5%** (35W - 5L)
- **Win Rate vs Strong Opponents (≥65k)**: **68.8%**
- **Decision Verdict**: `KEEP / PROMOTED`

---

## 2. Seed Suite Reference Benchmarks (eval_seeds.py)

**Candidate**: `policy.py` vs `starter` (Dual-Seat, 6 games):
```
seed     7 | S0:   73,885 vs    3,455 | S1:   66,219 vs    3,478 | Mean Δ:  +66,586
seed    42 | S0:   74,838 vs    3,506 | S1:   75,516 vs    3,506 | Mean Δ:  +71,671
seed   101 | S0:  144,046 vs    3,490 | S1:  147,906 vs    3,490 | Mean Δ: +142,486
=================================================================
SUMMARY: policy.py vs starter (6 games)
Win/Loss/Tie : 6W - 0L - 0T (100.0% WR)
Mean Score   : 97,068 | Median: 75,177 | Min: 66,219 | Max: 147,906
=================================================================
```

**Candidate**: `policy.py` vs `Phase2_v1_policy.py` (Dual-Seat, 4 games):
```
  policy.py            mean 66,379   median 65,908
  Phase2_v1_policy.py  mean 43,758   median 44,084
  diff +22,622   policy.py wins 4/4
  paired t = +9.84, p = 0.000 -> SIGNIFICANT
```
