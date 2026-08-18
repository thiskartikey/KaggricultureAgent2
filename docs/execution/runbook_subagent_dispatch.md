# Subagent Dispatch Runbook & Orchestration Protocol

> **Zero-Hallucination Protocol (§3 of `.agents/AGENTS.md`)**: Mandatory Subagent Delegation Recipes.

---

## 1. Subagent Dispatch Protocol

When delegating tasks to AI subagents during complex iterative development:
1. **Clean Context Window**: Subagent begins with an unpolluted context window.
2. **Explicit Contracts**: Every dispatch MUST define exact inputs, explicit return conditions, and formatted return structures.
3. **Never Chain Assumptions**: Outputs must be verified with active tool execution.

---

## 2. Mandatory Subagent Recipes

### Recipe 1: Deep Reasoning (Multi-Worker Pathfinding & Tile Assignment)
```markdown
Task: Analyze the worker assignment algorithm in `policy.py` (`_assign_tasks` and `_unit_op`).
Context:
- `policy.py` lines 630 to 860.
- Workers frequently suffer from travel overhead when walking between shed and animal pastures.
Goal:
1. Formulate an optimal Manhattan-distance greedy matching that combines Wheat pickup with Pasture servicing into a single compound route.
2. Formally prove that the algorithm produces zero worker oscillations and zero deadlock states.
Return Condition:
Return Python AST replacement chunk for `_assign_tasks` and `_unit_op` with unit test verifying zero oscillations.
```

---

### Recipe 2: Strategy Exploration (Replay Strategy Extraction)
```markdown
Task: Mine top-3 player replays for dynamic shop-response heuristics.
Context:
- Replay files in `replays/` from players Ezzzzzekki, GiovanniCR, ThunderThunder.
- `src/replay_analysis/rule_miner.py`.
Goal:
1. Extract the conditional crop planting distribution when Bakery, Pizza Shop, and Brunch Spot are unlocked.
2. Compare revenue yield when shifting 10 Strawberry tiles to Wheat/Tomato under 2x Bakery vs static 42 Strawberry baseline.
Return Condition:
Return a comparative tradeoff matrix with exact parameter formulas for `_seed_targets(obs)`.
```

---

### Recipe 3: Code Review Subagent (Mandatory for Diff > 50 lines)
```markdown
Task: Perform a strict security, invariant, and performance review on proposed changes to `policy.py`.
Checklist:
1. Interface Contract: Does `agent(obs, config)` return `{"farmer": [...], "hands": [...], "market": [...]}`?
2. Stdout Cleanliness: Are there ANY unshielded `print()` statements in runtime paths?
3. Step Time: Does step execution remain under 15ms?
4. Edge Case Safety: Does the code handle `money < 10`, `empty tiles`, `seed deficit`, and `step == 719` gracefully?
Return Condition:
Return PASS/FAIL verdict with line-by-line findings.
```

---

### Recipe 4: Adversarial Testing Subagent
```markdown
Task: Stress-test candidate policy against adversarial seeds and catastrophic economic conditions.
Suite:
1. Zero Cash Start / Immediate Debt.
2. Market Glut: All crop prices drop to $1 floor.
3. Severe Weed Outbreak: 50%+ farm overgrown with weeds.
4. Opponent Flooding: Opponent sells 10 units of wheat/strawberries every turn.
Return Condition:
Execute 20 hostile games and report survival rate, error count, and final score distribution.
```
