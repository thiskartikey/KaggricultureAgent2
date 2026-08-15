"""Kaggriculture heuristic agent -- TOP PLAYER STRATEGY (v5).

Strategy mined from 72 leaderboard replays (144 player-episodes, top scores
100k-158k).  Aggregated blueprint of the 117 player-episodes scoring >=100k:

  Labour   Hands are WIPED every night, so they must be re-hired EVERY morning.
           Cost is fib(n) for the n-th hire *of that day* (1,1,2,3,5,8,13,...),
           so a full 13-hand crew costs ~609/day -- trivial next to the payoff.
           Observed: 5 hands day 0, ~7 by day 7, 11-14 every day from day 11.

  Land     3 quadrants only: NE at day 7 (1000), SW at day 11 (2000).
           The 4th quadrant (4000) is never bought -- it cannot pay back.

  Field    Steady state from day 11 on 75 tiles:
             14 PASTURE (8 COW + 6 SHEEP), 42 STRAWBERRY, 12 MELON, ~7 WHEAT.
           Day 0 opening: 6 PASTURE, 11 MELON, 7 WHEAT, 2 COW, 2 SHEEP, 5 HIRE.
           From ~day 20 spent MELON tiles are recycled into WHEAT (2-day cycle).

  Economy  Animals are the engine: each yields 1 FERTILIZER/day (base 100) for
           free on top of its product.  CARE+FEED on the same day banks a +1
           bonus on the next production day.  WHEAT is bought from the market
           as feed (~527/episode) and sold back as harvest (~474/episode).

  Zero     No GOOSE/COOP/EGG, no CARROT, no TOMATO -- all dominated.

Mechanics that drive the rules below (verified against kaggriculture.py):
  * A plant not watered 2 days running turns to WEED -- and the planting day
    already counts as unwatered, so a new plant MUST be watered the same day.
  * Non-ongoing crops (WHEAT/MELON) accumulate yield only while watered inside
    [(max_yield_day+1)//2, max_yield_day]; harvesting clears the tile, so we
    wait for max_yield_day instead of harvesting the moment yield_units > 0.
  * An animal unfed 2 days running escapes; the structure survives.
  * Shed holds 100 items; end-of-day overflow is DISCARDED, and a full shed
    blocks BUY_ANIMAL / BUY_PRODUCT -- so we sell down every turn.
  * Only 10 market orders per turn are processed; the rest are dropped
    silently, so hiring spills over into the following turns.
"""
import math

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
SELLABLE = PRODUCTS
# Ordered by how much of the score each product carries in the mined replays.
SELL_PRODUCE = ["STRAWBERRY", "MELON", "MILK", "WOOL", "FERTILIZER", "WHEAT",
                "EGG", "CARROT", "TOMATO"]
PRODUCE_ITEMS = ("MELON", "STRAWBERRY", "MILK", "WOOL", "FERTILIZER",
                 "WHEAT", "EGG", "CARROT", "TOMATO")


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
    """How many units can be sold before the price drops under `reserve`."""
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


# ── Specs (exact copies of kaggriculture.CROPS / ANIMALS) ─────────────────────
CROP_SPECS = {
    "WHEAT":      dict(seed=10,  first=2,  maxday=4,  interval=0, max_yield=6, ongoing=False),
    "CARROT":     dict(seed=20,  first=2,  maxday=3,  interval=0, max_yield=4, ongoing=False),
    "TOMATO":     dict(seed=50,  first=8,  maxday=8,  interval=1, max_yield=4, ongoing=True),
    "STRAWBERRY": dict(seed=100, first=10, maxday=10, interval=2, max_yield=4, ongoing=True),
    "MELON":      dict(seed=80,  first=10, maxday=12, interval=0, max_yield=6, ongoing=False),
}
ANIMAL_SPECS = {
    "GOOSE": dict(cost=300, build="BUILD_COOP",    structure="COOP",    product="EGG",  interval=1, first=4),
    "COW":   dict(cost=400, build="BUILD_PASTURE", structure="PASTURE", product="MILK", interval=2, first=8),
    "SHEEP": dict(cost=500, build="BUILD_PASTURE", structure="PASTURE", product="WOOL", interval=3, first=6),
}
ANIMAL_ITEMS = ("GOOSE", "COW", "SHEEP")
CROPS = list(CROP_SPECS.keys())

LAND_PRICES = [1000, 2000, 4000]   # cost of the 2nd, 3rd, 4th quadrant

# ── Blueprint targets (from the mined aggregate) ──────────────────────────────
TARGET_PASTURE_BY_DAY = ((11, 14), (7, 12), (0, 6))   # (day_from, count)
TARGET_COOP_BY_DAY = ((11, 0), (7, 0), (0, 0))
TARGET_COW = 8
TARGET_SHEEP = 6
TARGET_GOOSE = 0
TARGET_STRAWBERRY = 38  # unchanged; top players ~35-36 but layout differs
TARGET_MELON = 9
LAND_UNLOCK_DAY = (7, 11)          # earliest day for the 2nd / 3rd quadrant
SHED_CAP = 100
CASH_FLOOR = 200                   # keep enough to buy a day of animal feed


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


def target_hands(day, total_days):
    """Faster crew ramp: match top-player labour curve more tightly.

    Top players run 3 hands days 1-4, 8 hands days 5-8, 13 from day 9.
    Original was 3 until day 7, 8 until day 11.
    """
    if day <= 0:
        return 5
    if day < 5:
        return 3
    if day < 9:
        return 8
    if day >= total_days - 2:
        return 10
    return 13
def hire_cost(n_already_hired):
    """cost of the n-th hire of the day = fib(n), fib(0)=fib(1)=1."""
    a, b = 1, 1
    for _ in range(int(n_already_hired)):
        a, b = b, a + b
    return a


# ── Market helpers ─────────────────────────────────────────────────────────────
_RESERVE_FRAC = {
    "WHEAT": 0.55, "CARROT": 0.40, "TOMATO": 0.40, "EGG": 0.40,
    "MILK": 0.50, "WOOL": 0.50, "STRAWBERRY": 0.50, "MELON": 0.50,
    "FERTILIZER": 0.35,
}


def plan_sells(shed, market_inv, day, hour, total_days, hold=None):
    """Sell down every turn: the shed only holds 100 and overflow is binned.

    No price reserve: sell all available produce at market price every turn.
    The shed cap (100 items) means unsold overflow is binned at end of day, so
    waiting for a better price costs more than selling at today's price.
    Wheat is protected separately via feed_hold (animal feed buffer).
    """
    orders = []
    hold = hold or {}
    for product in SELL_PRODUCE:
        qty = int(shed.get(product, 0))
        qty = max(0, qty - int(hold.get(product, 0)))
        if qty > 0:
            orders.append(["SELL", product, qty])
    return orders


def feed_hold(animal_count, shed_wheat, days_buffer=3):
    """Wheat we refuse to sell because the animals eat it.

    An escaped animal costs its 400-500 price plus every yield it had left, so
    a few days of feed in reserve is far cheaper than running the stock to zero.
    """
    return min(shed_wheat, min(45, animal_count * days_buffer))


# ── Farm scan ─────────────────────────────────────────────────────────────────
def _crop_harvestable(t, day, total_days):
    """Non-ongoing crops keep growing while watered -- don't harvest too early."""
    spec = CROP_SPECS.get(t.get("crop"))
    if spec is None or int(t.get("yield_units", 0)) <= 0:
        return False
    age = day - int(t.get("planted_day", day))
    if age < spec["first"]:
        return False                      # HARVEST would be a silent no-op
    if spec["ongoing"]:
        return True                       # take ongoing yields as they appear
    if age >= spec["maxday"]:
        return True                       # fully grown (decay starts next day)
    if int(t["yield_units"]) >= spec["max_yield"]:
        return True
    return day >= total_days - 2          # season over: bank whatever is there


def _animal_pending(t, has_wheat=True):
    """Outstanding work on an occupied pasture, in the order it should be done.

    Feeding leads: an animal unfed two days running escapes, taking its 400-500
    purchase price and every future yield with it.
    """
    if not t.get("fed_today") and has_wheat:
        return "FEED"
    if int(t.get("yield_units", 0)) > 0:
        return "HARVEST"
    if t.get("fertilizer_available"):
        return "COLLECT_FERTILIZER"
    if not t.get("cared_today"):
        return "CARE"
    return None


def _water_urgent(t, day):
    """Does this plant need water TODAY, or can it safely wait a day?

    A plant only dies after two consecutive dry days, and ongoing crops
    (STRAWBERRY/TOMATO) accrue yield on their own schedule whether or not they
    were watered.  Watering only *adds* yield on non-ongoing crops inside their
    growth window.  So a strawberry watered yesterday can skip today, which
    roughly halves the watering bill and frees the crew for the animals.
    """
    if int(t.get("consecutive_unwatered", 0)) >= 1:
        return True                      # dies tonight if it stays dry
    if int(t.get("fertilized_until_day", -1)) >= day:
        return True                      # the bonus only lands on watered days
    spec = CROP_SPECS.get(t.get("crop"))
    if spec is None or spec["ongoing"]:
        return False
    age = day - int(t.get("planted_day", day))
    return ((spec["maxday"] + 1) // 2) <= age <= spec["maxday"]


def _scan(me, day, total_days=30):
    out = dict(water=[], water_soon=[], service=[], service_soon=[],
               harvest_crop=[], weeds=[], structures_empty=[], fertilize=[],
               feed=[])
    tiles = me.get("tiles") or []
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            if not isinstance(t, dict):
                continue
            kind = t.get("kind")
            if kind == "PLANT":
                if not t.get("watered_today"):
                    if _water_urgent(t, day):
                        out["water"].append((x, y))
                    else:
                        out["water_soon"].append((x, y))
                if _crop_harvestable(t, day, total_days):
                    out["harvest_crop"].append((x, y))
                # Fertilizer doubles ongoing-crop output on watered days; on
                # WHEAT/MELON the yield cap is already reached by watering.
                spec = CROP_SPECS.get(t.get("crop"))
                if (spec and spec["ongoing"]
                        and int(t.get("fertilized_until_day", -1)) < day
                        and day - int(t.get("planted_day", day)) >= spec["first"] - 2):
                    out["fertilize"].append((x, y))
            elif kind in ("PASTURE", "COOP"):
                if t.get("animal"):
                    if not t.get("fed_today"):
                        out["feed"].append((x, y))
                    if _animal_pending(t) is not None:
                        # EVERY unfed animal is tier-0 work, not just the ones
                        # about to starve.  The care bonus banks only when an
                        # animal is cared AND fed on the same day, and it
                        # accumulates, so a skipped feed does not merely delay a
                        # meal -- it voids that day's care and cuts the next
                        # yield.  Worth +18,184 (24/24) once the farm was
                        # compacted; before that it LOST 11,018, because feeding
                        # a scattered farm stole the crew from urgent watering.
                        if not t.get("fed_today"):
                            out["service"].append((x, y))
                        else:
                            out["service_soon"].append((x, y))
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


def _placed_animals(me):
    """Animals actually living on the farm -- these are the ones that eat."""
    n = 0
    for row in (me.get("tiles") or []):
        for t in row:
            if isinstance(t, dict) and t.get("animal"):
                n += 1
    return n


def _count_animals(me, private=None):
    n = _placed_animals(me)
    if private:
        shed = private.get("shed") or {}
        for a in ("COW", "SHEEP", "GOOSE"):
            n += int(shed.get(a, 0))
        for inv in (private.get("inventories") or []):
            for a in ("COW", "SHEEP", "GOOSE"):
                n += int(inv.get(a, 0))
    return n


def _animal_census(me, private=None):
    """Per-species count including animals still waiting in the shed."""
    out = {"COW": 0, "SHEEP": 0, "GOOSE": 0}
    for row in (me.get("tiles") or []):
        for t in row:
            if isinstance(t, dict) and t.get("animal") in out:
                out[t["animal"]] += 1
    if private:
        shed = private.get("shed") or {}
        for a in out:
            out[a] += int(shed.get(a, 0))
        for inv in (private.get("inventories") or []):
            for a in out:
                out[a] += int(inv.get(a, 0))
    return out


def _count_structures(me, kind):
    n = 0
    for row in (me.get("tiles") or []):
        for t in row:
            if isinstance(t, dict) and t.get("kind") == kind:
                n += 1
    return n


def _crop_census(me):
    out = {c: 0 for c in CROPS}
    for row in (me.get("tiles") or []):
        for t in row:
            if isinstance(t, dict) and t.get("kind") == "PLANT":
                c = t.get("crop")
                if c in out:
                    out[c] += 1
    return out


def _land_cost(me):
    n = len(me.get("unlocked_quadrants", ["NW"])) - 1
    return LAND_PRICES[n] if 0 <= n < len(LAND_PRICES) else 10 ** 9


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


def shed_adjacent_cells(board, me=None):
    half = (board // 2) if isinstance(board, int) and board else 5
    return [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]


# ── Which crop to sow next ────────────────────────────────────────────────────
def _plant_choice(day, total_days, planted, seeds):
    """Pick the crop with the best remaining payback for one free tile."""
    left = total_days - day
    # MELON: 6 units x base 250 for an 80 seed, but needs maxday(12)+1 in soil.
    if (planted.get("MELON", 0) < TARGET_MELON and left >= 13
            and int(seeds.get("MELON", 0)) > 0):
        return "MELON"
    # STRAWBERRY: ongoing, first yield +10 then every 2 days.  Two harvests
    # (240) still beat the 100 seed, so keep sowing while left >= 13.
    if (planted.get("STRAWBERRY", 0) < TARGET_STRAWBERRY and left >= 13
            and int(seeds.get("STRAWBERRY", 0)) > 0):
        return "STRAWBERRY"
    # WHEAT: min viable window = 3 days (plant+water day X, harvest day X+2 = 2 units).
    # At max_yield_day=4 we get 4 units, but even 2 units @ ~$25 beats leaving the
    # tile fallow.  Top players plant wheat into every freed tile in the endgame.
    if left >= 3 and int(seeds.get("WHEAT", 0)) > 0:
        return "WHEAT"
    return None


def _seed_targets(day, total_days, planted, free_n, harvest_crop_n=0):
    """How many seeds of each crop we still want to hold."""
    left = total_days - day
    want = {}
    
    # R1: Maintain a buffer of seeds for crops that are about to be harvested
    # so we can plant immediately.
    target_free = free_n + harvest_crop_n
    
    if left >= 13:
        want["MELON"] = max(0, min(TARGET_MELON - planted.get("MELON", 0), target_free))
        want["STRAWBERRY"] = max(
            0, min(TARGET_STRAWBERRY - planted.get("STRAWBERRY", 0),
                   target_free - want["MELON"]))
    if left >= 5:
        # Wheat fills the rest. In endgame (days 20+) expired melon/straw tiles free
        # up land that top players aggressively plant to wheat (2-day cycle).
        # Allow a larger buffer (60) so those freed tiles can all be sown immediately.
        rest = target_free - want.get("MELON", 0) - want.get("STRAWBERRY", 0)
        wmax = 60 if left <= 12 else 30
        wmin = 20 if left <= 12 else 15
        want["WHEAT"] = max(wmin, min(max(0, rest), wmax))
    return want


# ── Market order builder ──────────────────────────────────────────────────────
def _make_market_orders(obs, player=0, total_days=30, scan=None):
    me = obs["farms"][player]
    private = obs.get("private") or {}
    market = obs.get("market") or {}
    minv = market.get("inventory") or {}
    shed = private.get("shed") or {}
    seeds = private.get("seeds") or {}
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    money = float(me.get("money", 0))
    quads = len(me.get("unlocked_quadrants") or ["NW"])
    board = len(me.get("tiles") or []) or 10
    free_cells = _free_cells(me, board)
    hires_today = int(me.get("hires_today", 0))
    hands = len(me.get("hands") or [])
    fed_animals = _placed_animals(me)
    shed_total = sum(int(v) for v in shed.values())

    orders = []
    money_left = money

    # ── R1: day 0 opening -- exactly the mined blueprint, 10 orders ──────────
    if day == 0 and hour == 0:
        return [
            ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"],
            ["BUY_ANIMAL", "COW", 2],
            ["BUY_ANIMAL", "SHEEP", 2],
            ["BUY_SEED", "MELON", 11],
            ["BUY_SEED", "WHEAT", 7],
            ["BUY_PRODUCT", "WHEAT", 8],
        ]

    # ── R2: sell first so the rest of the turn is funded ─────────────────────
    # Taper the wheat buffer in the final days: animals don't need feed after
    # the game ends, so release held wheat as we approach the last turn.
    days_left = total_days - day
    effective_buffer = max(0, min(2, days_left - 1))
    hold = {"WHEAT": feed_hold(fed_animals, int(shed.get("WHEAT", 0)),
                               days_buffer=effective_buffer)}
    sells = plan_sells(shed, minv, day, hour, total_days, hold)
    # Early in the day leave order slots for hiring; catch up from hour 2.
    orders += sells if hour >= 2 else sells[:3]
    for o in orders:
        inv = int(minv.get(o[1], 10000))
        rev, _ = sell_revenue(o[1], inv, o[2])
        money_left += rev

    # ── R3: re-hire the crew EVERY morning (hands are wiped each night) ──────
    want_hands = target_hands(day, total_days)
    n = 0
    while hands + n < want_hands and len(orders) < 10:
        c = hire_cost(hires_today + n)
        if money_left < c + 20:
            break
        orders.append(["HIRE"])
        money_left -= c
        n += 1

    # ── R4: land -- 2nd quadrant day 7, 3rd day 11, never the 4th ───────────
    if quads - 1 < len(LAND_UNLOCK_DAY) and day >= LAND_UNLOCK_DAY[quads - 1]:
        cost = _land_cost(me)
        if money_left >= cost + CASH_FLOOR and len(orders) < 10:
            orders.append(["BUY_LAND"])
            money_left -= cost

    # ── R5: feed reserve -- an animal unfed 2 days running escapes ──────────
    # Wheat the workers are already carrying counts: it left the shed but it is
    # still ours.  Ignoring it made this rule re-fire every single turn and buy
    # the same feed a dozen times a day.
    if fed_animals > 0 and day < total_days - 1:
        have = int(shed.get("WHEAT", 0))
        for inv in (private.get("inventories") or []):
            have += int(inv.get("WHEAT", 0))
        need = fed_animals * 3 - have
        room = SHED_CAP - shed_total - 5
        need = min(need, max(0, room), 45)
        # Only buy when meaningfully short (>= 1 day's feed).  Buying a single
        # unit to top up from need=1 wastes a market slot every other turn and
        # crowds out SELL orders.  The observation lags by one turn so need
        # oscillates 1↔0 constantly unless we require a real deficit.
        if need >= fed_animals and len(orders) < 10:
            c, _ = buy_cost("WHEAT", int(minv.get("WHEAT", 10000)), need)
            if money_left >= c:
                orders.append(["BUY_PRODUCT", "WHEAT", need])
                money_left -= c

    # ── R6: animals -- 8 COW then 6 SHEEP, only if a pasture is free ────────
    census = _animal_census(me, private)
    empty_pastures = sum(
        1 for row in (me.get("tiles") or []) for t in row
        if isinstance(t, dict) and t.get("kind") == "PASTURE" and not t.get("animal"))
    pending = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    slots = empty_pastures - pending
    if (day < total_days - 8 and slots > 0 and shed_total < SHED_CAP - 5
            and len(orders) < 10):
        for animal, target in (("COW", TARGET_COW), ("SHEEP", TARGET_SHEEP), ("GOOSE", TARGET_GOOSE)):
            if census[animal] >= target or slots <= 0:
                continue
            cost = ANIMAL_SPECS[animal]["cost"]
            want = min(target - census[animal], slots)
            afford = int((money_left - CASH_FLOOR) // cost)
            want = min(want, max(0, afford))
            if want > 0:
                orders.append(["BUY_ANIMAL", animal, want])
                money_left -= cost * want
                slots -= want
                break

    # ── R7: seeds for the tiles we are about to sow ─────────────────────────
    planted = _crop_census(me)
    harvest_n = len(scan.get('harvest_crop', [])) if scan else 0
    want_seeds = _seed_targets(day, total_days, planted, len(free_cells), harvest_n)
    for crop in ("MELON", "STRAWBERRY", "WHEAT"):
        if len(orders) >= 10:
            break
        deficit = want_seeds.get(crop, 0) - int(seeds.get(crop, 0))
        if deficit <= 0:
            continue
        unit = CROP_SPECS[crop]["seed"]
        afford = int((money_left - CASH_FLOOR) // unit)
        n = min(deficit, max(0, afford))
        if n > 0:
            orders.append(["BUY_SEED", crop, n])
            money_left -= unit * n

    return orders[:10]


# ── Task construction ─────────────────────────────────────────────────────────
# Tiers are strict: every tier-0 job is staffed before any tier-1 job.  Inside a
# tier the pairing is by pure distance, which is what keeps a worker harvesting
# its own corner instead of sprinting across the farm for a marginally hotter
# task -- distance/priority arithmetic in one flat scale was costing ~85% of all
# unit-turns to walking (top replays walk 46%).
TASK_TIER = {
    "service": 0,        # a starving animal escapes tonight -- never defer this
    "water": 0,          # dies tonight, or is in its yield window right now
    "harvest_crop": 1,   # banks value and frees the tile
    "place_animal": 1,   # an animal sitting in the shed earns nothing
    "service_soon": 1,   # routine upkeep: harvest / collect fertilizer / care
    "build_pasture": 2,
    "build_coop": 2,
    "plant": 2,          # a tile sown today compounds for the rest of the season
    # Spending a fertilizer on a producing strawberry doubles its next yield
    # (~+120-240) against the ~70-100 it would fetch on the market, so it beats
    # simply selling the stuff -- as long as a worker is already carrying some.
    "fertilize": 1,
    "water_soon": 3,     # already safe for today; catch it tomorrow if need be
    "weed": 4,
    "dropoff": 4,
}
N_TIERS = 5


def _build_tasks(scan, me, private, free_cells, day, total_days, hour=0):
    tasks = []
    # One "service" visit per occupied pasture bundles HARVEST + FEED +
    # COLLECT_FERTILIZER + CARE, so a worker pays the walk once and then works
    # the tile for up to four turns instead of being pulled away between each.
    for cell in scan["service"]:
        tasks.append(("service", cell))
    for cell in scan["service_soon"]:
        tasks.append(("service_soon", cell))
    for cell in scan["water"]:
        tasks.append(("water", cell))
    for cell in scan["water_soon"]:
        tasks.append(("water_soon", cell))
    for cell in scan["harvest_crop"]:
        tasks.append(("harvest_crop", cell))

    # Place animals waiting in the shed into empty pastures.
    shed = private.get("shed") or {}
    invs = private.get("inventories") or []
    unplaced = {}
    for a in ("COW", "SHEEP", "GOOSE"):
        n = int(shed.get(a, 0)) + sum(int(i.get(a, 0)) for i in invs)
        if n > 0:
            unplaced[a] = n
    if unplaced:
        for (cell, kind) in scan["structures_empty"]:
            if kind not in ("PASTURE", "COOP"):
                continue
            for a in list(unplaced):
                if unplaced[a] > 0:
                    req_kind = ANIMAL_SPECS[a]["structure"]
                    if kind == req_kind:
                        tasks.append(("place_animal", (a, cell)))
                        unplaced[a] -= 1
                        break

    # Build structures up to the blueprint cap -- never pave over crop land.
    have_pastures = _count_structures(me, "PASTURE")
    deficit_pasture = target_pastures(day) - have_pastures
    if deficit_pasture > 0 and day < total_days - 8:
        for cell in free_cells[:deficit_pasture]:
            tasks.append(("build_pasture", cell))
        free_cells = free_cells[deficit_pasture:]
        
    have_coops = _count_structures(me, "COOP")
    deficit_coop = target_coops(day) - have_coops
    if deficit_coop > 0 and day < total_days - 8:
        for cell in free_cells[:deficit_coop]:
            tasks.append(("build_coop", cell))
        free_cells = free_cells[deficit_coop:]

    # Sow the remaining free land.  A plant counts its planting day as unwatered
    # already, so anything sown too late to also be watered today dies tonight.
    # In the endgame (< 5 days left) we accept late-day plantings since the tile
    # otherwise just sits empty and we'll water it the same turn or next turn.
    plant_cutoff = 22 if (total_days - day) < 5 else 20
    if hour <= plant_cutoff:
        seeds = dict(private.get("seeds") or {})
        planted = _crop_census(me)
        for cell in free_cells:
            crop = _plant_choice(day, total_days, planted, seeds)
            if crop is None:
                break
            seeds[crop] = int(seeds.get(crop, 0)) - 1
            planted[crop] = planted.get(crop, 0) + 1
            tasks.append(("plant", (crop, cell)))

    for cell in scan["fertilize"]:
        tasks.append(("fertilize", cell))
    for cell in scan["weeds"]:
        tasks.append(("weed", cell))
    return tasks


def _task_cell(task):
    target = task[1] if len(task) > 1 else None
    if target is None:
        return None
    if (isinstance(target, tuple) and len(target) == 2
            and not isinstance(target[0], int)):
        return target[1]          # ("COW", cell) / ("WHEAT", cell)
    return target


def _assign_tasks(positions, tasks, invs, board, claims=None, feed_cells=None,
                  day=0, total_days=30):
    """Tier-by-tier greedy nearest-pair matching, with sticky claims.

    Recomputing assignments from scratch every turn made workers oscillate:
    a unit walking to a tile would be swapped onto another job the moment a
    colleague drifted closer, so nobody ever arrived.  A claim is therefore
    kept until the job it points at disappears from the task list.
    """
    assignment = {}
    taken = set()
    free = set(range(len(positions)))

    live = {}
    for t in tasks:
        live.setdefault((t[0], _task_cell(t)), t)

    # 1. Honour existing claims that still correspond to outstanding work.
    for ui, prev in (claims or {}).items():
        if ui not in free:
            continue
        key = (prev[0], _task_cell(prev))
        if key in live and key not in taken:
            assignment[ui] = live[key]
            taken.add(key)
            free.discard(ui)

    # 2. Fill the rest by a global score, strongly preferring d=0 for non-urgent tasks.
    # In the endgame (day >= 20), promote "plant" to Tier 1 so workers sow freed
    # melon/strawberry tiles instead of spending all turns on service_soon (CARE/
    # COLLECT_FERTILIZER).  Top players run 44-57 wheat tiles by day 27; we stall
    # at 12 because animal upkeep monopolises all 13 workers.
    endgame = day >= 20
    feed_cells = feed_cells or set()
    have_wheat = any(int((invs[ui] if ui < len(invs) else {}).get("WHEAT", 0)) > 0 for ui in free)
    pairs = []
    
    for ui in free:
        for t in tasks:
            key = (t[0], _task_cell(t))
            if key in taken:
                continue
            tier = TASK_TIER.get(t[0], 3)
            # Endgame: plant is now equal priority to service_soon so freed tiles
            # get sown before CARE/COLLECT_FERTILIZER steals every worker slot.
            if endgame and t[0] == "plant":
                tier = 1
            cell = _task_cell(t)
            if cell is None:
                continue
            inv = invs[ui] if ui < len(invs) else {}
            carrying = int(inv.get("WHEAT", 0)) > 0
            if t[0] == "fertilize" and int(inv.get("FERTILIZER", 0)) <= 0:
                continue
            hungry = t[0] in ("service", "service_soon") and cell in feed_cells
            if hungry and have_wheat and not carrying:
                continue
                
            d = manhattan(positions[ui], cell)
            if hungry and carrying:
                d -= 3
                
            # Score logic: Tier 0 is absolute priority.
            # If a worker is AT the tile (d=0), they should do the task there instead of walking,
            # UNLESS there's a Tier 0 emergency.
            score = tier * 1000 + d
            if d == 0 and tier > 0:
                score -= 1500  # Pulls it below the tier above it, but not below tier 0.
            
            pairs.append((score, ui, key, t))
            
    pairs.sort(key=lambda p: (p[0], p[1]))
    for score, ui, key, t in pairs:
        if ui not in free or key in taken:
            continue
        assignment[ui] = t
        taken.add(key)
        free.discard(ui)
    return assignment


def _unit_op(pos, task, private, unit_idx, board, me, shed_wheat):
    invs = private.get("inventories") or []
    inv = invs[unit_idx] if unit_idx < len(invs) else {}
    kind = task[0]
    target = task[1] if len(task) > 1 else None
    pos = tuple(pos)
    sheds = shed_adjacent_cells(board, me)
    shed_positions = [tuple(c) for c in sheds]

    def _go(cell, act):
        if pos == tuple(cell):
            return act
        st = step_toward(pos, cell)
        return [st] if st else act

    def _to_shed(act):
        if pos in shed_positions:
            return act
        tgt = min(sheds, key=lambda c: manhattan(pos, c))
        st = step_toward(pos, tgt)
        return [st] if st else act

    def _fetch(item, qty, then_cell, act):
        """Grab `item` from the shed, then head for the job."""
        if int(inv.get(item, 0)) > 0:
            return _go(then_cell, act)
        store = int((private.get("shed") or {}).get(item, 0))
        if store <= 0:
            return ["PASS"]
        return _to_shed(["PICKUP", item, min(store, qty)])

    if kind in ("service", "service_soon"):
        # Work the whole pasture in place: feed, harvest, collect, care.
        tiles = me.get("tiles") or []
        x, y = target
        tile = tiles[y][x] if 0 <= y < len(tiles) and 0 <= x < len(tiles[y]) else None
        if not isinstance(tile, dict):
            return ["PASS"]
        has_wheat = int(inv.get("WHEAT", 0)) > 0
        pend = _animal_pending(tile, has_wheat)
        if pend is None:
            # Only feeding is left and this worker is empty-handed.
            if not tile.get("fed_today"):
                return _fetch("WHEAT", 8, target, ["FEED"])
            return ["PASS"]
        return _go(target, [pend])
    if kind == "place_animal":
        animal, cell = target
        return _fetch(animal, 1, cell, ["PLACE", animal])
    if kind == "harvest_crop":
        return _go(target, ["HARVEST"])
    if kind in ("water", "water_soon"):
        return _go(target, ["WATER"])
    if kind == "build_pasture":
        return _go(target, ["BUILD_PASTURE"])
    if kind == "build_coop":
        return _go(target, ["BUILD_COOP"])
    if kind == "fertilize":
        return _go(target, ["FERTILIZE"])
    if kind == "plant":
        crop, cell = target
        return _go(cell, ["PLANT", crop])
    if kind == "weed":
        return _go(target, ["DIG"])
    if kind == "dropoff":
        return _to_shed(["DROP"])
    return ["PASS"]


# ── Main agent internal logic ─────────────────────────────────────────────────
# Sticky task claims, kept per seat so self-play in one process cannot cross
# them.  Reset whenever the step counter is not the expected successor (new
# episode, new day, replay) so stale claims never leak between games.
_CLAIM_STATE = {}


def _claims_for(player, step, n_units):
    st = _CLAIM_STATE.get(player)
    if (st is None or st.get("step") != step - 1
            or st.get("n_units") != n_units):
        return {}
    return st.get("claims") or {}


def _store_claims(player, step, n_units, claims):
    _CLAIM_STATE[player] = {"step": step, "n_units": n_units, "claims": claims}

def get_dt_task(act_id, pos, scan, free_cells):
    harv_crops = scan.get("harvest_crop", [])
    water = scan.get("water", []) + scan.get("water_soon", [])
    weeds = scan.get("weeds", [])
    feed_service = scan.get("service", []) + scan.get("service_soon", [])
    
    if act_id == 0:
        c = _nearest(pos, harv_crops)
        if c: return ("harvest_crop", c)
        c = _nearest(pos, feed_service)
        if c:
            if c in scan.get("service", []):
                return ("service", c)
            return ("service_soon", c)
    elif act_id == 1:
        c = _nearest(pos, water)
        if c:
            if c in scan.get("water", []):
                return ("water", c)
            return ("water_soon", c)
    elif act_id == 2:
        c = _nearest(pos, free_cells)
        if c: return ("plant", ("MELON", c))
    elif act_id == 3:
        c = _nearest(pos, free_cells)
        if c: return ("plant", ("CARROT", c))
    elif act_id == 4:
        c = _nearest(pos, free_cells)
        if c: return ("plant", ("WHEAT", c))
    elif act_id == 5:
        c = _nearest(pos, feed_service)
        if c:
            if c in scan.get("service", []):
                return ("service", c)
            return ("service_soon", c)
    elif act_id == 6:
        c = _nearest(pos, weeds)
        if c: return ("weed", c)
    return None


def _agent(obs, total_days=30):
    player = obs["player"]
    me = obs["farms"][player]
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    step = int(obs.get("step", day * 24 + hour))
    me = obs["farms"][player]
    private = obs.get("private") or {}
    tiles = me.get("tiles") or []
    board = len(tiles) or 10
    shed = private.get("shed") or {}
    invs = private.get("inventories") or [{}]

    scan = _scan(me, day, total_days)
    free_cells = _free_cells(me, board)
    # Claim land from the shed outwards.  Row-major order scattered pastures to
    # the far corners of the map, and feeding costs a shed round-trip per
    # animal, so a compact farm shortens the single most frequent walk on the
    # board.  Worth +17,521 (24/24, p=0.000) on its own -- walking, not
    # strategy, was the binding constraint.
    _sheds = shed_adjacent_cells(board, me)
    free_cells.sort(key=lambda c: min(manhattan(c, s) for s in _sheds))

    orders = _make_market_orders(obs, player, total_days, scan)
    tasks = _build_tasks(scan, me, private, free_cells, day, total_days, hour)

    positions = [tuple(me.get("farmer") or (4, 4))]
    positions += [tuple(h) for h in (me.get("hands") or [])]
    ops_out = [None] * len(positions)

    sheds = shed_adjacent_cells(board, me)
    shed_positions = [tuple(c) for c in sheds]
    shed_room = SHED_CAP - sum(int(v) for v in shed.values())
    shed_wheat = int(shed.get("WHEAT", 0))

    # Every worker respawns on a shed tile each morning, so the feed run is
    # free if we do it now.  Grabbing wheat later costs a round trip that used
    # to eat the first ten hours of the day.
    need_feed = len(scan["feed"])
    if hour <= 6 and need_feed > 0 and shed_wheat > 0:
        carried = sum(int((invs[i] if i < len(invs) else {}).get("WHEAT", 0))
                      for i in range(len(positions)))
        budget = min(shed_wheat, need_feed + 4 - carried)
        for i, pos in enumerate(positions):
            if budget <= 0:
                break
            if tuple(pos) not in shed_positions:
                continue
            inv = invs[i] if i < len(invs) else {}
            if int(inv.get("WHEAT", 0)) > 0:
                continue
            take = min(4, budget)
            ops_out[i] = ["PICKUP", "WHEAT", take]
            budget -= take

    # Produce stuck in a backpack cannot be sold, and every pack empties into
    # the shed at nightfall where anything past the 100-item cap is destroyed.
    # Lower thresholds so wool/milk/fertilizer from animals reaches the shed
    # same-day (intra-day sell), not overnight (losing 1 day of sell revenue).
    for i, pos in enumerate(positions):
        if ops_out[i] is not None:
            continue
        inv = invs[i] if i < len(invs) else {}
        carry = sum(int(v) for k, v in inv.items()
                    if k in PRODUCE_ITEMS and k != "WHEAT")
        if carry <= 0 or shed_room <= 2:
            continue
        if tuple(pos) in shed_positions:
            if carry >= 3:
                ops_out[i] = ["DROP"]
        elif carry >= 5:
            ops_out[i] = _unit_op(pos, ("dropoff", None), private, i,
                                  board, me, shed_wheat)

    # ── Task Assignment ──────────────────────────────────────────────────────

    free_units = [i for i in range(len(positions)) if ops_out[i] is None]
    assign_positions = [positions[i] for i in free_units]
    assign_invs = [invs[i] if i < len(invs) else {} for i in free_units]

    prev = _claims_for(player, step, len(positions))
    local_prev = {li: prev[gi] for li, gi in enumerate(free_units) if gi in prev}
    assignment = _assign_tasks(assign_positions, tasks, assign_invs, board, local_prev,
                               set(scan["feed"]), day=day, total_days=total_days)

    claims = {}
    for local_i, task in assignment.items():
        gi = free_units[local_i]
        claims[gi] = task
        ops_out[gi] = _unit_op(positions[gi], task, private, gi, board, me, shed_wheat)

    _store_claims(player, step, len(positions), claims)

    # Idle units carrying goods walk them back to the shed instead of passing.
    for i in range(len(ops_out)):
        if ops_out[i] is not None:
            continue
        inv = invs[i] if i < len(invs) else {}
        carry = sum(int(v) for k, v in inv.items() if k in PRODUCE_ITEMS)
        if carry > 0 and shed_room > 0:
            ops_out[i] = _unit_op(positions[i], ("dropoff", None), private, i,
                                  board, me, shed_wheat)
        else:
            ops_out[i] = ["PASS"]

    return {"farmer": ops_out[0], "hands": ops_out[1:], "market": orders}


def _to_dict(obj):
    """Recursively convert kaggle_environments Struct to plain dict."""
    try:
        import json
        return json.loads(json.dumps(obj))
    except Exception:
        return obj


def _total_days(config):
    try:
        steps = int(config["episodeSteps"] if isinstance(config, dict)
                    else getattr(config, "episodeSteps"))
        per = int(config["turnsPerDay"] if isinstance(config, dict)
                  else getattr(config, "turnsPerDay"))
        if steps > 0 and per > 0:
            return max(1, steps // per)
    except Exception:
        pass
    return 30


# ── Decision Transformer State and Actions Helper ─────────────────────────────
DT_MODEL = None
STATE_HISTORY = []
ACTION_HISTORY = []
RETURN_HISTORY = []

OBS_DIM = 107
CROPS    = ["WHEAT","CARROT","TOMATO","STRAWBERRY","MELON"]
ANIMALS  = ["GOOSE","COW","SHEEP"]
PRODUCTS = ["WHEAT","CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER"]
BASE_PRICES = [25, 35, 60, 120, 250, 50, 160, 200, 100]
SHOPS = ["BAKERY","PIZZA_SHOP","BRUNCH_SPOT","YARN_STORE","ICE_CREAM_SHOP",
         "PET_CAFE","SMOOTHIE_SHOP","FARMERS_MARKET"]

def _norm_shop(s):
    return str(s).strip().upper().replace(" ","_").replace("-","_")

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
                    cv[ci*4+1] += int(not t.get("watered_today",False))
                    cv[ci*4+2] += int(t.get("yield_units",0) > 0)
                    cv[ci*4+3] += max(0, day - t.get("planted_day",day)) / 30.0
            elif k in ("COOP","PASTURE"):
                a = t.get("animal")
                if a in ANIMALS:
                    ai = ANIMALS.index(a)
                    av[ai*3]   += 1
                    av[ai*3+1] += int(not t.get("fed_today",False))
                    av[ai*3+2] += int(t.get("yield_units",0) > 0)
    return cv, av

def obs_to_vec(obs, player):
    import numpy as np
    v = np.zeros(OBS_DIM, np.float32)
    me  = obs["farms"][player]
    opp = obs["farms"][1-player]
    day  = obs.get("day",0)
    hour = obs.get("hour",0)
    priv = obs.get("private",{}) or {}
    mkt  = obs.get("market",{}) or {}
    town = obs.get("town",{}) or {}

    i = 0
    v[i] = day / 30.0;   i+=1
    v[i] = hour / 24.0;  i+=1
    v[i] = min(me.get("money",0) / 50000.0, 1.0); i+=1
    v[i] = len(me.get("unlocked_quadrants",["NW"])) / 4.0; i+=1

    tiles = me.get("tiles") or []
    cv, av = _farm_summary(tiles, day)
    v[i:i+20] = cv / 10.0;  i+=20
    v[i:i+9]  = av / 10.0;  i+=9

    fx, fy = me.get("farmer", [4,4])
    v[i] = fx/10.0; v[i+1] = fy/10.0; i+=2

    minv = mkt.get("inventory",{}) or {}
    mprc = mkt.get("prices",{}) or {}
    for j,p in enumerate(PRODUCTS):
        v[i+j] = min(mprc.get(p, BASE_PRICES[j]) / (BASE_PRICES[j]*2), 1.0)
    i+=9
    for j,p in enumerate(PRODUCTS):
        v[i+j] = min(minv.get(p,10000) / 10000.0, 1.0)
    i+=9

    shed = priv.get("shed",{}) or {}
    seeds = priv.get("seeds",{}) or {}
    for j,p in enumerate(PRODUCTS):
        v[i+j] = min(shed.get(p,0) / 20.0, 1.0)
    i+=9
    for j,a in enumerate(ANIMALS):
        v[i+j] = min(shed.get(a,0) / 5.0, 1.0)
    i+=3

    for j,c in enumerate(CROPS):
        v[i+j] = min(seeds.get(c,0) / 10.0, 1.0)
    i+=5

    shops_u = {_norm_shop(s) for s in (town.get("unlocked_shops") or [])}
    for j,s in enumerate(SHOPS):
        v[i+j] = float(s in shops_u)
    i+=8

    opp_tiles = opp.get("tiles") or []
    ocv, oav = _farm_summary(opp_tiles, day)
    v[i:i+20] = ocv / 10.0; i+=20
    v[i:i+9]  = oav / 10.0; i+=9

    return v

def _step_toward(pos, target):
    x,y = pos; tx,ty = target
    dx,dy = tx-x, ty-y
    if dx==0 and dy==0: return None
    if abs(dx)>=abs(dy): return "EAST" if dx>0 else "WEST"
    return "SOUTH" if dy>0 else "NORTH"

def _nearest(pos, cells):
    if not cells: return None
    return min(cells, key=lambda c: abs(c[0]-pos[0])+abs(c[1]-pos[1]))

def macro_to_farmer_op(action_id, obs, player, seeds_override=None):
    me    = obs["farms"][player]
    priv  = obs.get("private",{}) or {}
    seeds = seeds_override or priv.get("seeds",{}) or {}
    tiles = me.get("tiles") or []
    n     = len(tiles)
    pos   = tuple(me.get("farmer",[4,4]))
    day   = obs.get("day",0)

    harv, water, empty, weeds, feed = [],[],[],[],[]
    for y in range(n):
        for x in range(n):
            t = tiles[y][x]
            if t=="LOCKED": continue
            if t is None: empty.append((x,y)); continue
            if not isinstance(t,dict): continue
            k = t.get("kind")
            if k=="PLANT":
                if t.get("yield_units",0)>0: harv.append((x,y))
                if not t.get("watered_today",False): water.append((x,y))
            elif k=="WEED": weeds.append((x,y))
            elif k in ("COOP","PASTURE") and t.get("animal"):
                if not t.get("fed_today",False): feed.append((x,y))
                if t.get("yield_units",0)>0: harv.append((x,y))

    def _go(cells, act):
        t = _nearest(pos, cells)
        if t is None: return ["PASS"]
        if tuple(pos)==tuple(t): return [act]
        st = _step_toward(pos,t)
        return [st] if st else [act]

    crop_map = {2:"MELON",3:"CARROT",4:"WHEAT"}
    if action_id == 0: return _go(harv, "HARVEST")
    if action_id == 1: return _go(water, "WATER")
    if action_id in (2,3,4):
        crop = crop_map[action_id]
        if seeds.get(crop,0)>0 and day<=26:
            return _go(empty, f"__PLANT__{crop}")
        return ["PASS"]
    if action_id == 5: return _go(feed, "FEED")
    if action_id == 6: return _go(weeds, "DIG")
    return ["PASS"]

def resolve_farmer_op(raw_op, obs, player, priv):
    if not raw_op or raw_op[0]=="PASS": return ["PASS"]
    op = raw_op[0]
    if op.startswith("__PLANT__"):
        crop = op[9:]
        me = obs["farms"][player]
        tiles = me.get("tiles") or []
        pos = tuple(me.get("farmer",[4,4]))
        x,y = pos
        t = tiles[y][x] if 0<=y<len(tiles) and 0<=x<len(tiles[y]) else "LOCKED"
        if t is None:
            return ["PLANT", crop]
        empty=[]
        for ry in range(len(tiles)):
            for rx in range(len(tiles[ry])):
                if tiles[ry][rx] is None: empty.append((rx,ry))
        tgt = _nearest(pos, empty)
        if tgt is None: return ["PASS"]
        if tuple(pos)==tgt: return ["PLANT", crop]
        st = _step_toward(pos, tgt)
        return [st] if st else ["PASS"]
    return raw_op


# ── Decision Transformer Inference (NumPy) ────────────────────────────────────
class DecisionTransformer:
    def __init__(self, weights_path):
        self.loaded = False
        try:
            import numpy as np
            import os
            if os.path.exists(weights_path):
                self._w = dict(np.load(weights_path, allow_pickle=False))
                self.loaded = True
        except Exception:
            pass
            
    def _linear(self, x, weight_key, bias_key=None):
        import numpy as np
        out = x @ self._w[weight_key].T
        if bias_key and bias_key in self._w:
            out += self._w[bias_key]
        return out
        
    def _layer_norm(self, x, w_key, b_key, eps=1e-5):
        import numpy as np
        mean = np.mean(x, axis=-1, keepdims=True)
        var = np.var(x, axis=-1, keepdims=True)
        return self._w[w_key] * (x - mean) / np.sqrt(var + eps) + self._w[b_key]

    def _self_attention(self, x, layer_idx, num_heads=4):
        import numpy as np
        seq_len, embed_dim = x.shape
        head_dim = embed_dim // num_heads
        
        # Q, K, V projections
        c_attn = self._linear(x, f'blocks.{layer_idx}.attn.c_attn.weight', f'blocks.{layer_idx}.attn.c_attn.bias')
        q, k, v = np.split(c_attn, 3, axis=-1)
        
        # Reshape to (num_heads, seq_len, head_dim)
        q = q.reshape(seq_len, num_heads, head_dim).transpose(1, 0, 2)
        k = k.reshape(seq_len, num_heads, head_dim).transpose(1, 0, 2)
        v = v.reshape(seq_len, num_heads, head_dim).transpose(1, 0, 2)
        
        # Causal mask
        mask = np.tril(np.ones((seq_len, seq_len)))
        mask = mask.reshape(1, seq_len, seq_len)
        
        # Attention scores
        scores = q @ k.transpose(0, 2, 1) / np.sqrt(head_dim)
        scores = np.where(mask == 1, scores, -1e4)
        
        # Softmax
        scores = scores - np.max(scores, axis=-1, keepdims=True)
        probs = np.exp(scores) / np.sum(np.exp(scores), axis=-1, keepdims=True)
        
        # Weighted sum
        out = (probs @ v).transpose(1, 0, 2).reshape(seq_len, embed_dim)
        return self._linear(out, f'blocks.{layer_idx}.attn.c_proj.weight', f'blocks.{layer_idx}.attn.c_proj.bias')

    def predict(self, states, actions, returns_to_go, timesteps):
        """
        Forward pass for causal transformer.
        Expects sequences of shape (K, dim). Returns logits for next action.
        """
        if not self.loaded:
            return 7 # fallback to PASS
            
        import numpy as np
        
        # Embeddings
        s_emb = self._linear(states, 'embed_state.weight', 'embed_state.bias')
        a_emb = self._linear(actions, 'embed_action.weight', 'embed_action.bias')
        r_emb = self._linear(returns_to_go, 'embed_return.weight', 'embed_return.bias')
        
        # Interleave (R, s, a) 
        # For prediction, we only have R and s for the current step
        # Assuming sequence length K
        K = states.shape[0]
        embed_dim = s_emb.shape[-1]
        
        # Construct token sequence
        seq = np.zeros((K * 3, embed_dim))
        seq[0::3] = r_emb
        seq[1::3] = s_emb
        seq[2::3] = a_emb # The last action is a dummy, but we only care about the state representation
        
        # Positional embedding
        pos_emb = self._w['embed_timestep.weight'][timesteps]
        pos_emb_interleaved = np.repeat(pos_emb, 3, axis=0)
        
        x = seq + pos_emb_interleaved
        x = self._layer_norm(x, 'embed_ln.weight', 'embed_ln.bias')
        
        # Transformer blocks
        num_layers = sum(1 for k in self._w.keys() if k.endswith('.attn.c_attn.weight'))
        for i in range(num_layers):
            # Attention
            h = self._layer_norm(x, f'blocks.{i}.ln_1.weight', f'blocks.{i}.ln_1.bias')
            x = x + self._self_attention(h, i)
            # MLP
            h = self._layer_norm(x, f'blocks.{i}.ln_2.weight', f'blocks.{i}.ln_2.bias')
            mlp_h = self._linear(h, f'blocks.{i}.mlp.c_fc.weight', f'blocks.{i}.mlp.c_fc.bias')
            mlp_h = mlp_h * (mlp_h > 0) # ReLU/GELU approx
            x = x + self._linear(mlp_h, f'blocks.{i}.mlp.c_proj.weight', f'blocks.{i}.mlp.c_proj.bias')
            
        x = self._layer_norm(x, 'ln_f.weight', 'ln_f.bias')
        
        # Predict action from the state token (index 1::3)
        state_tokens = x[1::3]
        logits = self._linear(state_tokens[-1:], 'predict_action.weight', 'predict_action.bias')
        return int(np.argmax(logits[0]))



# ── Entrypoint function (MUST be the last top-level function defined) ────────
def agent(obs, config=None):
    try:
        return _agent(_to_dict(obs), _total_days(config))
    except Exception:
        import traceback, sys
        traceback.print_exc(file=sys.stderr)
        return {"farmer": ["PASS"], "hands": [], "market": []}
