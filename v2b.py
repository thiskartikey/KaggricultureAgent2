"""Kaggriculture agent -- heuristic baseline v2 (modular)."""
import math

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
    "STRAWBERRY": 0.80, "MELON": 0.80, "MILK": 0.80, "WOOL": 0.80,
    "FERTILIZER": 0.55,
}


def reserve_price(resource, day, total_days=30):
    base = MARKET_PARAMS[resource][0]
    frac = _RESERVE_FRAC.get(resource, 0.7)
    if day >= total_days - 1:
        return 1
    if day >= total_days - 3:
        frac *= 0.5
    return max(1, int(math.floor(frac * base)))


SHOP_DEMANDS = {
    "BAKERY":         {"EGG": 1, "WHEAT": 1},
    "PIZZA_SHOP":     {"MILK": 1, "TOMATO": 1, "WHEAT": 1},
    "BRUNCH_SPOT":    {"EGG": 1, "WHEAT": 1, "STRAWBERRY": 1},
    "YARN_STORE":     {"WOOL": 2},
    "ICE_CREAM_SHOP": {"STRAWBERRY": 1, "MILK": 1},
    "PET_CAFE":       {"CARROT": 2},
    "SMOOTHIE_SHOP":  {"STRAWBERRY": 1, "MILK": 1},
    "FARMERS_MARKET": {"WHEAT": 1, "CARROT": 1, "TOMATO": 1, "STRAWBERRY": 1},
}
SHOP_DEMANDS["ICE_CREAM_SHOP"]["WHEAT"] = 1
CENTER_PRODUCTS = [p for p in PRODUCTS if p != "FERTILIZER"]


def _norm_shop(name):
    return str(name).strip().upper().replace(" ", "_").replace("-", "_")


def town_center_mult(day):
    return 4 if day >= 20 else (2 if day >= 10 else 1)


def town_drain_per_day(unlocked_shops, day, turns_per_day=24,
                       shop_interval=4, center_interval=12):
    drain = {p: 0.0 for p in PRODUCTS}
    center_ticks = turns_per_day / float(center_interval)
    m = town_center_mult(day)
    for p in CENTER_PRODUCTS:
        drain[p] += center_ticks * m
    shop_ticks = turns_per_day / float(shop_interval)
    for s in unlocked_shops or []:
        for p, q in SHOP_DEMANDS.get(_norm_shop(s), {}).items():
            drain[p] += shop_ticks * q
    return drain


def expected_future_drain(unlocked_shops, day, horizon_days,
                          unlock_interval=3, turns_per_day=24,
                          shop_interval=4, center_interval=12):
    unlocked = {_norm_shop(s) for s in (unlocked_shops or [])}
    remaining = [s for s in SHOP_DEMANDS if s not in unlocked]
    drain = {p: 0.0 for p in PRODUCTS}
    if horizon_days <= 0:
        return drain
    shop_ticks = turns_per_day / float(shop_interval)
    center_ticks = turns_per_day / float(center_interval)
    for d in range(day, day + horizon_days):
        m = town_center_mult(d)
        for p in CENTER_PRODUCTS:
            drain[p] += center_ticks * m
        k = min(len(remaining), max(0, (d // unlock_interval) - (day // unlock_interval)))
        for s in unlocked:
            for p, q in SHOP_DEMANDS.get(s, {}).items():
                drain[p] += shop_ticks * q
        if remaining and k > 0:
            frac = k / float(len(remaining))
            for s in remaining:
                for p, q in SHOP_DEMANDS[s].items():
                    drain[p] += shop_ticks * q * frac
    return {p: v / horizon_days for p, v in drain.items()}


_SELL_ORDER = ["MELON", "WOOL", "MILK", "STRAWBERRY", "TOMATO", "EGG",
               "CARROT", "FERTILIZER", "WHEAT"]


def plan_sells(shed, market_inv, day, hour, total_days=30, hold=None,
               max_orders=10, shed_cap=100):
    hold = hold or {}
    load = sum(v for k, v in shed.items() if k not in ("GOOSE", "COW", "SHEEP"))
    pressure = 1.0
    if load > 0.9 * shed_cap:
        pressure = 0.5
    elif load > 0.75 * shed_cap:
        pressure = 0.8
    orders = []
    for p in _SELL_ORDER:
        avail = int(shed.get(p, 0)) - int(hold.get(p, 0))
        if avail <= 0 or p not in MARKET_PARAMS:
            continue
        res = max(1, int(reserve_price(p, day, total_days) * pressure))
        inv = int(market_inv.get(p, MARKET_PARAMS[p][1]))
        n = min(avail, units_sellable_above(p, inv, res))
        if n <= 0:
            continue
        if p in ("MELON", "WOOL", "MILK", "STRAWBERRY") and n < 2 and avail >= 2 \
           and day < total_days - 3 and pressure == 1.0:
            continue
        orders.append(["SELL", p, n])
        if len(orders) >= max_orders:
            break
    return orders


def feed_hold(animal_count, shed_wheat, days_buffer=2):
    return min(shed_wheat, animal_count * days_buffer)


CROP_SPECS = {
    "WHEAT":      dict(seed=10,  first=2,  maxday=4,  peak=4, occ=5),
    "CARROT":     dict(seed=20,  first=2,  maxday=3,  peak=3, occ=4),
    "TOMATO":     dict(seed=50,  first=8,  maxday=11, peak=4, occ=12),
    "STRAWBERRY": dict(seed=100, first=10, maxday=16, peak=4, occ=17),
    "MELON":      dict(seed=80,  first=10, maxday=10, peak=6, occ=11),
}
ANIMAL_SPECS = {
    "GOOSE": dict(cost=300, build="BUILD_COOP",    structure="COOP",    product="EGG",  interval=1, first=4),
    "COW":   dict(cost=400, build="BUILD_PASTURE", structure="PASTURE", product="MILK", interval=2, first=8),
    "SHEEP": dict(cost=500, build="BUILD_PASTURE", structure="PASTURE", product="WOOL", interval=3, first=6),
}
CROP_PRODUCT = {c: c for c in CROP_SPECS}


def _exp_unit_price(product, market_inv, extra_units, drain_day, days):
    inv = int(market_inv.get(product, MARKET_PARAMS[product][1]))
    net = int(extra_units - drain_day * days)
    mid = inv + max(0, net) // 2
    return price(product, max(1, mid))


def plan_portfolio(free_tiles, n_units, money, market_inv, shops, day,
                   total_days, opp_flood=None, planned=None):
    opp_flood = opp_flood or {}
    planned = dict(planned or {})
    drain = town_drain_per_day(shops, day)
    budget = n_units * 24 * 0.60
    picks, spend, counts = [], 0.0, {}
    committed = 0.0
    for _ in range(int(free_tiles)):
        best, best_score = None, 0.0
        days_left = total_days - day
        for c, s in CROP_SPECS.items():
            if days_left <= s["first"] + 1 or money - spend < s["seed"]:
                continue
            horizon = min(days_left, s["occ"])
            upd = s["peak"] / float(s["occ"])
            total_units = planned.get(c, 0) + upd * days_left \
                + opp_flood.get(c, 0) * days_left
            p = _exp_unit_price(c, market_inv, total_units, drain.get(c, 0), days_left)
            rev = upd * p - s["seed"] / float(s["occ"])
            apd = 1.0 + 2.0 / s["occ"]
            score = rev / apd * (0.85 ** counts.get(c, 0))
            if score > best_score:
                best, best_score = ("PLANT", c, apd, s["seed"], upd, c), score
        for a, s in ANIMAL_SPECS.items():
            if days_left <= s["first"] + 3 or money - spend < s["cost"]:
                continue
            pr = s["product"]
            upd = 1.0 / s["interval"]
            total_units = planned.get(pr, 0) + upd * days_left \
                + opp_flood.get(pr, 0) * days_left
            p = _exp_unit_price(pr, market_inv, total_units, drain.get(pr, 0), days_left)
            feed_cost = price("WHEAT", market_inv.get("WHEAT", 10000))
            rev = upd * p - feed_cost - s["cost"] / float(days_left)
            apd = 1.0 + upd + 0.2
            score = rev / apd * (0.85 ** counts.get(pr, 0))
            if score > best_score:
                best, best_score = ("ANIMAL", a, apd, s["cost"], upd, pr), score
        if best is None or best_score <= 0 or committed + best[2] > budget:
            break
        kind, name, apd, cost, upd, prod = best
        picks.append((kind, name))
        counts[prod] = counts.get(prod, 0) + 1
        spend += cost
        committed += apd
        planned[prod] = planned.get(prod, 0) + upd * (total_days - day)
    return picks


def read_opponent(opp_farm, day):
    flood = {}
    tiles = opp_farm.get("tiles") or []
    for row in tiles:
        for t in row:
            if not isinstance(t, dict):
                continue
            if t.get("kind") == "PLANT":
                c = t.get("crop")
                s = CROP_SPECS.get(c)
                if not s:
                    continue
                age = day - t.get("planted_day", day)
                ready_in = max(1, s["maxday"] - age)
                if ready_in <= 7:
                    flood[c] = flood.get(c, 0.0) + s["peak"] / 7.0
            elif t.get("kind") in ("COOP", "PASTURE") and t.get("animal"):
                sp = ANIMAL_SPECS.get(t["animal"])
                if sp:
                    pr = sp["product"]
                    flood[pr] = flood.get(pr, 0.0) + 1.0 / sp["interval"]
    return flood


_FIB = [1, 1]
while len(_FIB) < 40:
    _FIB.append(_FIB[-1] + _FIB[-2])


def hire_cost(hires_today, mult=1):
    return mult * _FIB[min(hires_today, len(_FIB) - 1)]


def plan_hires(day, hour, hires_today, money, value_per_action, total_days=30,
               max_hands=6, mult=1):
    if day >= total_days - 1 or hour > 4:
        return 0
    n = 0
    while hires_today + n < max_hands:
        cost = hire_cost(hires_today + n, mult)
        turns_left = 24 - hour
        profit = turns_left * value_per_action * 0.6
        if money < cost + 200 or profit < 2.0 * cost:
            break
        n += 1
        money -= cost
    return n


def step_toward(pos, target):
    x, y = pos
    tx, ty = target
    dx, dy = tx - x, ty - y
    if dx == 0 and dy == 0:
        return None
    if abs(dx) >= abs(dy):
        return "EAST" if dx > 0 else "WEST"
    return "SOUTH" if dy > 0 else "NORTH"


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def shed_adjacent_cells(board_size=10):
    h = board_size // 2
    return [(h - 1, h - 1), (h, h - 1), (h - 1, h), (h, h)]


def assign_tasks(unit_positions, tasks):
    tasks = sorted(enumerate(tasks), key=lambda it: -it[1][2])
    free = set(range(len(unit_positions)))
    out = {}
    for _, (cell, ops, _pr) in tasks:
        if not free:
            break
        best_u, best_d = None, 10 ** 9
        for u in free:
            d = manhattan(unit_positions[u], cell)
            if d < best_d:
                best_u, best_d = u, d
        free.discard(best_u)
        out[best_u] = (cell, ops)
    return out


SELL_PRODUCE = ["MELON", "WOOL", "MILK", "STRAWBERRY", "TOMATO", "EGG", "CARROT", "WHEAT", "FERTILIZER"]
ANIMAL_ITEMS = ("GOOSE", "COW", "SHEEP")


def _my_pipeline(me, day, total_days):
    planned = {}
    for row in me.get("tiles") or []:
        for t in row:
            if not isinstance(t, dict):
                continue
            if t.get("kind") == "PLANT":
                c = t.get("crop")
                s = CROP_SPECS.get(c)
                if s:
                    planned[c] = planned.get(c, 0) + max(s["peak"], t.get("yield_units", 0))
            elif t.get("kind") in ("COOP", "PASTURE") and t.get("animal"):
                sp = ANIMAL_SPECS.get(t["animal"])
                if sp:
                    pr = sp["product"]
                    planned[pr] = planned.get(pr, 0) + (total_days - day) / float(sp["interval"])
    return planned


def _free_cells(me, board_size):
    cells = []
    tiles = me.get("tiles") or []
    for y in range(len(tiles)):
        for x in range(len(tiles[y])):
            if tiles[y][x] is None:
                cells.append((x, y))
    h = board_size // 2
    cells.sort(key=lambda c: manhattan(c, (h, h)))
    return cells


def _scan(me, day):
    out = dict(water=[], harvest_crop=[], harvest_urgent=[], feed=[], care=[],
               collect=[], weeds=[], structures_empty=[], harvest_animal=[])
    for y, row in enumerate(me.get("tiles") or []):
        for x, t in enumerate(row):
            if not isinstance(t, dict):
                continue
            k = t.get("kind")
            if k == "PLANT":
                c, s = t.get("crop"), CROP_SPECS.get(t.get("crop"))
                if not s:
                    continue
                age = day - t.get("planted_day", day)
                onetime = c in ("WHEAT", "CARROT", "MELON")
                if not t.get("watered_today") and age < s["occ"]:
                    pr = 120 if t.get("consecutive_unwatered", 0) >= 1 else 100
                    out["water"].append(((x, y), pr))
                if t.get("yield_units", 0) > 0:
                    if onetime:
                        if age > s["maxday"]:
                            out["harvest_urgent"].append((x, y))
                        elif age >= s["maxday"]:
                            out["harvest_crop"].append((x, y))
                    else:
                        out["harvest_crop"].append((x, y))
            elif k == "WEED":
                out["weeds"].append((x, y))
            elif k in ("COOP", "PASTURE"):
                if t.get("animal"):
                    if not t.get("fed_today"):
                        out["feed"].append(((x, y), 115 if t.get("consecutive_unfed", 0) >= 1 else 105))
                    if t.get("yield_units", 0) > 0:
                        out["harvest_animal"].append((x, y))
                    if t.get("fertilizer_available"):
                        out["collect"].append((x, y))
                    if t.get("fed_today") and not t.get("cared_today"):
                        out["care"].append((x, y))
                else:
                    out["structures_empty"].append(((x, y), t.get("kind")))
    return out


def _count_animals(me):
    n = 0
    for row in me.get("tiles") or []:
        for t in row:
            if isinstance(t, dict) and t.get("kind") in ("COOP", "PASTURE") and t.get("animal"):
                n += 1
    return n


def build_tasks(scan, me, private, picks, free_cells, day, hour, board_size, total_days):
    tasks = []
    for cell, pr in scan["water"]:
        tasks.append((cell, ["WATER"], pr))
    for cell, pr in scan["feed"]:
        tasks.append((cell, ["FEED"], pr))
    for cell in scan["harvest_urgent"]:
        tasks.append((cell, ["HARVEST"], 95))
    for cell in scan["harvest_crop"]:
        tasks.append((cell, ["HARVEST"], 80))
    for cell in scan["harvest_animal"]:
        tasks.append((cell, ["HARVEST"], 75))
    shed = private.get("shed") or {}
    placeable = [(cell, kind) for cell, kind in scan["structures_empty"]]
    for a in ANIMAL_ITEMS:
        want = ANIMAL_SPECS[a]["structure"]
        n = int(shed.get(a, 0))
        for cell, kind in placeable:
            if n <= 0 or kind != want:
                continue
            tasks.append((cell, ["__PLACE__", a], 85))
            n -= 1
    seeds = private.get("seeds") or {}
    ci = 0
    for kind, name in picks:
        if ci >= len(free_cells):
            break
        if kind == "PLANT" and seeds.get(name, 0) > 0:
            tasks.append((free_cells[ci], ["PLANT", name], 70))
            seeds = dict(seeds)
            seeds[name] -= 1
            ci += 1
        elif kind == "ANIMAL":
            tasks.append((free_cells[ci], [ANIMAL_SPECS[name]["build"]], 65))
            ci += 1
    if day < total_days - 2:
        for cell in scan["weeds"]:
            tasks.append((cell, ["DIG"], 40))
    for cell in scan["collect"]:
        tasks.append((cell, ["COLLECT_FERTILIZER"], 30))
    for cell in scan["care"]:
        tasks.append((cell, ["CARE"], 25))
    return tasks


def _unit_op(pos, task, private, unit_idx, board_size, feed_wheat_needed):
    invs = private.get("inventories") or []
    inv = invs[unit_idx] if unit_idx < len(invs) else {}
    cell, ops = task
    op = ops[0]
    if op == "FEED" and int((inv or {}).get("WHEAT", 0)) <= 0:
        sheds = shed_adjacent_cells(board_size)
        if tuple(pos) in [tuple(c) for c in sheds]:
            n = max(1, min(int((private.get("shed") or {}).get("WHEAT", 0)), feed_wheat_needed))
            if n > 0:
                return ["PICKUP", "WHEAT", n]
            return ["PASS"]
        tgt = min(sheds, key=lambda c: manhattan(pos, c))
        step = step_toward(pos, tgt)
        return [step] if step else ["PASS"]
    if op == "__PLACE__":
        a = ops[1]
        if int((inv or {}).get(a, 0)) > 0:
            if tuple(pos) == tuple(cell):
                return ["PLACE", a]
            step = step_toward(pos, cell)
            return [step] if step else ["PLACE", a]
        sheds = shed_adjacent_cells(board_size)
        if tuple(pos) in [tuple(c) for c in sheds]:
            if int((private.get("shed") or {}).get(a, 0)) > 0:
                return ["PICKUP", a, 1]
            return ["PASS"]
        tgt = min(sheds, key=lambda c: manhattan(pos, c))
        step = step_toward(pos, tgt)
        return [step] if step else ["PASS"]
    if tuple(pos) == tuple(cell):
        return list(ops)
    step = step_toward(pos, cell)
    return [step] if step else list(ops)


def _drop_task_needed(inv):
    return sum(int(v) for k, v in (inv or {}).items()) >= 25


def _pasture_choice(market_inv):
    m = price("MILK", market_inv.get("MILK", 10000)) * 0.5
    w = price("WOOL", market_inv.get("WOOL", 10000)) / 3.0
    return "COW" if m >= w else "SHEEP"


def _land_order(me, free_count, day, money, total_days):
    q = len(me.get("unlocked_quadrants") or ["NW"])
    if q >= 4:
        return None
    cost = 1000 * (2 ** (q - 1))
    if free_count < 6 and day < total_days - 8 - 2 * (q - 1) and money > cost + 500:
        return ["BUY_LAND"]
    return None


def _desired_hands(me, scan, free_cells, picks, day, total_days):
    if day >= total_days - 1:
        return 0
    work = len(scan["water"]) + len(scan["feed"]) + len(scan["harvest_crop"]) \
        + len(scan["harvest_animal"]) + min(len(picks), len(free_cells)) + len(scan["weeds"])
    return max(0, min(11, work // 5))


def _agent(obs):
    player = obs["player"]
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    me = obs["farms"][player]
    opp = obs["farms"][1 - player]
    private = obs.get("private") or {}
    market = obs.get("market") or {}
    minv = market.get("inventory") or {}
    shops = (obs.get("town") or {}).get("unlocked_shops") or []
    tiles = me.get("tiles") or []
    board = len(tiles) or 10
    total_days = 30
    money = me.get("money", 0)
    shed = private.get("shed") or {}
    seeds = private.get("seeds") or {}
    invs = private.get("inventories") or [{}]

    scan = _scan(me, day)
    free_cells = _free_cells(me, board)
    animals = _count_animals(me)
    n_units = 1 + len(me.get("hands") or [])
    pipeline = _my_pipeline(me, day, total_days)
    for p in SELL_PRODUCE:
        pipeline[p] = pipeline.get(p, 0) + int(shed.get(p, 0))
    opp_flood = read_opponent(opp, day)

    picks = []
    if day < total_days - 3 and free_cells:
        picks = plan_portfolio(len(free_cells), n_units, money, minv, shops,
                               day, total_days, opp_flood, pipeline)

    orders = []
    hold = {"WHEAT": feed_hold(animals, int(shed.get("WHEAT", 0)))}
    orders += plan_sells(shed, minv, day, hour, total_days, hold)
    money_left = money
    if animals and int(shed.get("WHEAT", 0)) < animals and day < total_days - 1:
        need = animals * 2 - int(shed.get("WHEAT", 0))
        cost, _ = buy_cost("WHEAT", minv.get("WHEAT", 10000), need)
        if money_left > cost + 100:
            orders.append(["BUY_PRODUCT", "WHEAT", need])
            money_left -= cost
    want_seeds = {}
    for kind, name in picks:
        if kind == "PLANT":
            want_seeds[name] = want_seeds.get(name, 0) + 1
    for c, n in want_seeds.items():
        n -= int(seeds.get(c, 0))
        n = min(n, 8)
        if n > 0 and money_left > CROP_SPECS[c]["seed"] * n + 100:
            orders.append(["BUY_SEED", c, n])
            money_left -= CROP_SPECS[c]["seed"] * n
    for cell, kind in scan["structures_empty"][:2]:
        a = "GOOSE" if kind == "COOP" else _pasture_choice(minv)
        pending = int(shed.get(a, 0)) + sum(int((iv or {}).get(a, 0)) for iv in invs)
        if pending == 0 and money_left > ANIMAL_SPECS[a]["cost"] + 200 \
           and day < total_days - ANIMAL_SPECS[a]["first"] - 4:
            orders.append(["BUY_ANIMAL", a, 1])
            money_left -= ANIMAL_SPECS[a]["cost"]
    want = _desired_hands(me, scan, free_cells, picks, day, total_days)
    hires_today = int(me.get("hires_today", 0))
    if hour <= 2:
        h = 0
        while hires_today + h < want:
            c = hire_cost(hires_today + h)
            if money_left < c + 50:
                break
            orders.append(["HIRE"])
            money_left -= c
            h += 1
    lo = _land_order(me, len(free_cells), day, money_left, total_days)
    if lo:
        orders.append(lo)
    orders = orders[:10]

    tasks = build_tasks(scan, me, private, picks, free_cells, day, hour, board, total_days)
    positions = [tuple(me.get("farmer") or (board // 2 - 1, board // 2 - 1))]
    positions += [tuple(h) for h in (me.get("hands") or [])]
    ops_out = [None] * len(positions)
    sheds = shed_adjacent_cells(board)
    for i, pos in enumerate(positions):
        inv = invs[i] if i < len(invs) else {}
        if _drop_task_needed(inv):
            if tuple(pos) in [tuple(c) for c in sheds]:
                ops_out[i] = ["DROP"]
            else:
                tgt = min(sheds, key=lambda c: manhattan(pos, c))
                st = step_toward(pos, tgt)
                ops_out[i] = [st] if st else ["DROP"]
    free_units = [i for i in range(len(positions)) if ops_out[i] is None]
    assign = assign_tasks([positions[i] for i in free_units], tasks)
    feed_need = max(1, min(6, len(scan["feed"])))
    for local_i, task in assign.items():
        gi = free_units[local_i]
        ops_out[gi] = _unit_op(positions[gi], task, private, gi, board, feed_need)
    for i in range(len(ops_out)):
        if ops_out[i] is None:
            ops_out[i] = ["PASS"]
    return {"farmer": ops_out[0], "hands": ops_out[1:], "market": orders}


def agent(obs):
    try:
        return _agent(obs)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
