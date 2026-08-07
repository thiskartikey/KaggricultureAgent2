"""Kaggriculture heuristic agent -- TOP PLAYER STRATEGY (v4).

Strategy reverse-engineered from top leaderboard replays (120k-158k scores):
  Day 0:   Day 0 Hour 1 Opening Playbook: 5 HIRE + 2 COW + 2 SHEEP + 7 WHEAT seed + 12 MELON seed + 5 WHEAT product.
  Day 1-6: Water crops, feed/care animals, collect fertilizer, harvest crops & animal products. Maintain 5 hands.
  Day 7+:  Expand Land Quadrant 2 (at >=1000 coins), scale active hands to 7. Build PASTUREs, buy SHEEP/COWs.
  Day 11+: Expand Land Quadrants 3 & 4 (at >=2000 coins), scale active hands to 11-14 hands.
  Zero Policy: Zero COOP, GOOSE, EGG, CARROT, TOMATO. Focus strictly on PASTURE (COW, SHEEP), WHEAT, MELON, STRAWBERRY.
  Drop Policy: Reduced backpack drop threshold to 5 items (or drop when carrying produce near shed).
"""
import math

# ── Market price model ────────────────────────────────────────────────────────
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
SELLABLE = PRODUCTS
SELL_PRODUCE = ["WHEAT", "STRAWBERRY", "MELON", "MILK", "WOOL", "FERTILIZER"]
PRODUCE_ITEMS = ("MELON", "STRAWBERRY", "MILK", "WOOL", "FERTILIZER")


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


def marginal_revenue(resource, inv, qty):
    if qty <= 1:
        return price(resource, inv)
    _, inv2 = sell_revenue(resource, inv, qty - 1)
    return price(resource, inv2)


def buy_cost(resource, inv, qty):
    cost = 0
    for _ in range(int(qty)):
        inv -= 1
        cost += price(resource, inv)
    return cost, inv


def units_sellable_above(resource, inv, reserve):
    if reserve <= 1:
        return 10 ** 6
    n = 0
    while n < 2000:
        p = price(resource, inv)
        if p < reserve:
            break
        n += 1
        if p > 1:
            inv += 1
    return n


_RESERVE_FRAC = {
    "WHEAT": 0.72, "CARROT": 0.70, "TOMATO": 0.70, "EGG": 0.72,
    "MILK": 0.72, "WOOL": 0.72, "STRAWBERRY": 0.72, "MELON": 0.72,
    "FERTILIZER": 0.72,
}

# ── Specs ─────────────────────────────────────────────────────────────────────
CROP_SPECS = {
    "WHEAT":      dict(seed=10,  first=1,  maxday=2,  peak=2, occ=1),
    "CARROT":     dict(seed=20,  first=2,  maxday=3,  peak=4, occ=2),
    "TOMATO":     dict(seed=50,  first=8,  maxday=8,  peak=4, occ=8),
    "STRAWBERRY": dict(seed=100, first=10, maxday=10, peak=4, occ=10),
    "MELON":      dict(seed=80,  first=10, maxday=12, peak=6, occ=10),
}
ANIMAL_SPECS = {
    "GOOSE": dict(cost=300,  build="BUILD_COOP",    structure="COOP",    product="EGG",  interval=1, first=4),
    "COW":   dict(cost=400,  build="BUILD_PASTURE", structure="PASTURE", product="MILK", interval=2, first=8),
    "SHEEP": dict(cost=500,  build="BUILD_PASTURE", structure="PASTURE", product="WOOL", interval=3, first=6),
}
ANIMAL_ITEMS = ("GOOSE", "COW", "SHEEP")
CROPS = list(CROP_SPECS.keys())


# ── Market helpers ─────────────────────────────────────────────────────────────
def plan_sells(shed, market_inv, day, hour, total_days, hold=None):
    """Decide what to sell this turn."""
    orders = []
    hold = hold or {}
    for product in SELL_PRODUCE:
        qty = int(shed.get(product, 0))
        reserve = hold.get(product, 0)
        qty = max(0, qty - reserve)
        if qty <= 0:
            continue
        inv = int(market_inv.get(product, MARKET_PARAMS[product][1]))
        reserve_price = _RESERVE_FRAC.get(product, 0.70) * MARKET_PARAMS[product][0]
        sell_n = min(qty, units_sellable_above(product, inv, reserve_price))
        # Late game: sell everything
        if day >= total_days - 3:
            sell_n = qty
        if sell_n > 0:
            orders.append(["SELL", product, sell_n])
    return orders


def feed_hold(animal_count, shed_wheat, days_buffer=2):
    return min(shed_wheat, animal_count * days_buffer)


# ── Farm scan ─────────────────────────────────────────────────────────────────
def _scan(me, day):
    out = dict(water=[], feed=[], harvest_crop=[], harvest_animal=[],
               collect=[], weeds=[], structures_empty=[], care=[],
               collect_fertilizer=[])
    tiles = me.get("tiles") or []
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            if not isinstance(t, dict):
                continue
            kind = t.get("kind")
            if kind == "PLANT":
                if not t.get("watered_today"):
                    out["water"].append((x, y))
                if t.get("yield_units", 0) > 0:
                    out["harvest_crop"].append((x, y))
            elif kind == "PASTURE":  # Zero-COOP Policy: focus on PASTURE
                if t.get("animal"):
                    if not t.get("fed_today"):
                        out["feed"].append((x, y))
                    if t.get("fertilizer_available"):
                        out["collect_fertilizer"].append((x, y))
                    out["care"].append((x, y))
                    if t.get("yield_units", 0) > 0:
                        out["harvest_animal"].append((x, y))
                else:
                    out["structures_empty"].append(((x, y), kind))
            elif kind == "WEED":
                out["weeds"].append((x, y))
    return out


def _free_cells(me, board):
    tiles = me.get("tiles") or []
    free = []
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            if t is None:
                free.append((x, y))
    return free


def _count_animals(me, private=None):
    n = 0
    tiles = me.get("tiles") or []
    for row in tiles:
        for t in row:
            if isinstance(t, dict) and t.get("kind") in ("COOP", "PASTURE") and t.get("animal"):
                n += 1
    if private:
        shed = private.get("shed") or {}
        n += int(shed.get("COW", 0))
        n += int(shed.get("SHEEP", 0))
        for inv in (private.get("inventories") or []):
            n += int(inv.get("COW", 0))
            n += int(inv.get("SHEEP", 0))
    return n


def _count_structures(me, kind):
    n = 0
    tiles = me.get("tiles") or []
    for row in tiles:
        for t in row:
            if isinstance(t, dict) and t.get("kind") == kind:
                n += 1
    return n


def _count_planted(me):
    n = 0
    tiles = me.get("tiles") or []
    for row in tiles:
        for t in row:
            if isinstance(t, dict) and t.get("kind") == "PLANT":
                n += 1
    return n


def _land_cost(me):
    n = len(me.get("unlocked_quadrants", ["NW"])) - 1
    costs = [1000, 2000, 3000]
    return costs[n] if n < len(costs) else 999999


# ── Movement helpers ──────────────────────────────────────────────────────────
def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def step_toward(pos, target):
    x, y = pos
    tx, ty = target
    dx, dy = tx - x, ty - y
    if dx == 0 and dy == 0:
        return None
    if abs(dx) >= abs(dy):
        return "EAST" if dx > 0 else "WEST"
    return "SOUTH" if dy > 0 else "NORTH"


def _nearest(pos, cells):
    if not cells:
        return None
    return min(cells, key=lambda c: manhattan(pos, c))


def shed_adjacent_cells(board, me):
    half = board // 2 if isinstance(board, int) else 5
    return [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]
    # Returns [(4, 4), (5, 4), (4, 5), (5, 5)] for board size 10


def hire_cost(n_already_hired):
    fib = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
    return fib[min(n_already_hired, len(fib) - 1)]


# ── Task assignment ──────────────────────────────────────────────────────────
TASK_PRIORITY = {
    "feed": 10.0,
    "water": 9.3,
    "harvest_crop": 9.0,
    "harvest_animal": 8.5,
    "care": 8.0,
    "collect_fertilizer": 7.5,
    "build_pasture": 6.0,
    "place_animal": 5.0,
    "plant": 4.0,
    "weed": 1.0,
}


def _unit_op(pos, task, private, unit_idx, board, me, shed_wheat):
    """Convert a task assignment to an actual operation."""
    invs = private.get("inventories") or []
    inv = invs[unit_idx] if unit_idx < len(invs) else {}
    kind = task[0]
    target = task[1] if len(task) > 1 else None
    pos = tuple(pos)
    sheds = shed_adjacent_cells(board, me)
    shed_positions = [tuple(c) for c in sheds]

    if kind == "feed":
        cell = target
        if int(inv.get("WHEAT", 0)) <= 0:
            s_wheat = int((private.get("shed") or {}).get("WHEAT", 0))
            if s_wheat <= 0:
                return ["PASS"]
            if pos in shed_positions:
                return ["PICKUP", "WHEAT", min(s_wheat, 3)]
            else:
                tgt = min(sheds, key=lambda c: manhattan(pos, c))
                st = step_toward(pos, tgt)
                return [st] if st else ["PICKUP", "WHEAT", min(s_wheat, 3)]
        if pos == tuple(cell):
            return ["FEED"]
        st = step_toward(pos, cell)
        return [st] if st else ["FEED"]

    elif kind == "place_animal":
        animal, cell = target
        if int(inv.get(animal, 0)) <= 0:
            s_count = int((private.get("shed") or {}).get(animal, 0))
            if s_count <= 0:
                return ["PASS"]
            if pos in shed_positions:
                return ["PICKUP", animal, 1]
            else:
                tgt = min(sheds, key=lambda c: manhattan(pos, c))
                st = step_toward(pos, tgt)
                return [st] if st else ["PICKUP", animal, 1]
        if pos == tuple(cell):
            return ["PLACE", animal]
        st = step_toward(pos, cell)
        return [st] if st else ["PLACE", animal]

    elif kind == "care":
        if pos == tuple(target):
            return ["CARE"]
        st = step_toward(pos, target)
        return [st] if st else ["CARE"]

    elif kind == "collect_fertilizer":
        if pos == tuple(target):
            return ["COLLECT_FERTILIZER"]
        st = step_toward(pos, target)
        return [st] if st else ["COLLECT_FERTILIZER"]

    elif kind == "harvest_animal":
        if pos == tuple(target):
            return ["HARVEST"]
        st = step_toward(pos, target)
        return [st] if st else ["HARVEST"]

    elif kind == "harvest_crop":
        if pos == tuple(target):
            return ["HARVEST"]
        st = step_toward(pos, target)
        return [st] if st else ["HARVEST"]

    elif kind == "water":
        if pos == tuple(target):
            return ["WATER"]
        st = step_toward(pos, target)
        return [st] if st else ["WATER"]

    elif kind == "build_pasture":
        if pos == tuple(target):
            return ["BUILD_PASTURE"]
        st = step_toward(pos, target)
        return [st] if st else ["BUILD_PASTURE"]

    elif kind == "plant":
        crop, cell = target
        if pos == tuple(cell):
            return ["PLANT", crop]
        st = step_toward(pos, cell)
        return [st] if st else ["PLANT", crop]

    elif kind == "weed":
        if pos == tuple(target):
            return ["DIG"]
        st = step_toward(pos, target)
        return [st] if st else ["DIG"]

    return ["PASS"]


def _build_tasks(scan, me, private, free_cells, day, total_days):
    """Build prioritized task list based on current farm state."""
    tasks = []

    # Priority 1: Feed animals (critical — miss 2 days = animal escapes)
    for cell in scan["feed"]:
        tasks.append(("feed", cell))

    # Priority 2: Water crops
    for cell in scan["water"]:
        tasks.append(("water", cell))

    # Priority 3: Harvest crops (MELON, STRAWBERRY, WHEAT ready)
    for cell in scan["harvest_crop"]:
        tasks.append(("harvest_crop", cell))

    # Priority 4: Harvest animals (MILK, WOOL ready)
    for cell in scan["harvest_animal"]:
        tasks.append(("harvest_animal", cell))

    # Priority 5: CARE animals (generates fertilizer)
    for cell in scan["care"]:
        tasks.append(("care", cell))

    # Priority 6: Collect fertilizer
    for cell in scan["collect_fertilizer"]:
        tasks.append(("collect_fertilizer", cell))

    # Priority 7: Build PASTUREs on empty tiles (Zero-COOP Policy)
    if day < total_days - 8:
        for cell in free_cells[:8]:
            tasks.append(("build_pasture", cell))

    # Priority 8: Place animals from shed into empty PASTURE structures
    shed = (private.get("shed") or {})
    invs = (private.get("inventories") or [])
    unplaced = {}
    for a in ("COW", "SHEEP"):
        n = int(shed.get(a, 0))
        for inv in invs:
            n += int(inv.get(a, 0))
        if n > 0:
            unplaced[a] = n

    if unplaced:
        for (cell, kind) in scan["structures_empty"]:
            if kind == "PASTURE":
                for a, n in list(unplaced.items()):
                    if n <= 0:
                        continue
                    tasks.append(("place_animal", (a, cell)))
                    unplaced[a] -= 1
                    break

    # Priority 9: Plant seeds (STRAWBERRY, MELON, WHEAT only) on free cells
    seeds = private.get("seeds") or {}
    ci = 0
    if day < total_days - 3:
        for crop in ("STRAWBERRY", "MELON", "WHEAT"):
            crop_seeds = int(seeds.get(crop, 0))
            if crop_seeds > 0:
                for cell in free_cells[ci : ci + crop_seeds]:
                    tasks.append(("plant", (crop, cell)))
                ci += crop_seeds

    # Priority 10: Remove weeds
    for cell in scan["weeds"]:
        tasks.append(("weed", cell))

    return tasks


def _assign_tasks(positions, tasks, invs):
    """Greedy nearest-task assignment."""
    assignment = {}
    available_tasks = list(tasks)
    assigned_tasks = set()

    for i, pos in enumerate(positions):
        best_task = None
        best_dist = 999999
        best_idx = -1
        for j, task in enumerate(available_tasks):
            if j in assigned_tasks:
                continue
            kind = task[0]
            target = task[1] if len(task) > 1 else None
            if target is None:
                continue
            if isinstance(target, tuple) and len(target) == 2 and isinstance(target[0], int):
                dist = manhattan(pos, target)
            elif isinstance(target, tuple) and len(target) == 2:
                # (animal, cell) or (crop, cell) format
                dist = manhattan(pos, target[1])
            else:
                dist = 0
            # Adjust by priority
            priority = TASK_PRIORITY.get(kind, 0)
            score = dist - priority * 3
            if score < best_dist:
                best_dist = score
                best_task = task
                best_idx = j
        if best_task is not None:
            assignment[i] = best_task
            assigned_tasks.add(best_idx)
    return assignment


# ── Market order builder ──────────────────────────────────────────────────────
def _make_market_orders(obs, player=0):
    """Build market orders following top-player empirical strategy."""
    me = obs["farms"][player]
    private = obs.get("private") or {}
    market = obs.get("market") or {}
    minv = market.get("inventory") or {}
    shed = private.get("shed") or {}
    seeds = private.get("seeds") or {}
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    total_days = 30
    money = float(me.get("money", 0))
    quadrants = me.get("unlocked_quadrants") or ["NW"]
    unlocked_quads = len(quadrants)
    free_cells = _free_cells(me, len(me.get("tiles") or []) or 10)
    animals = _count_animals(me, private)
    hires_today = int(me.get("hires_today", 0))

    orders = []

    # Rule R1: Day 0 Hour 1 Opening Playbook
    if day == 0 and hour <= 1:
        if money >= 2500 or hires_today == 0:
            return [
                ["HIRE"],
                ["HIRE"],
                ["HIRE"],
                ["HIRE"],
                ["HIRE"],
                ["BUY_ANIMAL", "COW", 2],
                ["BUY_ANIMAL", "SHEEP", 2],
                ["BUY_SEED", "WHEAT", 7],
                ["BUY_SEED", "MELON", 12],
                ["BUY_PRODUCT", "WHEAT", 5],
            ]

    # Rule R3.2 / Market Sales: Sell produce
    hold = {"WHEAT": feed_hold(animals, int(shed.get("WHEAT", 0)))}
    orders += plan_sells(shed, minv, day, hour, total_days, hold)
    money_left = money

    # Emergency WHEAT buy for animal feed if shed WHEAT is low
    if animals > 0 and int(shed.get("WHEAT", 0)) < animals * 2 and day < total_days - 1:
        need = min(40, animals * 4 - int(shed.get("WHEAT", 0)))
        if need > 0:
            c, _ = buy_cost("WHEAT", minv.get("WHEAT", 10000), need)
            if money_left >= c:
                orders.append(["BUY_PRODUCT", "WHEAT", need])
                money_left -= c

    # Rule R3.4: Land Expansion Triggers
    if day >= 7 and unlocked_quads < 2:
        land_c = _land_cost(me)
        if money_left >= land_c + 100:
            orders.append(["BUY_LAND"])
            money_left -= land_c
            unlocked_quads += 1

    if day >= 11 and unlocked_quads < 4:
        while unlocked_quads < 4:
            land_c = _land_cost(me)
            if money_left >= land_c + 100:
                orders.append(["BUY_LAND"])
                money_left -= land_c
                unlocked_quads += 1
            else:
                break

    # Rule R2: Worker Hiring & Coin Balance Threshold Check
    # Scale worker count based on land expansion: 5 hands on Day 0; up to 7 hands on Day 7 (if coins > 600); up to 11-14 hands on Day 11+ (if coins > 15,000)
    target_hands = 5
    if day >= 11:
        if money_left >= 15000:
            target_hands = 14
        elif money_left >= 5000:
            target_hands = 11
        elif money_left >= 600:
            target_hands = 7
    elif day >= 7:
        if money_left >= 600:
            target_hands = 7

    active_hands = len(me.get("hands") or [])
    if active_hands < target_hands and hour <= 1:
        needed = target_hands - active_hands
        for _ in range(needed):
            c = hire_cost(hires_today)
            # Explicit coin balance check before hiring worker
            reserve = 32
            if money_left >= c + 32 and money_left >= 32:
                orders.append(["HIRE"])
                money_left -= c
                hires_today += 1
            else:
                break

    # Rule R3.3 / Zero-COOP Policy: Fill empty PASTURE structures with COW or SHEEP
    scan = _scan(me, day)
    if day > 0 and hour <= 2 and scan["structures_empty"] and day < total_days - 5:
        for (cell, kind) in scan["structures_empty"][:4]:
            if kind == "PASTURE":
                milk_p = price("MILK", minv.get("MILK", 10000)) * 0.5
                wool_p = price("WOOL", minv.get("WOOL", 10000)) / 3.0
                a = "SHEEP" if wool_p > milk_p else "COW"
                cost = ANIMAL_SPECS[a]["cost"]
                if money_left >= cost + 100:
                    orders.append(["BUY_ANIMAL", a, 1])
                    money_left -= cost

    # Rule R3.2 / Zero-CARROT/TOMATO Policy: Buy seeds (WHEAT, MELON, STRAWBERRY only)
    if day < total_days - 5 and free_cells:
        current_wheat_seeds = int(seeds.get("WHEAT", 0))
        current_melon_seeds = int(seeds.get("MELON", 0))
        current_straw_seeds = int(seeds.get("STRAWBERRY", 0))

        if day >= 20:
            # Late game: shift entirely to WHEAT for feed security & sell loop
            if current_wheat_seeds < 7:
                n = min(7, len(free_cells))
                cost = n * CROP_SPECS["WHEAT"]["seed"]
                if money_left >= cost + 100:
                    orders.append(["BUY_SEED", "WHEAT", n])
                    money_left -= cost
        else:
            # Early/Mid game: plant MELON and STRAWBERRY for cash, WHEAT for feed
            if current_wheat_seeds < 3 and animals > 0:
                n = min(5, len(free_cells))
                cost = n * CROP_SPECS["WHEAT"]["seed"]
                if money_left >= cost + 100:
                    orders.append(["BUY_SEED", "WHEAT", n])
                    money_left -= cost
            elif current_straw_seeds < 3 and money_left >= 500:
                n = min(5, len(free_cells))
                cost = n * CROP_SPECS["STRAWBERRY"]["seed"]
                if money_left >= cost + 200:
                    orders.append(["BUY_SEED", "STRAWBERRY", n])
                    money_left -= cost
            elif current_melon_seeds < 3 and money_left >= 400:
                n = min(5, len(free_cells))
                cost = n * CROP_SPECS["MELON"]["seed"]
                if money_left >= cost + 200:
                    orders.append(["BUY_SEED", "MELON", n])
                    money_left -= cost

    # Additional Land Purchases if farm is full
    if unlocked_quads < 4 and day < total_days - 8:
        land_cost = _land_cost(me)
        if len(free_cells) < 3 and money_left >= land_cost + 1000:
            orders.append(["BUY_LAND"])
            money_left -= land_cost

    return orders[:10]


# ── Main agent internal logic ─────────────────────────────────────────────────
def _agent(obs):
    player = obs["player"]
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    me = obs["farms"][player]
    private = obs.get("private") or {}
    market = obs.get("market") or {}
    minv = market.get("inventory") or {}
    tiles = me.get("tiles") or []
    board = len(tiles) or 10
    total_days = 30
    money = me.get("money", 0)
    shed = private.get("shed") or {}
    seeds = private.get("seeds") or {}
    invs = private.get("inventories") or [{}]

    scan = _scan(me, day)
    free_cells = _free_cells(me, board)
    animals = _count_animals(me, private)

    orders = _make_market_orders(obs, player)

    # Build task list
    tasks = _build_tasks(scan, me, private, free_cells, day, total_days)

    # Assign tasks to farmer + hands
    positions = [tuple(me.get("farmer") or (4, 4))]
    positions += [tuple(h) for h in (me.get("hands") or [])]
    ops_out = [None] * len(positions)

    # Rule R3 / Product Claiming & Backpack Drop-off Fix:
    # Only drop produce (MELON, STRAWBERRY, MILK, WOOL, FERTILIZER)
    sheds = shed_adjacent_cells(board, me)
    shed_positions = [tuple(c) for c in sheds]
    for i, pos in enumerate(positions):
        inv = invs[i] if i < len(invs) else {}
        produce_carry = sum(int(v) for k, v in inv.items() if k in PRODUCE_ITEMS)
        total_carry = sum(int(v) for k, v in inv.items() if k not in ANIMAL_ITEMS)
        pos_t = tuple(pos)
        near_shed = pos_t in shed_positions

        if produce_carry >= 5 or (produce_carry >= 1 and near_shed) or total_carry >= 15:
            if near_shed:
                ops_out[i] = ["DROP"]
            else:
                tgt = min(sheds, key=lambda c: manhattan(pos, c))
                st = step_toward(pos, tgt)
                ops_out[i] = [st] if st else ["DROP"]

    # Assign remaining workers to tasks
    free_units = [i for i in range(len(positions)) if ops_out[i] is None]
    free_positions = [positions[i] for i in free_units]
    free_invs = [invs[i] if i < len(invs) else {} for i in free_units]
    assignment = _assign_tasks(free_positions, tasks, free_invs)

    shed_wheat = int(shed.get("WHEAT", 0))
    for local_i, task in assignment.items():
        gi = free_units[local_i]
        ops_out[gi] = _unit_op(positions[gi], task, private, gi, board, me, shed_wheat)

    for i in range(len(ops_out)):
        if ops_out[i] is None:
            ops_out[i] = ["PASS"]

    return {"farmer": ops_out[0], "hands": ops_out[1:], "market": orders}


def _to_dict(obj):
    """Recursively convert kaggle_environments Struct to plain dict."""
    try:
        import json
        return json.loads(json.dumps(obj))
    except Exception:
        return obj


# ── Compat exports (used by env_wrapper.py) ───────────────────────────────────
def plan_portfolio(day, total_days, money, free_tiles, seeds):
    """Legacy compat — top strategy doesn't use this."""
    return []


def _count_animals_compat(me, private=None):
    return _count_animals(me, private)


# ── Entrypoint function (MUST be the last top-level function defined) ────────
def agent(obs, config=None):
    try:
        return _agent(_to_dict(obs))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"farmer": ["PASS"], "hands": [], "market": []}
