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

## Verified Mechanics (2026-08-12)

Read from source (lines 11–1063 of kaggriculture.py):

### Crop Lifecycle Details
- **STRAWBERRY & TOMATO (ongoing crops)**: Get **at most `max_yield` production ticks lifetime** (4 for both), then decay to WEED. Each tick adds 1 unit (+2 if fertilized AND watered that day). Total output: ~4–8 units per 100 seed, over days +10..+16 for strawberry.
- **WHEAT/CARROT/MELON (non-ongoing)**: Harvest clears the tile immediately (becomes `None`), allowing replanting same turn or next turn.
- **Planting day counts as unwatered** (initialized to 1, line 208). An unwatered plant dies that same night (1→2 consecutive unwatered = WEED). So new plants **must be watered the same day or they die**.
- **Yield window for non-ongoing crops**: WHEAT gains +1 per first-water-of-day during age days 2–4 (+2 if fertilized), capped at 6; unfertilized max 4. CARROT window 2–3, max 3 unfertilized. MELON window 6–12, max 6 unfertilized with ≥5 waterings.

### End-of-Day Mechanics
- All unit inventories auto-drop to shed (overflow above 100-cap is **discarded**, not returned).
- Hands are wiped (`farm["hands"] = []`).
- **Farmer is teleported to the shed spawn** (easy to miss for planning across day boundaries).
- `hires_today` resets to 0.

### Market & Timing
- Hour (0–23) is cosmetic — all 24 turns are full activity turns; market runs every turn.
- Produce `DROP`-ped this turn can be `SELL`-ed the same turn (market processes after unit ops).
- Only 10 market orders per player per turn processed; extras silently dropped.
- Atomic PLANT validation: if a turn's PLANT requests for a crop exceed seeds held, **all plants of that crop fail** that turn.

### Animals
- Animals produce even unfed (feeding only gates escape + care-bonus payout).
- `fertilizer_available` sets daily unconditionally (1 per animal).
- `CARE` + `FEED` same day banks a `pending_care_bonus` that accumulates and is paid on the next production day (roughly triples yield if all animals cared daily).

### Land & Building
- `BUY_LAND` order is **forced order**: NE → SW → SE (not choosable).
- `BUILD_PASTURE` / `BUILD_COOP` are **free** (any unit, empty tile).
- Newly unlocked tiles are empty (`None`), not weeds.
