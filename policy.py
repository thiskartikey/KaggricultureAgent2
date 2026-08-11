"""Kaggriculture — Pure Decision Transformer agent (v6).

The farmer, hands, and market are all driven by the Decision Transformer.
No heuristic task engine.  Fallback is PASS on every exception.

Action space (8 tokens):
  0  HARVEST  — harvest a ready crop or collect animal produce
  1  WATER    — water an unwatered plant
  2  PLANT MELON
  3  PLANT CARROT
  4  PLANT WHEAT
  5  FEED     — feed/service an animal
  6  DIG      — remove a weed
  7  PASS

Market orders are emitted by a lightweight rule set that does not depend on
the heuristic task engine.  See _market_orders().

To reference the old heuristic engine, read:
  archive/HEURISTIC_V5.md
  archive/heuristic_policy_v5.py
"""

import math
import os

# ── Market price model (mirrors kaggriculture.market_price) ───────────────────
_FUNCS = {
    "linear": lambda x: float(x),
    "sq":     lambda x: float(x) * float(x),
    "sqrt":   lambda x: math.sqrt(x),
    "log":    lambda x: math.log(1.0 + x),
    "log10":  lambda x: math.log10(1.0 + x),
}
MARKET_PARAMS = {
    "WHEAT":      (25,  10000, 400, "sqrt",   0.80, "log",    0.20),
    "CARROT":     (35,  10000, 450, "log",    0.20, "sqrt",   0.70),
    "TOMATO":     (60,  10000, 200, "linear", 0.40, "sqrt",   0.60),
    "STRAWBERRY": (120, 10000, 100, "sqrt",   0.70, "linear", 1.60),
    "MELON":      (250, 10000, 300, "log",    0.20, "sq",     3.60),
    "EGG":        (50,  10000, 332, "linear", 0.40, "log",    0.20),
    "MILK":       (160, 10000, 122, "sqrt",   0.60, "linear", 1.60),
    "WOOL":       (200, 10000, 105, "log",    0.20, "sq",     3.20),
    "FERTILIZER": (100, 10000, 200, "linear", 0.40, "linear", 0.40),
}
PRODUCTS = list(MARKET_PARAMS.keys())
SELL_PRODUCE = ["STRAWBERRY", "MELON", "MILK", "WOOL", "FERTILIZER",
                "WHEAT", "EGG", "CARROT", "TOMATO"]
PRODUCE_ITEMS = ("MELON", "STRAWBERRY", "MILK", "WOOL", "FERTILIZER",
                 "WHEAT", "EGG", "CARROT", "TOMATO")

ANIMAL_SPECS = {
    "GOOSE": dict(cost=300, product="EGG",  interval=1, first=4),
    "COW":   dict(cost=400, product="MILK", interval=2, first=8),
    "SHEEP": dict(cost=500, product="WOOL", interval=3, first=6),
}
CROP_SPECS = {
    "WHEAT":      dict(seed=10,  first=2,  interval=0, max_yield=6, ongoing=False),
    "CARROT":     dict(seed=20,  first=2,  interval=0, max_yield=4, ongoing=False),
    "STRAWBERRY": dict(seed=100, first=10, interval=2, max_yield=4, ongoing=True),
    "MELON":      dict(seed=80,  first=10, interval=0, max_yield=6, ongoing=False),
}

SHED_CAP    = 100
CASH_FLOOR  = 350
LAND_PRICES = [1000, 2000, 4000]
LAND_UNLOCK = (7, 11, 15)

TARGET_COW        = 8
TARGET_SHEEP      = 6
TARGET_STRAWBERRY = 42
TARGET_MELON      = 13
TARGET_WHEAT      = 8

TARGET_PASTURE_BY_DAY = (
    (14, 6),
    (10, 4),
    (0, 2),
)
TARGET_COOP_BY_DAY = (
    (0, 0),
)

def target_pastures(day):
    for day_from, count in TARGET_PASTURE_BY_DAY:
        if day >= day_from:
            return count
    return 6

def target_coops(day):
    for day_from, count in TARGET_COOP_BY_DAY:
        if day >= day_from:
            return count
    return 0

def _find_structures(me, kind):
    out = []
    for y, row in enumerate(me.get("tiles") or []):
        for x, t in enumerate(row):
            if isinstance(t, dict) and t.get("kind") == kind:
                out.append((x, y))
    return out

def shed_adjacent_cells(board, me=None):
    half = (board // 2) if isinstance(board, int) and board else 5
    unlocked = me.get("unlocked_quadrants") if me else ["NW"]
    cells = []
    # NW neighbor (always unlocked)
    cells.append((half - 1, half - 1))
    # SW neighbors
    if "SW" in unlocked:
        cells.append((half - 2, half))
        cells.append((half - 1, half + 1))
    # SE neighbor
    if "SE" in unlocked:
        cells.append((half, half))
    return cells


# ── Price helpers ─────────────────────────────────────────────────────────────
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


def sell_revenue(resource, inv, qty):
    rev = 0
    for _ in range(int(qty)):
        p = price(resource, inv)
        rev += p
        if p > 1:
            inv += 1
    return rev, inv


def buy_cost(resource, inv, qty):
    cost = 0
    for _ in range(int(qty)):
        inv -= 1
        cost += price(resource, inv)
    return cost, inv


def hire_cost(n_already_hired):
    a, b = 1, 1
    for _ in range(int(n_already_hired)):
        a, b = b, a + b
    return a


def should_buy_animal(animal, day, total_days, market_inv):
    spec = ANIMAL_SPECS[animal]
    left = total_days - day
    if left <= spec["first"]:
        return False
    harvests = max(0, (left - spec["first"]) // spec["interval"]) + 1
    revenue = harvests * price(spec["product"], int(market_inv.get(spec["product"], 0)))
    feed_cost = left * price("WHEAT", int(market_inv.get("WHEAT", 0)))
    return (revenue - spec["cost"] - feed_cost) > 0


def plant_expected_profit(crop, day, total_days, market_inv):
    spec = CROP_SPECS[crop]
    left = total_days - day
    if left <= spec["first"]:
        return -9999
    harvests = (max(0, (left - spec["first"]) // spec["interval"]) + 1
                if spec["ongoing"] and spec["interval"] > 0 else 1)
    return harvests * spec["max_yield"] * price(crop, int(market_inv.get(crop, 0))) - spec["seed"]


# ── Utility ───────────────────────────────────────────────────────────────────
def _nearest(pos, cells):
    if not cells:
        return None
    return min(cells, key=lambda c: abs(c[0] - pos[0]) + abs(c[1] - pos[1]))


def _step_toward(pos, target):
    x, y = pos
    tx, ty = target
    dx, dy = tx - x, ty - y
    if dx == 0 and dy == 0:
        return None
    if abs(dx) >= abs(dy):
        return "EAST" if dx > 0 else "WEST"
    return "SOUTH" if dy > 0 else "NORTH"


def _count_animals(me, private=None):
    count = 0
    for row in (me.get("tiles") or []):
        for t in row:
            if isinstance(t, dict) and t.get("kind") in ("PASTURE", "COOP") and t.get("animal"):
                count += 1
    if private:
        shed = private.get("shed") or {}
        for a in ("COW", "SHEEP", "GOOSE"):
            count += int(shed.get(a, 0))
    return count


def _animal_census(me, private=None):
    census = {"COW": 0, "SHEEP": 0, "GOOSE": 0}
    for row in (me.get("tiles") or []):
        for t in row:
            if isinstance(t, dict) and t.get("kind") in ("PASTURE", "COOP"):
                a = t.get("animal")
                if a in census:
                    census[a] += 1
    if private:
        shed = private.get("shed") or {}
        for a in census:
            census[a] += int(shed.get(a, 0))
    return census


def _crop_census(me):
    census = {}
    for row in (me.get("tiles") or []):
        for t in row:
            if isinstance(t, dict) and t.get("kind") == "PLANT":
                c = t.get("crop")
                if c:
                    census[c] = census.get(c, 0) + 1
    return census


def _target_hands(day, total_days):
    if day <= 0:  return 5
    if day < 7:   return 3
    if day < 11:  return 8
    if day >= total_days - 2: return 10
    return 13


# ── Market orders (lightweight, no heuristic task engine) ─────────────────────
def _market_orders(obs, player, total_days):
    """Return up to 10 market orders for this turn."""
    me      = obs["farms"][player]
    private = obs.get("private") or {}
    market  = obs.get("market") or {}
    minv    = market.get("inventory") or {}
    shed    = private.get("shed") or {}
    seeds   = private.get("seeds") or {}
    day     = int(obs.get("day", 0))
    hour    = int(obs.get("hour", 0))
    money   = float(me.get("money", 0))
    quads   = len(me.get("unlocked_quadrants") or ["NW"])
    hands   = len(me.get("hands") or [])
    hires   = int(me.get("hires_today", 0))
    tiles   = me.get("tiles") or []
    board   = len(tiles) or 10

    shed_total = sum(int(v) for v in shed.values())
    fed_animals = _count_animals(me, private)
    orders = []
    budget = money

    # ── Day 0 opening ─────────────────────────────────────────────────────────
    if day == 0 and hour == 0:
        return [
            ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"],
            ["BUY_ANIMAL", "COW", 2],
            ["BUY_ANIMAL", "SHEEP", 2],
            ["BUY_SEED", "MELON", 11],
            ["BUY_SEED", "WHEAT", 7],
            ["BUY_PRODUCT", "WHEAT", 8],
        ]

    # ── Sell produce ──────────────────────────────────────────────────────────
    hold_wheat = fed_animals * 3 if day < total_days - 1 else 0
    have_wheat = int(shed.get("WHEAT", 0))
    for inv_dict in (private.get("inventories") or []):
        have_wheat += int(inv_dict.get("WHEAT", 0))

    shed_total_prod = sum(int(v) for k, v in shed.items()
                         if k not in ("COW", "SHEEP", "GOOSE"))
    endgame = day >= total_days - 2
    for item in SELL_PRODUCE:
        if len(orders) >= 10:
            break
        qty = int(shed.get(item, 0))
        if item == "WHEAT":
            qty = max(0, qty - hold_wheat)
        if qty <= 0:
            continue
        sell_n = qty if endgame else min(qty, max(1, qty // 2 + 1))
        if sell_n > 0:
            orders.append(["SELL", item, sell_n])
            inv_mkt = int(minv.get(item, 0))
            rev, _ = sell_revenue(item, inv_mkt, sell_n)
            budget += rev

    # ── Seeds (survival priority) ──────────────────────────────────────────────
    planted = _crop_census(me)
    free_tiles = sum(
        1 for row in tiles for t in row
        if t is None
    )
    for crop, target in (("WHEAT", TARGET_WHEAT), ("STRAWBERRY", TARGET_STRAWBERRY), ("MELON", TARGET_MELON)):
        if len(orders) >= 10:
            break
        if plant_expected_profit(crop, day, total_days, minv) <= 0:
            continue
        deficit = max(0, target - planted.get(crop, 0) - int(seeds.get(crop, 0)))
        deficit = min(deficit, free_tiles + 5)
        if deficit <= 0:
            continue
        unit = CROP_SPECS[crop]["seed"]
        floor = 10 if crop == "WHEAT" else CASH_FLOOR
        can_afford = int((budget - floor) // unit)
        n = min(deficit, max(0, can_afford))
        if n > 0:
            orders.append(["BUY_SEED", crop, n])
            budget -= unit * n

    # ── Feed reserve ──────────────────────────────────────────────────────────
    if fed_animals > 0 and day < total_days - 1:
        need = fed_animals * 3 - have_wheat
        room = SHED_CAP - shed_total - 5
        need = min(need, max(0, room), 45)
        if need > 0 and len(orders) < 10:
            min_reserve = 20 if day < total_days - 1 else CASH_FLOOR
            avail_budget = max(0.0, budget - min_reserve)
            n_buy = 0
            curr_inv = int(minv.get("WHEAT", 0))
            for k in range(1, need + 1):
                c, _ = buy_cost("WHEAT", curr_inv, k)
                if c <= avail_budget:
                    n_buy = k
                else:
                    break
            if n_buy > 0:
                c, _ = buy_cost("WHEAT", curr_inv, n_buy)
                orders.append(["BUY_PRODUCT", "WHEAT", n_buy])
                budget -= c

    # ── Hire workers ──────────────────────────────────────────────────────────
    want = _target_hands(day, total_days)
    if budget < CASH_FLOOR:
        want = min(want, 2)
    n = 0
    while hands + n < want and len(orders) < 10:
        c = hire_cost(hires + n)
        if budget < c + 20:
            break
        orders.append(["HIRE"])
        budget -= c
        n += 1

    # ── Buy land ──────────────────────────────────────────────────────────────
    if quads - 1 < len(LAND_UNLOCK) and day >= LAND_UNLOCK[quads - 1]:
        cost = LAND_PRICES[quads - 1]
        if budget >= cost + CASH_FLOOR and len(orders) < 10:
            orders.append(["BUY_LAND"])
            budget -= cost

    # ── Buy animals ───────────────────────────────────────────────────────────
    census = _animal_census(me, private)
    empty_pastures = sum(
        1 for row in tiles for t in row
        if isinstance(t, dict) and t.get("kind") == "PASTURE" and not t.get("animal")
    )
    pending = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0)) + int(shed.get("GOOSE", 0))
    slots = empty_pastures - pending
    if slots > 0 and shed_total < SHED_CAP - 5 and len(orders) < 10:
        for animal, target in (("COW", TARGET_COW), ("SHEEP", TARGET_SHEEP)):
            if census[animal] >= target or slots <= 0:
                continue
            if not should_buy_animal(animal, day, total_days, minv):
                continue
            cost = ANIMAL_SPECS[animal]["cost"]
            want_n = min(target - census[animal], slots)
            afford = int((budget - CASH_FLOOR) // cost)
            want_n = min(want_n, max(0, afford))
            if want_n > 0:
                orders.append(["BUY_ANIMAL", animal, want_n])
                budget -= cost * want_n
                slots -= want_n
                break

    return orders[:10]


# ── Observation → vector ──────────────────────────────────────────────────────
OBS_DIM     = 107
CROPS       = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
ANIMALS     = ["GOOSE", "COW", "SHEEP"]
_PRODUCTS   = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
               "EGG", "MILK", "WOOL", "FERTILIZER"]
BASE_PRICES = [25, 35, 60, 120, 250, 50, 160, 200, 100]
SHOPS       = ["BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "YARN_STORE",
               "ICE_CREAM_SHOP", "PET_CAFE", "SMOOTHIE_SHOP", "FARMERS_MARKET"]


def _norm_shop(s):
    return str(s).strip().upper().replace(" ", "_").replace("-", "_")


def _farm_summary(tiles, day):
    import numpy as np
    cv = np.zeros(20, np.float32)
    av = np.zeros(9,  np.float32)
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            if not isinstance(t, dict):
                continue
            k = t.get("kind")
            if k == "PLANT":
                c = t.get("crop")
                if c in CROPS:
                    ci = CROPS.index(c)
                    cv[ci*4]   += 1
                    cv[ci*4+1] += int(not t.get("watered_today", False))
                    cv[ci*4+2] += int(t.get("yield_units", 0) > 0)
                    cv[ci*4+3] += max(0, day - t.get("planted_day", day)) / 30.0
            elif k in ("COOP", "PASTURE"):
                a = t.get("animal")
                if a in ANIMALS:
                    ai = ANIMALS.index(a)
                    av[ai*3]   += 1
                    av[ai*3+1] += int(not t.get("fed_today", False))
                    av[ai*3+2] += int(t.get("yield_units", 0) > 0)
    return cv, av


def obs_to_vec(obs, player):
    import numpy as np
    v   = np.zeros(OBS_DIM, np.float32)
    me  = obs["farms"][player]
    opp = obs["farms"][1 - player]
    day  = obs.get("day", 0)
    hour = obs.get("hour", 0)
    priv = obs.get("private", {}) or {}
    mkt  = obs.get("market", {}) or {}
    town = obs.get("town", {}) or {}

    i = 0
    v[i] = day / 30.0;                                        i += 1
    v[i] = hour / 24.0;                                       i += 1
    v[i] = min(me.get("money", 0) / 50000.0, 1.0);           i += 1
    v[i] = len(me.get("unlocked_quadrants", ["NW"])) / 4.0;  i += 1

    tiles = me.get("tiles") or []
    cv, av = _farm_summary(tiles, day)
    v[i:i+20] = cv / 10.0; i += 20
    v[i:i+9]  = av / 10.0; i += 9

    fx, fy = me.get("farmer", [4, 4])
    v[i] = fx / 10.0; v[i+1] = fy / 10.0; i += 2

    minv = mkt.get("inventory", {}) or {}
    mprc = mkt.get("prices", {}) or {}
    for j, p in enumerate(_PRODUCTS):
        v[i+j] = min(mprc.get(p, BASE_PRICES[j]) / (BASE_PRICES[j] * 2), 1.0)
    i += 9
    for j, p in enumerate(_PRODUCTS):
        v[i+j] = min(minv.get(p, 10000) / 10000.0, 1.0)
    i += 9

    shed = priv.get("shed", {}) or {}
    seeds = priv.get("seeds", {}) or {}
    for j, p in enumerate(_PRODUCTS):
        v[i+j] = min(shed.get(p, 0) / 20.0, 1.0)
    i += 9
    for j, a in enumerate(ANIMALS):
        v[i+j] = min(shed.get(a, 0) / 5.0, 1.0)
    i += 3
    for j, c in enumerate(CROPS):
        v[i+j] = min(seeds.get(c, 0) / 10.0, 1.0)
    i += 5

    shops_u = {_norm_shop(s) for s in (town.get("unlocked_shops") or [])}
    for j, s in enumerate(SHOPS):
        v[i+j] = float(s in shops_u)
    i += 8

    opp_tiles = opp.get("tiles") or []
    ocv, oav = _farm_summary(opp_tiles, day)
    v[i:i+20] = ocv / 10.0; i += 20
    v[i:i+9]  = oav / 10.0; i += 9

    return v


def _crop_harvestable(t, day, total_days):
    if not isinstance(t, dict) or t.get("kind") != "PLANT":
        return False
    crop = t.get("crop")
    if not crop:
        return False
    spec = CROP_SPECS.get(crop)
    if not spec:
        return False
    yield_units = int(t.get("yield_units", 0))
    if yield_units <= 0:
        return False
    if not spec.get("ongoing", False):
        age = day - int(t.get("planted_day", day))
        return age >= spec.get("first", 2) or (day >= total_days - 2)
    return True


# ── Farmer op resolution ──────────────────────────────────────────────────────
def macro_to_farmer_op(action_id, obs, player, seeds_override=None, pos_override=None, unit_idx=0, total_days=30):
    """Translate a DT action token into a concrete operation for any unit."""
    me    = obs["farms"][player]
    priv  = obs.get("private", {}) or {}
    seeds = seeds_override or priv.get("seeds", {}) or {}
    tiles = me.get("tiles") or []
    n     = len(tiles)
    pos   = tuple(pos_override) if pos_override is not None else tuple(me.get("farmer", [4, 4]))
    day   = obs.get("day", 0)
    hour  = obs.get("hour", 0)

    harv, water, empty, weeds, feed = [], [], [], [], []
    empty_structures = []
    have_pastures = 0
    have_coops = 0
    for y in range(n):
        for x in range(n):
            t = tiles[y][x]
            if t == "LOCKED":
                continue
            if t is None:
                empty.append((x, y))
                continue
            if not isinstance(t, dict):
                continue
            k = t.get("kind")
            if k == "PLANT":
                if _crop_harvestable(t, day, total_days):
                    harv.append((x, y, "HARVEST"))
                if not t.get("watered_today", False):
                    water.append((x, y))
            elif k == "WEED":
                weeds.append((x, y))
            elif k in ("COOP", "PASTURE"):
                if k == "PASTURE":
                    have_pastures += 1
                else:
                    have_coops += 1
                if t.get("animal"):
                    if not t.get("fed_today", False):
                        feed.append((x, y))
                    if t.get("yield_units", 0) > 0:
                        harv.append((x, y, "HARVEST"))
                    if t.get("fertilizer_available", False):
                        harv.append((x, y, "COLLECT_FERTILIZER"))
                else:
                    empty_structures.append((x, y, k))

    def _go(cells, act=None):
        if cells and len(cells[0]) == 3:
            t = _nearest(pos, [(c[0], c[1]) for c in cells])
            if t is None:
                return ["PASS"]
            tgt_act = next(c[2] for c in cells if (c[0], c[1]) == t)
            if tuple(pos) == tuple(t):
                return [tgt_act]
            st = _step_toward(pos, t)
            return [st] if st else [tgt_act]
        else:
            t = _nearest(pos, cells)
            if t is None:
                return ["PASS"]
            if tuple(pos) == tuple(t):
                return [act]
            st = _step_toward(pos, t)
            return [st] if st else [act]

    # Calculate unplaced animals
    shed = priv.get("shed") or {}
    invs = priv.get("inventories") or []
    unit_inv = invs[unit_idx] if unit_idx < len(invs) else {}
    
    unplaced = {}
    for a in ("COW", "SHEEP", "GOOSE"):
        n_unplaced = int(shed.get(a, 0)) + sum(int(i.get(a, 0)) for i in invs)
        if n_unplaced > 0:
            unplaced[a] = n_unplaced

    carrying_animal = None
    for a in ("COW", "SHEEP", "GOOSE"):
        if int(unit_inv.get(a, 0)) > 0:
            carrying_animal = a
            break

    crop_map = {2: "MELON", 3: "CARROT", 4: "WHEAT"}
    carry_qty = sum(int(unit_inv.get(item, 0)) for item in PRODUCE_ITEMS)
    
    # --- Pre-empt DT with urgent survival tasks ---
    # 1. Feed hungry animals (prevent escape)
    if feed:
        t = _nearest(pos, feed)
        if t: return ["__FEED__", t]
        
    # Helper hands drop off immediately if they carry any products (since they vanish at midnight)
    if unit_idx > 0 and carry_qty > 0:
        return ["__DROPOFF__"]

    # Drop off to shed if backpack is getting full, at end of day, or if passing adjacent to the shed
    shed_adjacent = [(4, 4), (3, 5), (4, 6), (5, 5)]
    if carry_qty >= 4 or (carry_qty > 0 and hour >= 21) or (carry_qty > 0 and tuple(pos) in shed_adjacent):
        return ["__DROPOFF__"]

    # 2. Harvest matured crops & products (cash flow)
    if harv:
        return _go(harv, "HARVEST")

    if action_id == 0:
        return _go(harv, "HARVEST")
    if action_id == 1:
        return _go(water, "WATER")
    if action_id in (2, 3, 4):
        crop = crop_map[action_id]
        if seeds.get(crop, 0) > 0 and day <= 26:
            return _go(empty, f"__PLANT__{crop}")
    if action_id == 5:
        t = _nearest(pos, feed)
        if t: return ["__FEED__", t]
    if action_id == 6:
        if weeds:
            return _go(weeds, "DIG")
        
    # action_id == 7 (PASS): fallback to urgent tasks, placement, building
    # 1. Place animal if carrying
    if carrying_animal:
        req_kind = "PASTURE" if carrying_animal in ("COW", "SHEEP") else "COOP"
        matching_empty = [(sx, sy) for sx, sy, sk in empty_structures if sk == req_kind]
        if matching_empty:
            tgt_cell = _nearest(pos, matching_empty)
            return ["__PLACE__", carrying_animal, tgt_cell]
            
    # 2. Feed hungry animals (emergency)
    if feed:
        t = _nearest(pos, feed)
        if t: return ["__FEED__", t]
    
    # 3. Place animals if not carrying but unplaced exist
    if unplaced:
        for a in ("COW", "SHEEP", "GOOSE"):
            if unplaced.get(a, 0) <= 0:
                continue
            req_kind = "PASTURE" if a in ("COW", "SHEEP") else "COOP"
            matching_empty = [(sx, sy) for sx, sy, sk in empty_structures if sk == req_kind]
            if matching_empty:
                tgt_cell = _nearest(pos, matching_empty)
                return ["__PLACE__", a, tgt_cell]
                
    # 4. Build pastures/coops if deficit exists
    deficit_pasture = target_pastures(day) - have_pastures
    deficit_coop = target_coops(day) - have_coops
    if day < total_days - 8:
        if deficit_pasture > 0 and empty:
            tgt_cell = _nearest(pos, empty)
            return ["__BUILD__", "PASTURE", tgt_cell]
        if deficit_coop > 0 and empty:
            tgt_cell = _nearest(pos, empty)
            return ["__BUILD__", "COOP", tgt_cell]
            
    # 5. Harvest, Water, Dig, Plant as normal fallbacks
    if harv:    return _go(harv,  "HARVEST")
    if water:   return _go(water, "WATER")
    if weeds:   return _go(weeds, "DIG")
    # Try to plant with whatever seeds are available (high-value crops prioritized)
    for crop in ("STRAWBERRY", "MELON", "CARROT", "WHEAT"):
        if seeds.get(crop, 0) > 0 and empty and day <= 26:
            return _go(empty, f"__PLANT__{crop}")
            
    if carry_qty > 0:
        return ["__DROPOFF__"]
    return ["PASS"]


def resolve_farmer_op(raw_op, obs, player, unit_idx=0):
    """Resolve pseudo-ops into actual commands."""
    if not raw_op or raw_op[0] == "PASS":
        return ["PASS"]
    op = raw_op[0]
    
    me = obs["farms"][player]
    positions = [tuple(me.get("farmer") or (4, 4))] + [tuple(h) for h in (me.get("hands") or [])]
    pos = positions[unit_idx] if unit_idx < len(positions) else tuple(me.get("farmer", [4, 4]))

    if op.startswith("__PLANT__"):
        crop = op[9:]
        tiles = me.get("tiles") or []
        x, y  = pos
        t = (tiles[y][x]
             if 0 <= y < len(tiles) and 0 <= x < len(tiles[y])
             else "LOCKED")
        if t is None:
            return ["PLANT", crop]
        empty = [(rx, ry)
                 for ry in range(len(tiles))
                 for rx in range(len(tiles[ry]))
                 if tiles[ry][rx] is None]
        tgt = _nearest(pos, empty)
        if tgt is None:
            return ["PASS"]
        if tuple(pos) == tgt:
            return ["PLANT", crop]
        st = _step_toward(pos, tgt)
        return [st] if st else ["PASS"]
        
    if op == "__PLACE__":
        animal = raw_op[1]
        target_cell = raw_op[2]
        priv = obs.get("private") or {}
        invs = priv.get("inventories") or []
        unit_inv = invs[unit_idx] if unit_idx < len(invs) else {}
        shed = priv.get("shed") or {}
        board = len(me.get("tiles") or []) or 10
        sheds = shed_adjacent_cells(board, me)
            
        if int(unit_inv.get(animal, 0)) > 0:
            if pos == tuple(target_cell):
                return ["PLACE", animal]
            st = _step_toward(pos, target_cell)
            return [st] if st else ["PLACE", animal]
        else:
            store = int(shed.get(animal, 0))
            if store <= 0:
                return ["PASS"]
            nearest_shed = min(sheds, key=lambda c: abs(c[0]-pos[0])+abs(c[1]-pos[1]))
            if pos == tuple(nearest_shed):
                return ["PICKUP", animal, 1]
            st = _step_toward(pos, nearest_shed)
            return [st] if st else ["PICKUP", animal, 1]
            
    if op == "__BUILD__":
        structure = raw_op[1]
        target_cell = raw_op[2]
        if pos == tuple(target_cell):
            return [f"BUILD_{structure}"]
        st = _step_toward(pos, target_cell)
        return [st] if st else [f"BUILD_{structure}"]

    if op == "__FEED__":
        target_cell = raw_op[1]
        priv = obs.get("private") or {}
        invs = priv.get("inventories") or []
        unit_inv = invs[unit_idx] if unit_idx < len(invs) else {}
        shed = priv.get("shed") or {}
        board = len(me.get("tiles") or []) or 10
        sheds = shed_adjacent_cells(board, me)
            
        if int(unit_inv.get("WHEAT", 0)) > 0:
            if pos == tuple(target_cell):
                return ["FEED"]
            st = _step_toward(pos, target_cell)
            return [st] if st else ["FEED"]
        else:
            store = int(shed.get("WHEAT", 0))
            if store <= 0:
                return ["PASS"]
            nearest_shed = min(sheds, key=lambda c: abs(c[0]-pos[0])+abs(c[1]-pos[1]))
            if pos == tuple(nearest_shed):
                return ["PICKUP", "WHEAT", min(store, 4)]
            st = _step_toward(pos, nearest_shed)
            return [st] if st else ["PICKUP", "WHEAT", min(store, 4)]

    if op == "__DROPOFF__":
        board = len(me.get("tiles") or []) or 10
        sheds = shed_adjacent_cells(board, me)
        nearest_shed = min(sheds, key=lambda c: abs(c[0]-pos[0])+abs(c[1]-pos[1]))
        if pos == tuple(nearest_shed):
            return ["DROP"]
        st = _step_toward(pos, nearest_shed)
        return [st] if st else ["DROP"]
        
    return raw_op


# ── Hands: simple rule-based fill ────────────────────────────────────────────
def _hand_op(pos, obs, player, priv, action_id):
    """Give each hand the same macro action as the farmer (crude but coherent)."""
    return resolve_farmer_op(macro_to_farmer_op(action_id, obs, player), obs, player)


# ── Decision Transformer Inference (NumPy-only) ───────────────────────────────
class DecisionTransformer:
    def __init__(self, weights_path):
        self.loaded = False
        try:
            import numpy as np
            if os.path.exists(weights_path):
                self._w = dict(np.load(weights_path, allow_pickle=False))
                self.loaded = True
        except Exception:
            pass

    def _linear(self, x, wk, bk=None):
        out = x @ self._w[wk].T
        if bk and bk in self._w:
            out += self._w[bk]
        return out

    def _layer_norm(self, x, wk, bk, eps=1e-5):
        mean = x.mean(axis=-1, keepdims=True)
        var  = x.var(axis=-1,  keepdims=True)
        return self._w[wk] * (x - mean) / (var + eps) ** 0.5 + self._w[bk]

    def _self_attention(self, x, li, num_heads=4):
        import numpy as np
        seq_len, embed_dim = x.shape
        head_dim = embed_dim // num_heads
        c_attn = self._linear(x, f"blocks.{li}.attn.c_attn.weight",
                                  f"blocks.{li}.attn.c_attn.bias")
        q, k, v = np.split(c_attn, 3, axis=-1)
        q = q.reshape(seq_len, num_heads, head_dim).transpose(1, 0, 2)
        k = k.reshape(seq_len, num_heads, head_dim).transpose(1, 0, 2)
        v = v.reshape(seq_len, num_heads, head_dim).transpose(1, 0, 2)
        mask   = np.tril(np.ones((seq_len, seq_len))).reshape(1, seq_len, seq_len)
        scores = q @ k.transpose(0, 2, 1) / head_dim ** 0.5
        scores = np.where(mask == 1, scores, -1e4)
        scores = scores - scores.max(axis=-1, keepdims=True)
        probs  = np.exp(scores) / np.exp(scores).sum(axis=-1, keepdims=True)
        out    = (probs @ v).transpose(1, 0, 2).reshape(seq_len, embed_dim)
        return self._linear(out, f"blocks.{li}.attn.c_proj.weight",
                                  f"blocks.{li}.attn.c_proj.bias")

    def predict(self, states, actions, returns_to_go, timesteps):
        if not self.loaded:
            return 7
        import numpy as np
        s_emb = self._linear(states,      "embed_state.weight",  "embed_state.bias")
        a_emb = self._linear(actions,     "embed_action.weight", "embed_action.bias")
        r_emb = self._linear(returns_to_go, "embed_return.weight", "embed_return.bias")
        K         = states.shape[0]
        embed_dim = s_emb.shape[-1]
        seq = np.zeros((K * 3, embed_dim), dtype=np.float32)
        seq[0::3] = r_emb
        seq[1::3] = s_emb
        seq[2::3] = a_emb
        pos_emb = self._w["embed_timestep.weight"][timesteps]
        x = seq + np.repeat(pos_emb, 3, axis=0)
        x = self._layer_norm(x, "embed_ln.weight", "embed_ln.bias")
        num_layers = sum(1 for k in self._w if k.endswith(".attn.c_attn.weight"))
        for li in range(num_layers):
            h = self._layer_norm(x, f"blocks.{li}.ln_1.weight", f"blocks.{li}.ln_1.bias")
            x = x + self._self_attention(h, li)
            h = self._layer_norm(x, f"blocks.{li}.ln_2.weight", f"blocks.{li}.ln_2.bias")
            mlp_h = self._linear(h, f"blocks.{li}.mlp.c_fc.weight",
                                     f"blocks.{li}.mlp.c_fc.bias")
            mlp_h = mlp_h * (mlp_h > 0)
            x = x + self._linear(mlp_h, f"blocks.{li}.mlp.c_proj.weight",
                                          f"blocks.{li}.mlp.c_proj.bias")
        x = self._layer_norm(x, "ln_f.weight", "ln_f.bias")
        logits = self._linear(x[1::3][-1:], "predict_action.weight", "predict_action.bias")
        return int(logits[0].argmax())


# ── Episode-level state ───────────────────────────────────────────────────────
DT_MODEL        = None
STATE_HISTORY   = []
ACTION_HISTORY  = []
RETURN_HISTORY  = []
TIMESTEP_HISTORY = []


def _agent(obs, total_days=30):
    import numpy as np
    global DT_MODEL, STATE_HISTORY, ACTION_HISTORY, RETURN_HISTORY, TIMESTEP_HISTORY

    player  = obs["player"]
    me      = obs["farms"][player]
    private = obs.get("private") or {}
    day     = int(obs.get("day", 0))
    hour    = int(obs.get("hour", 0))

    # Reset at episode start
    if day == 0 and hour == 0:
        STATE_HISTORY    = []
        ACTION_HISTORY   = []
        RETURN_HISTORY   = []
        TIMESTEP_HISTORY = []

    # Load weights once
    weights_file = "rl_weights.npz"
    if DT_MODEL is None and os.path.exists(weights_file):
        try:
            DT_MODEL = DecisionTransformer(weights_file)
        except Exception:
            pass

    # Default action
    action_id = 7  # PASS

    if DT_MODEL is not None and DT_MODEL.loaded:
        try:
            s_t    = obs_to_vec(obs, player)
            money  = float(me.get("money", 0.0))
            r_t    = max(0.0, 200000.0 - money)

            STATE_HISTORY.append(s_t)
            RETURN_HISTORY.append([r_t])
            TIMESTEP_HISTORY.append(day * 24 + hour)

            # Pad action history
            if len(ACTION_HISTORY) < len(STATE_HISTORY):
                dummy = np.zeros(8, dtype=np.float32)
                dummy[7] = 1.0
                ACTION_HISTORY.append(dummy)

            K = 20
            states_k    = np.array(STATE_HISTORY[-K:],    dtype=np.float32)
            actions_k   = np.array(ACTION_HISTORY[-K:],   dtype=np.float32)
            returns_k   = np.array(RETURN_HISTORY[-K:],   dtype=np.float32)
            timesteps_k = np.array(TIMESTEP_HISTORY[-K:], dtype=np.int64)

            action_id = DT_MODEL.predict(states_k, actions_k, returns_k, timesteps_k)

            chosen = np.zeros(8, dtype=np.float32)
            chosen[action_id] = 1.0
            ACTION_HISTORY[-1] = chosen

            # Append dummy for next step
            dummy = np.zeros(8, dtype=np.float32)
            dummy[7] = 1.0
            ACTION_HISTORY.append(dummy)
        except Exception:
            pass

    # Build farmer and hands operations independently to maximize efficiency
    tiles = me.get("tiles") or []
    feed_q = []
    harv_q = []
    water_q = []
    weeds_q = []
    empty_q = []
    empty_structs = []
    have_pastures = 0
    have_coops = 0
    
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            if t is None:
                empty_q.append((x, y))
                continue
            if not isinstance(t, dict):
                continue
            k = t.get("kind")
            if k == "PLANT":
                if _crop_harvestable(t, day, total_days):
                    harv_q.append((x, y, "HARVEST"))
                if not t.get("watered_today", False):
                    water_q.append((x, y))
            elif k == "WEED":
                weeds_q.append((x, y))
            elif k in ("COOP", "PASTURE"):
                if k == "PASTURE":
                    have_pastures += 1
                else:
                    have_coops += 1
                if t.get("animal"):
                    if not t.get("fed_today", False):
                        feed_q.append((x, y))
                    if t.get("yield_units", 0) > 0:
                        harv_q.append((x, y, "HARVEST"))
                    if t.get("fertilizer_available", False):
                        harv_q.append((x, y, "COLLECT_FERTILIZER"))
                else:
                    empty_structs.append((x, y, k))

    def _go_local(pos, cells, act=None):
        if cells and len(cells[0]) == 3:
            t = _nearest(pos, [(c[0], c[1]) for c in cells])
            if t is None:
                return ["PASS"]
            tgt_act = next(c[2] for c in cells if (c[0], c[1]) == t)
            if tuple(pos) == tuple(t):
                return [tgt_act]
            st = _step_toward(pos, t)
            return [st] if st else [tgt_act]
        else:
            t = _nearest(pos, cells)
            if t is None:
                return ["PASS"]
            if tuple(pos) == tuple(t):
                return [act]
            st = _step_toward(pos, t)
            return [st] if st else [act]

    def get_unit_action(pos, unit_idx, force_action_id=None):
        invs = private.get("inventories") or []
        unit_inv = invs[unit_idx] if unit_idx < len(invs) else {}
        shed = private.get("shed") or {}
        carrying_animal = next((a for a in ("COW", "SHEEP", "GOOSE") if int(unit_inv.get(a, 0)) > 0), None)
        unplaced = {}
        for a in ("COW", "SHEEP", "GOOSE"):
            qty = int(shed.get(a, 0))
            if qty > 0:
                unplaced[a] = qty
                
        carry_qty = sum(int(unit_inv.get(item, 0)) for item in PRODUCE_ITEMS)
        
        if carrying_animal:
            req_kind = "PASTURE" if carrying_animal in ("COW", "SHEEP") else "COOP"
            matching = [t for t in empty_structs if t[2] == req_kind]
            if matching:
                tgt = _nearest(pos, [(m[0], m[1]) for m in matching])
                for m in matching:
                    if (m[0], m[1]) == tgt:
                        empty_structs.remove(m)
                        break
                return ["__PLACE__", carrying_animal, tgt]
                
        if feed_q:
            t = _nearest(pos, feed_q)
            if t:
                feed_q.remove(t)
                return ["__FEED__", t]

        if force_action_id is not None and force_action_id != 7:
            if force_action_id == 0 and harv_q:
                t = _nearest(pos, [(c[0], c[1]) for c in harv_q])
                if t:
                    tgt_item = next(c for c in harv_q if (c[0], c[1]) == t)
                    harv_q.remove(tgt_item)
                    return _go_local(pos, [tgt_item])
            elif force_action_id == 1 and water_q:
                t = _nearest(pos, water_q)
                if t:
                    water_q.remove(t)
                    return _go_local(pos, [t], "WATER")
            elif force_action_id in (2, 3, 4) and empty_q:
                crop_map = {2: "MELON", 3: "CARROT", 4: "WHEAT"}
                crop = crop_map[force_action_id]
                seeds = private.get("seeds") or {}
                if seeds.get(crop, 0) > 0 and day <= 26:
                    t = _nearest(pos, empty_q)
                    if t:
                        empty_q.remove(t)
                        return ["__PLANT__" + crop, t]
            elif force_action_id == 5 and feed_q:
                t = _nearest(pos, feed_q)
                if t:
                    feed_q.remove(t)
                    return ["__FEED__", t]
            elif force_action_id == 6 and weeds_q:
                t = _nearest(pos, weeds_q)
                if t:
                    weeds_q.remove(t)
                    return _go_local(pos, [t], "DIG")
                    
        if unplaced:
            for a in ("COW", "SHEEP", "GOOSE"):
                if unplaced.get(a, 0) <= 0:
                    continue
                req_kind = "PASTURE" if a in ("COW", "SHEEP") else "COOP"
                matching = [t for t in empty_structs if t[2] == req_kind]
                if matching:
                    tgt = _nearest(pos, [(m[0], m[1]) for m in matching])
                    for m in matching:
                        if (m[0], m[1]) == tgt:
                            empty_structs.remove(m)
                            break
                    return ["__PLACE__", a, tgt]

        deficit_pasture = target_pastures(day) - have_pastures
        deficit_coop = target_coops(day) - have_coops
        if day < total_days - 8:
            if deficit_pasture > 0 and empty_q:
                tgt = _nearest(pos, empty_q)
                empty_q.remove(tgt)
                return ["__BUILD__", "PASTURE", tgt]
            if deficit_coop > 0 and empty_q:
                tgt = _nearest(pos, empty_q)
                empty_q.remove(tgt)
                return ["__BUILD__", "COOP", tgt]

        if harv_q:
            t = _nearest(pos, [(c[0], c[1]) for c in harv_q])
            if t:
                tgt_item = next(c for c in harv_q if (c[0], c[1]) == t)
                harv_q.remove(tgt_item)
                return _go_local(pos, [tgt_item])
        if water_q:
            t = _nearest(pos, water_q)
            if t:
                water_q.remove(t)
                return _go_local(pos, [t], "WATER")
        if weeds_q:
            t = _nearest(pos, weeds_q)
            if t:
                weeds_q.remove(t)
                return _go_local(pos, [t], "DIG")
                
        seeds = private.get("seeds") or {}
        for crop in ("STRAWBERRY", "MELON", "CARROT", "WHEAT"):
            if seeds.get(crop, 0) > 0 and empty_q and day <= 26:
                t = _nearest(pos, empty_q)
                if t:
                    empty_q.remove(t)
                    return ["__PLANT__" + crop, t]

        # 6. Dropoff if carrying anything (only if full or no tasks remain)
        if carry_qty > 0:
            if carry_qty >= 8 or not (feed_q or harv_q or water_q or weeds_q):
                return ["__DROPOFF__"]
            
        return ["PASS"]

    farmer_pos = tuple(me.get("farmer") or (4, 4))
    farmer_raw = get_unit_action(farmer_pos, 0, force_action_id=action_id)
    farmer_op = resolve_farmer_op(farmer_raw, obs, player, unit_idx=0)
    
    hand_positions = me.get("hands") or []
    hands_ops = []
    for idx, hand_pos in enumerate(hand_positions):
        hpos = tuple(hand_pos)
        h_raw = get_unit_action(hpos, 1 + idx, force_action_id=None)
        hands_ops.append(resolve_farmer_op(h_raw, obs, player, unit_idx=1 + idx))

    # Market orders
    orders = _market_orders(obs, player, total_days)

    return {"farmer": farmer_op, "hands": hands_ops, "market": orders}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _to_dict(obj):
    try:
        import json
        return json.loads(json.dumps(obj))
    except Exception:
        return obj


def _total_days(config):
    try:
        steps = int(config["episodeSteps"] if isinstance(config, dict)
                    else getattr(config, "episodeSteps"))
        per   = int(config["turnsPerDay"] if isinstance(config, dict)
                    else getattr(config, "turnsPerDay"))
        if steps > 0 and per > 0:
            return max(1, steps // per)
    except Exception:
        pass
    return 30


# ── Entrypoint ────────────────────────────────────────────────────────────────
def agent(obs, config=None):
    try:
        return _agent(_to_dict(obs), _total_days(config))
    except Exception:
        import traceback, sys
        traceback.print_exc(file=sys.stderr)
        return {"farmer": ["PASS"], "hands": [], "market": []}
