# Kagriculture Environment Rules

Kagriculture is a two-player agricultural simulation game. The season is
**30 days of 24 turns (720 steps)**, and the final score is **cash on hand at the
end — nothing else**. Land, livestock and unsold produce are worth zero at the
buzzer, so everything must be converted to money before day 29 ends.

> [!IMPORTANT]
> The authoritative rules are the environment source itself:
> `~/.local/lib/python3.14/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py`
> Read it rather than relying on this summary — earlier versions of this file
> stated a 365-day season and an asset-based score, and both were wrong.

## Core Mechanics

### 1. Farmers & Labor
- You control one permanent farmer plus hired hands.
- **Hands are dismissed every night** and must be re-hired each morning. The
  n-th hire *of a given day* costs `fib(n)` (1, 1, 2, 3, 5, 8, 13, …) — there is
  no ongoing wage, so a large crew is cheap.
- Everyone respawns on the four shed-access tiles at dawn.
- Ops: `PLANT`, `WATER`, `HARVEST`, `FEED`, `CARE`, `COLLECT_FERTILIZER`,
  `FERTILIZE`, `BUILD_PASTURE`, `BUILD_COOP`, `DIG`, `PICKUP`, `PLACE`, `DROP`,
  and the four compass moves.

### 2. Crop Cultivation
- **Crops**: Wheat, Carrot, Tomato, Strawberry, Melon.
- **Cycle**: Buy seeds -> Plant on available land -> Care (water/fertilize) -> Harvest.
- Melons are highly lucrative but slow-growing; wheat is cheap and serves as animal feed.

### 3. Animal Husbandry
- **Animals**: GOOSE (eggs, needs a COOP), COW (milk) and SHEEP (wool), both of
  which need a PASTURE.
- Each animal eats **1 WHEAT per day**. Two consecutive unfed days and it
  **escapes permanently** — the structure survives but the animal and its
  purchase price are gone. There is no health bar.
- `CARE` on a day the animal was also fed banks a bonus that **accumulates** and
  pays out on the next production day, roughly tripling yield.
- Every animal also drops **1 FERTILIZER per day for free** (base price 100),
  collected with `COLLECT_FERTILIZER`.

### 4. Dynamic Market Economy
- All resource prices (crops, seeds, animal products) fluctuate dynamically based on the global inventory supply.
- Selling in bulk drops the price; buying in bulk increases the price. Selling must be done incrementally and strategically.
