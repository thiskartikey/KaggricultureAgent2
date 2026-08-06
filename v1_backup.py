"""Kaggriculture agent v1 — price-curve seller + crop portfolio + cheap-labor scaling.

Strategy:
- Exact reconstruction of the market price function -> never dump into our own glut.
- Sell each resource only down to a reserve price (adaptive; collapses late-game).
- Crop portfolio: wheat/carrot early cash -> melons mid-game (highest $/tile-day).
- Hire hands aggressively (fib cost = pennies) so labor never bottlenecks tiles.
- Buy land when cash allows; plant deadlines respect season end.
"""
import math

# ---- game constants (from README) ----
CROPS = {
    "WHEAT":  {"seed": 10, "first": 2,  "maxday": 4,  "plant_by": 24},
    "CARROT": {"seed": 20, "first": 2,  "maxday": 3,  "plant_by": 25},
    "MELON":  {"seed": 80, "first": 10, "maxday": 10, "plant_by": 18},
}
# res: (base, I0, T, (below_func, below_target), (above_func, above_target))
MARKET = {
    "WHEAT":      (25, 10000, 400, ("sqrt", .8),   ("log", .2)),
    "CARROT":     (35, 10000, 450, ("log", .2),    ("sqrt", .7)),
    "TOMATO":     (60, 10000, 200, ("linear", .4), ("sqrt", .6)),
    "STRAWBERRY": (120, 10000, 100, ("sqrt", .7),  ("linear", 1.6)),
    "MELON":      (250, 10000, 300, ("log", .2),   ("sq", 3.6)),
    "EGG":        (50, 10000, 332, ("linear", .4), ("log", .2)),
    "MILK":       (160, 10000, 122, ("sqrt", .6),  ("linear", 1.6)),
    "WOOL":       (200, 10000, 105, ("log", .2),   ("sq", 3.2)),
    "FERTILIZER": (100, 10000, 200, ("linear", .4), ("linear", .4)),
}
RESERVE = {"WHEAT": 15, "CARROT": 22, "MELON": 130, "TOMATO": 30,
           "STRAWBERRY": 70, "EGG": 30, "MILK": 90, "WOOL": 110, "FERTILIZER": 55}

SHED_TILES = [(4, 4), (5, 4), (4, 5), (5, 5)]


def _f(name, x):
    if name == "linear":
        return x
    if name == "sq":
        return x * x
    if name == "sqrt":
        return math.sqrt(x)
    if name == "log":
        return math.log1p(x)
    if name == "log10":
        return math.log10(1 + x)
    return x


def price(res, inv):
    base, I0, T, below, above = MARKET[res]
    if inv == I0:
        return base
    if inv < I0:
        fn, tgt = below
        sign = 1
    else:
        fn, tgt = above
        sign = -1
    amp = tgt * base / _f(fn, T)
    return max(1, round(base + sign * amp * _f(fn, abs(inv - I0))))


def max_sell(res, inv, have, reserve):
    """Largest q <= have such that the price of the q-th unit >= reserve."""
    lo, q = 0, 0
    for k in range(1, min(have, 400) + 1):
        if price(res, inv + k - 1) >= reserve:
            q = k
        else:
            break
    return q


def _dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _step_toward(pos, tgt):
    x, y = pos
    tx, ty = tgt
    if x < tx:
        return "EAST"
    if x > tx:
        return "WEST"
    if y < ty:
        return "SOUTH"
    if y > ty:
        return "NORTH"
    return "PASS"


def _crop_want(day):
    if 4 <= day <= CROPS["MELON"]["plant_by"]:
        return "MELON"
    if day <= CROPS["CARROT"]["plant_by"]:
        return "CARROT" if day % 2 else "WHEAT"
    if day <= CROPS["WHEAT"]["plant_by"]:
        return "WHEAT"
    return None


def _agent(obs):
    player = obs["player"]
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    me = obs["farms"][player]
    tiles = me["tiles"]
    money = me["money"]
    priv = obs["private"]
    seeds = dict(priv.get("seeds", {}) or {})
    shed = priv.get("shed", {}) or {}
    market_state = obs.get("market", {}) or {}
    minv = market_state.get("inventory", {}) or {}
    n = len(tiles)

    # ---------- build task list over unlocked tiles ----------
    harvest_t, water_t, empty_t, weed_t = [], [], [], []
    for y in range(n):
        for x in range(n):
            t = tiles[y][x]
            if t == "LOCKED":
                continue
            if t is None:
                empty_t.append((x, y))
                continue
            if not isinstance(t, dict):
                continue
            kind = t.get("kind")
            if kind == "WEED":
                weed_t.append((x, y))
            elif kind == "PLANT":
                crop = t.get("crop")
                cfg = CROPS.get(crop)
                age = day - t.get("planted_day", day)
                ready = (cfg and age >= cfg["maxday"]) or (
                    not cfg and t.get("yield_units", 0) > 0)
                if ready and t.get("yield_units", 0) >= 0:
                    harvest_t.append((x, y))
                elif not t.get("watered_today", False):
                    water_t.append((x, y))

    # ---------- units = farmer + hands ----------
    units = [tuple(me["farmer"])] + [tuple(h) for h in me.get("hands", [])]
    claimed = set()
    plant_budget = dict(seeds)  # per-crop PLANT actions we may issue this turn
    actions = []

    tasks = ([(0, p) for p in harvest_t] + [(1, p) for p in water_t] +
             [(2, p) for p in empty_t] + [(3, p) for p in weed_t])

    for pos in units:
        # act in place if standing on a task tile
        x, y = pos
        t = tiles[y][x] if 0 <= y < n and 0 <= x < n else None
        act = None
        if isinstance(t, dict) and t != "LOCKED":
            kind = t.get("kind")
            if kind == "PLANT":
                crop = t.get("crop")
                cfg = CROPS.get(crop)
                age = day - t.get("planted_day", day)
                if cfg and age >= cfg["maxday"]:
                    act = ["HARVEST"]
                elif not cfg and t.get("yield_units", 0) > 0:
                    act = ["HARVEST"]
                elif not t.get("watered_today", False):
                    act = ["WATER"]
            elif kind == "WEED":
                if not harvest_t and not water_t:
                    act = ["DIG"]
        elif t is None:
            # plant best available seed
            for crop in ("MELON", "CARROT", "WHEAT"):
                if plant_budget.get(crop, 0) > 0 and day <= CROPS[crop]["plant_by"]:
                    act = ["PLANT", crop]
                    plant_budget[crop] -= 1
                    break
        if act:
            actions.append(act)
            claimed.add(pos)
            continue

        # otherwise: walk to nearest unclaimed task
        best = None
        for prio, p in tasks:
            if p in claimed:
                continue
            if prio == 2:
                # only worth walking to empty tile if we hold a plantable seed
                if not any(plant_budget.get(c, 0) > 0 and day <= CROPS[c]["plant_by"]
                           for c in CROPS):
                    continue
            d = _dist(pos, p)
            key = (prio, d)
            if best is None or key < best[0]:
                best = (key, p)
        if best:
            claimed.add(best[1])
            actions.append([_step_toward(pos, best[1])])
        else:
            actions.append(["PASS"])

    # ---------- market orders ----------
    orders = []
    unlocked = me.get("unlocked_quadrants", ["NW"])
    n_unlocked = len(unlocked)

    # 1. hire hands at day start — fib cost is pennies
    target_hands = min(3 + 2 * (n_unlocked - 1), 7)
    if hour == 0:
        need = target_hands - me.get("hires_today", 0)
        for _ in range(max(0, need)):
            orders.append(["HIRE"])

    # 2. buy land when cash comfortably covers it (after first melon wave is funded)
    if n_unlocked < 4 and 6 <= day <= 20:
        cost = 1000 * (2 ** (n_unlocked - 1))
        if money >= cost + 900:
            orders.append(["BUY_LAND"])

    # 3. seed purchases — fill the pipeline for empty tiles
    want = _crop_want(day)
    if want:
        empties = len(empty_t)
        have = sum(seeds.get(c, 0) for c in CROPS)
        pipeline = 12 if n_unlocked == 1 else 18
        need = max(0, min(empties, pipeline) - have)
        if need > 0:
            cost = CROPS[want]["seed"]
            afford = max(0, int((money - 150) // cost))
            q = min(need, afford, 10)
            if q > 0:
                orders.append(["BUY_SEED", want, q])
                # early game: mix wheat in alongside carrot
                if want == "CARROT" and money > 400:
                    orders.append(["BUY_SEED", "WHEAT", min(5, q)])

    # 4. sells — marginal-revenue scheduler with adaptive reserve
    sellable = [(r, h) for r, h in shed.items() if r in MARKET and h > 0]
    for res, have in sorted(sellable, key=lambda kv: -price(kv[0], minv.get(kv[0], 10000)) * kv[1]):
        reserve = RESERVE.get(res, 20)
        if day >= 28:
            reserve = 2
        elif day >= 24:
            reserve = max(2, int(reserve * 0.5))
        elif have > 40:
            reserve = max(2, int(reserve * 0.7))
        inv = minv.get(res, MARKET[res][1])
        q = max_sell(res, inv, have, reserve)
        if q > 0:
            orders.append(["SELL", res, q])

    return {"farmer": actions[0], "hands": actions[1:], "market": orders[:10]}


def agent(obs):
    """Entry point — must be the LAST function defined (kaggle loads the last callable)."""
    try:
        return _agent(obs)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
