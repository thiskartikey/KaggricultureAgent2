"""
Theoretical max revenue calculation for Kaggriculture.
Given: 30 days, 75 usable tiles (3 quadrants), 8 pastures, 14 animals.
"""
import math

# Market params mirror the game engine
_FUNCS = {
    "linear": lambda x: float(x),
    "sq":     lambda x: float(x) * float(x),
    "sqrt":   lambda x: math.sqrt(x),
    "log":    lambda x: math.log(1.0 + x),
    "log10":  lambda x: math.log10(1.0 + x),
}
MARKET_PARAMS = {
    "WHEAT":      (25,  10000, 400, "sqrt",   0.80, "log",    0.20),
    "STRAWBERRY": (120, 10000, 100, "sqrt",   0.70, "linear", 1.60),
    "MELON":      (250, 10000, 300, "log",    0.20, "sq",     3.60),
    "MILK":       (160, 10000, 122, "sqrt",   0.60, "linear", 1.60),
    "WOOL":       (200, 10000, 105, "log",    0.20, "sq",     3.20),
    "FERTILIZER": (100, 10000, 200, "linear", 0.40, "linear", 0.40),
}

def price(resource, inv):
    base, I0, T, bf, bt, af, at = MARKET_PARAMS[resource]
    if inv < I0:
        f = _FUNCS[bf]
        p = base + (bt * base / f(T)) * f(I0 - inv)
    elif inv > I0:
        f = _FUNCS[af]
        p = base - (at * base / f(T)) * f(inv - I0)
    else:
        p = float(base)
    return max(1, int(round(p)))

def sell_batch(resource, qty, start_inv=0):
    """Revenue from selling `qty` units starting from `start_inv` in market."""
    rev = 0
    inv = start_inv
    for _ in range(int(qty)):
        p = price(resource, inv)
        rev += p
        if p > 1:
            inv += 1
    return rev

print("=" * 60)
print("THEORETICAL MAX REVENUE BREAKDOWN")
print("=" * 60)

# --- Farm layout: 3 quadrants (75 tiles) ---
# 14 PASTURE (8 COW + 6 SHEEP), rest is crops
# ~53 planting tiles = 14 STRAWBERRY, 30 MELON, 8 WHEAT, 1 reserved
PASTURES = 14  # 8 cow + 6 sheep
CROP_TILES = 75 - PASTURES  # = 61

# Actually top players use ~42 STRAWBERRY, 12 MELON (from docstring)
# Let's compute for both our current target and their "optimal"

print("\n--- Animal Revenue (per-animal, 30 days) ---")
# COW: MILK every 2 days after first 8 days => ~(30-8)//2 + 1 = 12 milks
# SHEEP: WOOL every 3 days after first 6 days => ~(30-6)//3 + 1 = 9 wools
# Each also produces 1 FERTILIZER/day = ~30 fertilizer total per animal (ongoing)

cows = 8
sheep = 6
milk_per_cow = (30 - 8) // 2 + 1  # 12
wool_per_sheep = (30 - 6) // 3 + 1  # 9

milk_total = cows * milk_per_cow
wool_total = sheep * wool_per_sheep
fert_total = (cows + sheep) * 30  # rough (14 animals * 30 days)

milk_rev = sell_batch("MILK", milk_total)
wool_rev = sell_batch("WOOL", wool_total)
fert_rev = sell_batch("FERTILIZER", fert_total)

print(f"  Cows: {cows} x {milk_per_cow} MILK = {milk_total} MILK -> {milk_rev:,} coins")
print(f"  Sheep: {sheep} x {wool_per_sheep} WOOL = {wool_total} WOOL -> {wool_rev:,} coins")
print(f"  Fertilizer: {fert_total} units -> {fert_rev:,} coins")
print(f"  Animal subtotal: {milk_rev + wool_rev + fert_rev:,}")

print("\n--- Current Crop Targets (ours: 30 STRAWBERRY, 62 MELON, 8 WHEAT) ---")
# STRAWBERRY: ongoing every 2 days after day 10 => (30-10)//2 + 1 = 11 harvests, 4 yield each
# MELON: one-shot at day 12, 6 yield each
# WHEAT: one-shot at day 4, 6 yield each, but multiple cycles ~3-4 cycles

straw_tiles = 30
melon_tiles = 62
wheat_tiles = 8

straw_harvests = (30 - 10) // 2 + 1  # 11
melon_harvests = 1  # one-shot but recycled; let's say 2 (plant early + replant)
wheat_harvests = 4  # plant days 0, 4, 8, 12...

straw_total = straw_tiles * straw_harvests * 4
melon_total = melon_tiles * melon_harvests * 6
wheat_total_units = wheat_tiles * wheat_harvests * 6

straw_rev = sell_batch("STRAWBERRY", straw_total)
melon_rev = sell_batch("MELON", melon_total)

print(f"  STRAWBERRY: {straw_tiles} tiles x {straw_harvests} harvests x 4 yield = {straw_total} units -> {straw_rev:,} coins")
print(f"  MELON: {melon_tiles} tiles x {melon_harvests} harvests x 6 yield = {melon_total} units -> {melon_rev:,} coins")

print("\n--- Top-Player Crop Targets (42 STRAWBERRY, 12 MELON, 7 WHEAT) ---")
straw_t2 = 42
melon_t2 = 12
straw_total2 = straw_t2 * straw_harvests * 4
melon_total2 = melon_t2 * melon_harvests * 6

straw_rev2 = sell_batch("STRAWBERRY", straw_total2)
melon_rev2 = sell_batch("MELON", melon_total2)

print(f"  STRAWBERRY: {straw_t2} tiles x {straw_harvests} harvests x 4 yield = {straw_total2} units -> {straw_rev2:,} coins")
print(f"  MELON: {melon_t2} tiles x {melon_harvests} harvests x 6 yield = {melon_total2} units -> {melon_rev2:,} coins")
print(f"  Crop subtotal (top-player): {straw_rev2 + melon_rev2:,}")

print("\n=== GRAND TOTAL ESTIMATES ===")
animal_total = milk_rev + wool_rev + fert_rev
our_crop_total = straw_rev + melon_rev
topplayer_crop_total = straw_rev2 + melon_rev2

# Start with 1500 coins, minus costs
opening_costs = 5*1 + 5*1 + 5*2 + 5*3 + 5*5  # 5 hires: 1+1+2+3+5 = 12, + 2 cows*400 + 2 sheep*500 + seeds
opening_costs = 12 + 800 + 1000 + 11*80 + 7*10  # hires + animals + melon seed + wheat seed
start_capital = 1500 - opening_costs

print(f"  Our crop layout (30 STR, 62 MEL): {our_crop_total + animal_total:>12,} coins")
print(f"  Top-player layout (42 STR, 12 MEL): {topplayer_crop_total + animal_total:>12,} coins")
print(f"  Best observed in training data: ~150,533 coins")
print()
print(f"  200k would require roughly {200000 / (our_crop_total + animal_total) * 100:.0f}% of our theoretical estimate.")
