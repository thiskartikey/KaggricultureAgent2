# Heuristic Rule-Based System

The rule-based heuristics located in [heuristic.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/heuristic.py) act as both the standalone baseline agent and the low-level micro-management fallback inside the main reinforcement learning agent loop.

## Core Heuristics Components

### 1. Market Pricing Estimation
To prevent buying high and selling low, the heuristic models market prices using supply/demand elasticity equations.
- Pricing parameters are stored in `MARKET_PARAMS` for crops, seeds, fertilizer, and animal yields.
- Non-linear transformations (`log`, `sqrt`, `sq`, `linear`) scale the prices based on inventory levels compared to a base index (`I0`).

### 2. Operational Priorities
When allocating farmers to daily operations, the heuristic runs through a prioritized queue of actions:
1. **Care (Watering/Feeding)**: Keep existing crops and animals alive.
2. **Harvest**: Gather mature products to lock in value and free up land.
3. **Pasture Building**: Expand housing for livestock if pasture capacities are met.
4. **Planting**: Seed open land based on seed availability and target crop ratios.

### 3. Inventory Reserve Thresholds
- The agent maintains a minimum cash reserve (`min_reserve`) to prevent bankruptcy from farmer wages.
- Seed restocking levels (`seed_restock`) ensure we do not run out of seeds for planting.
