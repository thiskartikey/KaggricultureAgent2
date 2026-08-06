"""Kaggriculture agent v3 — RL policy (PPO) with v2 heuristic fallback.

Submission: kaggle competitions submit kaggriculture -f submission.tar.gz -m "v3 RL"
Bundle:     tar -czf submission.tar.gz main.py rl_inference.py rl_weights.npz
"""
import math, os

# ── try to load trained RL weights (optional; heuristic runs without them) ──
_RL_POLICY = None
try:
    import numpy as np
    from rl_inference import RLPolicy
    from env_wrapper import obs_to_vec, macro_to_farmer_op, resolve_farmer_op, _count_animals as _cnt_animals
    _WEIGHTS = os.path.join(os.path.dirname(__file__), "rl_weights.npz")
    _RL_POLICY = RLPolicy(_WEIGHTS)
    if not _RL_POLICY.loaded:
        _RL_POLICY = None
except Exception:
    _RL_POLICY = None

# ══════════════════════════════════════════════════════════════════════════════
# v2 heuristic modules (used as market/hands fallback and when RL not loaded)
# ══════════════════════════════════════════════════════════════════════════════
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
    "ICE_CREAM_SHOP": {"STRAWBERRY": 1, "MILK": 1, "WHEAT": 1},
    "PET_CAFE":       {"CARROT": 2},
    "SMOOTHIE_SHOP":  {"STRAWBERRY": 1, "MILK": 1},
    "FARMERS_MARKET": {"WHEAT": 1, "CARROT": 1, "TOMATO": 1, "STRAWBERRY": 1},
}
CENTER_PRODUCTS = [p for p in PRODUCTS if p != "FERTILIZER"]

def _norm_shop(name):
    return str(name).strip().upper().replace(" ","_").replace("-","_")

def town_center_mult(day):
    return 4 if day >= 20 else (2 if day >= 10 else 1)

def town_drain_per_day(unlocked_shops, day, turns_per_day=24, shop_interval=4, center_interval=12):
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

_SELL_ORDER = ["MELON","WOOL","MILK","STRAWBERRY","TOMATO","EGG","CARROT","FERTILIZER","WHEAT"]

def plan_sells(shed, market_inv, day, hour, total_days=30, hold=None, max_orders=10, shed_cap=100):
    hold = hold or {}
    load = sum(v for k, v in shed.items() if k not in ("GOOSE","COW","SHEEP"))
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
        if p in ("MELON","WOOL","MILK","STRAWBERRY") and n < 2 and avail >= 2 \
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

def read_opponent(opp_farm, day):
    flood = {}
    for row in opp_farm.get("tiles") or []:
        for t in row:
            if not isinstance(t, dict):
                continue
            if t.get("kind") == "PLANT":
                c = t.get("crop"); s = CROP_SPECS.get(c)
                if s:
                    age = day - t.get("planted_day", day)
                    if max(1, s["maxday"] - age) <= 7:
                        flood[c] = flood.get(c, 0.0) + s["peak"] / 7.0
            elif t.get("kind") in ("COOP","PASTURE") and t.get("animal"):
                sp = ANIMAL_SPECS.get(t["animal"])
                if sp:
                    pr = sp["product"]
                    flood[pr] = flood.get(pr, 0.0) + 1.0 / sp["interval"]
    return flood

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
    picks, spend, counts, committed = [], 0.0, {}, 0.0
    for _ in range(int(free_tiles)):
        best, best_score = None, 0.0
        days_left = total_days - day
        for c, s in CROP_SPECS.items():
            if days_left <= s["first"] + 1 or money - spend < s["seed"]:
                continue
            upd = s["peak"] / float(s["occ"])
            total_units = planned.get(c, 0) + upd * days_left + opp_flood.get(c, 0) * days_left
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
            total_units = planned.get(pr, 0) + upd * days_left + opp_flood.get(pr, 0) * days_left
            p = _exp_unit_price(pr, market_inv, total_units, drain.get(pr, 0), days_left)
            feed_cost = price("WHEAT", market_inv.get("WHEAT", 10000))
            # every surviving animal yields 1 fertilizer/day for 1 COLLECT action
            fert_p = _exp_unit_price("FERTILIZER", market_inv,
                                     planned.get("FERTILIZER", 0) + days_left,
                                     drain.get("FERTILIZER", 0), days_left)
            rev = upd * p + fert_p - feed_cost - s["cost"] / float(days_left)
            apd = 1.0 + upd + 1.0 + 0.2   # feed + harvest + collect_fert + care
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

_FIB = [1, 1]
while len(_FIB) < 40:
    _FIB.append(_FIB[-1] + _FIB[-2])

def step_toward(pos, target):
    x,y=pos; tx,ty=target; dx,dy=tx-x,ty-y
    if dx==0 and dy==0: return None
    if abs(dx)>=abs(dy): return "EAST" if dx>0 else "WEST"
    return "SOUTH" if dy>0 else "NORTH"

def manhattan(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])

def shed_adjacent_cells(board_size=10, me=None):
    h=board_size//2
    cells = [(h-1,h-1),(h,h-1),(h-1,h),(h,h)]
    if me is None: return cells
    quads = me.get("unlocked_quadrants") or ["NW"]
    avail = []
    if "NW" in quads: avail.append((h-1, h-1))
    if "NE" in quads: avail.append((h, h-1))
    if "SW" in quads: avail.append((h-1, h))
    if "SE" in quads: avail.append((h, h))
    return avail

_STICKY={}   # assignment key -> {unit_index: target cell} from the previous turn

def assign_tasks(unit_positions, tasks, key="h"):
    """Greedy nearest-unit assignment, biased to keep last turn's targets.

    Assignments are recomputed every hour, so without stickiness a unit part-way
    to a tile gets re-aimed at another and oscillates instead of arriving. The
    bias is small enough that a genuinely closer unit still wins the task.
    """
    prev=_STICKY.get(key) or {}
    tasks=sorted(enumerate(tasks),key=lambda it:-it[1][2]); free=set(range(len(unit_positions))); out={}
    for _,(cell,ops,_pr) in tasks:
        if not free: break
        best_u,best_d=None,10**9
        for u in free:
            d=manhattan(unit_positions[u],cell)
            if prev.get(u)==tuple(cell): d-=6
            if d<best_d: best_u,best_d=u,d
        free.discard(best_u); out[best_u]=(cell,ops)
    _STICKY[key]={u:tuple(c) for u,(c,_o) in out.items()}
    return out

SELL_PRODUCE=["MELON","WOOL","MILK","STRAWBERRY","TOMATO","EGG","CARROT","WHEAT","FERTILIZER"]
ANIMAL_ITEMS=("GOOSE","COW","SHEEP")

def _my_pipeline(me, day, total_days):
    planned={}
    for row in me.get("tiles") or []:
        for t in row:
            if not isinstance(t,dict): continue
            if t.get("kind")=="PLANT":
                c=t.get("crop"); s=CROP_SPECS.get(c)
                if s: planned[c]=planned.get(c,0)+max(s["peak"],t.get("yield_units",0))
            elif t.get("kind") in ("COOP","PASTURE") and t.get("animal"):
                sp=ANIMAL_SPECS.get(t["animal"])
                if sp:
                    pr=sp["product"]
                    planned[pr]=planned.get(pr,0)+(total_days-day)/float(sp["interval"])
    return planned

def _free_cells(me, board_size):
    cells=[]; tiles=me.get("tiles") or []
    for y in range(len(tiles)):
        for x in range(len(tiles[y])):
            if tiles[y][x] is None: cells.append((x,y))
    h=board_size//2; cells.sort(key=lambda c:manhattan(c,(h,h))); return cells

def _scan(me, day):
    out=dict(water=[],harvest_crop=[],harvest_urgent=[],feed=[],care=[],
             collect=[],weeds=[],structures_empty=[],harvest_animal=[],fertilize=[])
    for y,row in enumerate(me.get("tiles") or []):
        for x,t in enumerate(row):
            if not isinstance(t,dict): continue
            k=t.get("kind")
            if k=="PLANT":
                c,s=t.get("crop"),CROP_SPECS.get(t.get("crop"))
                if not s: continue
                age=day-t.get("planted_day",day); onetime=c in ("WHEAT","CARROT","MELON")
                if not t.get("watered_today") and age<s["occ"]:
                    pr=120 if t.get("consecutive_unwatered",0)>=1 else 100
                    out["water"].append(((x,y),pr))
                if t.get("yield_units",0)>0:
                    if onetime:
                        if age>s["maxday"]: out["harvest_urgent"].append((x,y))
                        elif age>=s["maxday"]: out["harvest_crop"].append((x,y))
                    else: out["harvest_crop"].append((x,y))
                if t.get("fertilized_until_day", -1) < day and age < s["occ"] and t.get("yield_units", 0) == 0:
                    out["fertilize"].append(((x,y), 88 if c == "WHEAT" else 50))
            elif k=="WEED": out["weeds"].append((x,y))
            elif k in ("COOP","PASTURE"):
                if t.get("animal"):
                    if not t.get("fed_today"): out["feed"].append(((x,y),115 if t.get("consecutive_unfed",0)>=1 else 105))
                    if t.get("yield_units",0)>0: out["harvest_animal"].append((x,y))
                    if t.get("fertilizer_available"): out["collect"].append((x,y))
                    if t.get("fed_today") and not t.get("cared_today"): out["care"].append((x,y))
                else: out["structures_empty"].append(((x,y),t.get("kind")))
    return out

def _count_animals(me, private):
    n=0
    for row in me.get("tiles") or []:
        for t in row:
            if isinstance(t,dict) and t.get("kind") in ("COOP","PASTURE") and t.get("animal"): n+=1
    shed = private.get("shed") or {}
    invs = private.get("inventories") or []
    for a in ("GOOSE", "COW", "SHEEP"):
        n += int(shed.get(a, 0))
        for iv in invs:
            n += int((iv or {}).get(a, 0))
    return n

def build_tasks(scan, me, private, picks, free_cells, day, hour, board_size, total_days):
    tasks=[]
    for cell,pr in scan["water"]: tasks.append((cell,["WATER"],pr))
    # Only assign FEED tasks if we actually have WHEAT
    total_wheat = int((private.get("shed") or {}).get("WHEAT", 0))
    for iv in (private.get("inventories") or []):
        total_wheat += int((iv or {}).get("WHEAT", 0))
    for cell,pr in scan["feed"]:
        if total_wheat > 0:
            tasks.append((cell,["FEED"],pr))
            total_wheat -= 1
    for cell in scan["harvest_urgent"]: tasks.append((cell,["HARVEST"],95))
    for cell in scan["harvest_crop"]: tasks.append((cell,["HARVEST"],80))
    for cell in scan["harvest_animal"]: tasks.append((cell,["HARVEST"],75))
    shed=private.get("shed") or {}
    placeable=[(cell,kind) for cell,kind in scan["structures_empty"]]
    invs = private.get("inventories") or []
    for a in ANIMAL_ITEMS:
        want=ANIMAL_SPECS[a]["structure"]
        n=int(shed.get(a,0))
        for inv in invs:
            n += int((inv or {}).get(a, 0))
        for cell,kind in placeable:
            if n<=0 or kind!=want: continue
            tasks.append((cell,["__PLACE__",a],125)); n-=1
    seeds=private.get("seeds") or {}; ci=0
    for kind,name in picks:
        if ci>=len(free_cells): break
        if kind=="PLANT" and seeds.get(name,0)>0:
            tasks.append((free_cells[ci],["PLANT",name],70))
            seeds=dict(seeds); seeds[name]-=1; ci+=1
        elif kind=="ANIMAL":
            tasks.append((free_cells[ci],[ANIMAL_SPECS[name]["build"]],65)); ci+=1
    for cell in scan["collect"]: tasks.append((cell,["COLLECT_FERTILIZER"],78))
    if day<total_days-2:
        for cell in scan["weeds"]: tasks.append((cell,["DIG"],40))
    for cell in scan["care"]: tasks.append((cell,["CARE"],72))
    # Build PASTUREs on free tiles (top-player strategy: expand animal housing)
    n_pastures = sum(1 for row in (me.get("tiles") or []) for t in row if isinstance(t,dict) and t.get("kind") in ("COOP","PASTURE"))
    if day < total_days - 10:
        target_pastures = 6 if day < 5 else 14
        needed = target_pastures - n_pastures
        if needed > 0:
            for cell in free_cells[:needed]:
                tasks.append((cell, ["BUILD_PASTURE"], 88))
    n_fert = int((private.get("shed") or {}).get("FERTILIZER", 0))
    for iv in (private.get("inventories") or []):
        n_fert += int((iv or {}).get("FERTILIZER", 0))
    fert_tasks = []
    for cell, pr in scan.get("fertilize", []):
        fert_tasks.append((cell, ["__FERTILIZE__"], pr))
    # Add up to n_fert fertilize tasks (so we don't spam if we have no fertilizer)
    fert_tasks = sorted(fert_tasks, key=lambda x: -x[2])
    tasks.extend(fert_tasks[:max(n_fert, 2)])
    return tasks

def _unit_op(pos, task, private, unit_idx, board_size, feed_wheat_needed, me):
    invs=private.get("inventories") or []; inv=invs[unit_idx] if unit_idx<len(invs) else {}
    cell,ops=task; op=ops[0]
    if op=="FEED" and int((inv or {}).get("WHEAT",0))<=0:
        sheds=shed_adjacent_cells(board_size, me)
        if tuple(pos) in [tuple(c) for c in sheds]:
            shed_wheat = int((private.get("shed") or {}).get("WHEAT",0))
            if shed_wheat <= 0: return ["PASS"]
            n=max(1,min(shed_wheat,feed_wheat_needed))
            return ["PICKUP","WHEAT",n]
        tgt=min(sheds,key=lambda c:manhattan(pos,c)); st=step_toward(pos,tgt)
        return [st] if st else ["PASS"]
    if op=="__FERTILIZE__":
        if int((inv or {}).get("FERTILIZER",0))>0:
            if tuple(pos)==tuple(cell): return ["FERTILIZE"]
            st=step_toward(pos,cell); return [st] if st else ["FERTILIZE"]
        sheds=shed_adjacent_cells(board_size, me)
        if tuple(pos) in [tuple(c) for c in sheds]:
            n = int((private.get("shed") or {}).get("FERTILIZER",0))
            return ["PICKUP","FERTILIZER",min(n, 5)] if n>0 else ["PASS"]
        tgt=min(sheds,key=lambda c:manhattan(pos,c)); st=step_toward(pos,tgt)
        return [st] if st else ["PASS"]
    if op=="__PLACE__":
        a=ops[1]
        if int((inv or {}).get(a,0))>0:
            if tuple(pos)==tuple(cell): return ["PLACE",a]
            st=step_toward(pos,cell); return [st] if st else ["PLACE",a]
        sheds=shed_adjacent_cells(board_size, me)
        if tuple(pos) in [tuple(c) for c in sheds]:
            return ["PICKUP",a,1] if int((private.get("shed") or {}).get(a,0))>0 else ["PASS"]
        tgt=min(sheds,key=lambda c:manhattan(pos,c)); st=step_toward(pos,tgt)
        return [st] if st else ["PASS"]
    if tuple(pos)==tuple(cell): return list(ops)
    st=step_toward(pos,cell); return [st] if st else list(ops)

def _drop_task_needed(inv):
    return sum(int(v) for k,v in (inv or {}).items())>=25

def _pasture_choice(market_inv):
    m=price("MILK",market_inv.get("MILK",10000))*0.5
    w=price("WOOL",market_inv.get("WOOL",10000))/3.0
    return "COW" if m>=w else "SHEEP"

def _land_cost(me):
    n=len(me.get("unlocked_quadrants") or ["NW"])-1
    costs=[1000,2000,3000]
    return costs[n] if n<len(costs) else 999999

def _land_order(me, free_count, day, money, total_days):
    q=len(me.get("unlocked_quadrants") or ["NW"])
    if q>=4: return None
    cost=1000*(2**(q-1))
    if free_count<12 and day<total_days-6 and money>cost+400: return ["BUY_LAND"]
    return None

def _desired_hands(scan, free_cells, picks, day, total_days):
    if day>=total_days-1: return 0
    work=len(scan["water"])+len(scan["feed"])+len(scan["harvest_crop"]) \
        +len(scan["harvest_animal"])+min(len(picks),len(free_cells))+len(scan["weeds"])
    return max(0, min(5, work//7))

# ── market order builder (used by both RL and heuristic paths) ───────────────
def _build_market_orders(obs, picks, scan, total_days=30):
    """Top-player strategy (#1 Mohit Rao): hire hands, WHEAT/MELON blitz day 0, buy wheat in bulk."""
    player=obs["player"]; me=obs["farms"][player]; priv=obs.get("private") or {}
    market=obs.get("market") or {}; minv=market.get("inventory") or {}
    shed=priv.get("shed") or {}; seeds=priv.get("seeds") or {}
    invs=priv.get("inventories") or [{}]
    day=obs.get("day",0); hour=obs.get("hour",0); money=me.get("money",0)
    animals=_count_animals(me, priv)
    hires=int(me.get("hires_today",0))
    quadrants=me.get("unlocked_quadrants") or ["NW"]
    free_cells=_free_cells(me,len(me.get("tiles") or []))

    orders=[]; hold={"WHEAT": animals * (total_days - day)}
    orders+=plan_sells(shed,minv,day,hour,total_days,hold); money_l=money

    # 1. Aggressive wheat buy for animal feed (buy in bulk)
    if animals and int(shed.get("WHEAT",0)) < animals*3 and day < total_days-1:
        # Buy 40 units at a time if we have enough money, else try smaller
        for batch in [80, 40, 20, 10, 5, 2]:
            c,_=buy_cost("WHEAT",minv.get("WHEAT",10000),batch)
            if money_l >= c:
                orders.append(["BUY_PRODUCT","WHEAT",batch]); money_l-=c
                break

    # 2. Hire hands aggressively (top players hire 5-14 per day)
    if hour<=1:
        n_pastures=sum(1 for row in (me.get("tiles") or []) for t in row
                      if isinstance(t,dict) and t.get("kind") in ("COOP","PASTURE"))
        total_hands = len(me.get("hands") or [])
        # Labour is cheap: HIRE costs fib(n) per extra hand that day, so a crew of
        # 10 is only ~143 total and 14 is ~986. Hands vanish nightly, so re-hire a
        # full crew every day -- idle tiles and unharvested produce cost far more.
        target_hands = 5 if day == 0 else 14
        
        hires_needed = target_hands - total_hands
        if hires_needed > 0:
            target_hires_today = min(hires_needed, 14)
            while hires<target_hires_today:
                c=_FIB[min(hires,len(_FIB)-1)]
                # Keep only a token reserve. A large one blocks hiring entirely on
                # low-cash days, which strands the whole farm for lack of labour.
                min_reserve = 60
                if money_l > c + min_reserve: orders.append(["HIRE"]); money_l-=c; hires+=1
                else: break

    # 3. Day 0 blitz: MELON seeds + WHEAT seeds + SHEEP + COW
    if day==0 and hour==0:
        # Budget is 3000. Animals starve (and die by day 3) unless we also buy
        # their feed up front, so reserve cash for WHEAT before livestock.
        # MELON funds the mid-game (harvests ~D10), but do NOT spend down to
        # near-zero for a bigger blitz: wages go unpaid, the crew dies, and the
        # farm stalls for 15 days. 6 melons + a cash buffer beats 12 + no buffer.
        orders.append(["BUY_SEED","MELON",6]); money_l-=6*CROP_SPECS["MELON"]["seed"]
        orders.append(["BUY_SEED","WHEAT",7]); money_l-=7*CROP_SPECS["WHEAT"]["seed"]
        orders.append(["BUY_ANIMAL","COW",2]); money_l-=2*ANIMAL_SPECS["COW"]["cost"]
        orders.append(["BUY_ANIMAL","SHEEP",1]); money_l-=ANIMAL_SPECS["SHEEP"]["cost"]
        c,_=buy_cost("WHEAT",minv.get("WHEAT",10000),20)
        orders.append(["BUY_PRODUCT","WHEAT",20]); money_l-=c

    # 4. Fill empty structures with animals every day
    min_reserve = 300 if (day > 2 and hires >= 4) else 0
    if day>0 and hour<=2 and day<total_days-5:
        pastures = sum(1 for row in (me.get("tiles") or []) for t in row if isinstance(t,dict) and t.get("kind")=="PASTURE")
        coops = sum(1 for row in (me.get("tiles") or []) for t in row if isinstance(t,dict) and t.get("kind")=="COOP")
        owned_cows_sheep = 0; owned_geese = 0
        for row in (me.get("tiles") or []):
            for t in row:
                if isinstance(t,dict) and t.get("animal"):
                    a = t.get("animal")
                    if a in ("COW","SHEEP"): owned_cows_sheep += 1
                    elif a == "GOOSE": owned_geese += 1
        for a in ("COW", "SHEEP"):
            owned_cows_sheep += int(shed.get(a, 0)) + sum(int((iv or {}).get(a,0)) for iv in invs)
        owned_geese += int(shed.get("GOOSE", 0)) + sum(int((iv or {}).get("GOOSE",0)) for iv in invs)
        
        pasture_shortage = pastures - owned_cows_sheep
        coop_shortage = coops - owned_geese
        
        buy_count = 0
        while pasture_shortage > 0 and buy_count < 4:
            milk_p=price("MILK",minv.get("MILK",10000))*0.5
            wool_p=price("WOOL",minv.get("WOOL",10000))/3.0
            a="SHEEP" if wool_p>milk_p else "COW"
            c=ANIMAL_SPECS[a]["cost"]
            if money_l > c + min_reserve:
                orders.append(["BUY_ANIMAL",a,1]); money_l-=c
                pasture_shortage -= 1
                buy_count += 1
            else: break
            
        while coop_shortage > 0 and buy_count < 4:
            c=ANIMAL_SPECS["GOOSE"]["cost"]
            if money_l > c + min_reserve:
                orders.append(["BUY_ANIMAL","GOOSE",1]); money_l-=c
                coop_shortage -= 1
                buy_count += 1
            else: break

    # 5. Buy seeds when running low. Scaling this to fill every idle tile was
    #    tested with both WHEAT and MELON and lost every time: the cash leaves
    #    the wage/feed budget faster than the extra tiles return it.
    if day<total_days-5 and free_cells and int(seeds.get("WHEAT",0))<3:
        n=min(7, len(free_cells))
        if money_l>n*10+300: orders.append(["BUY_SEED","WHEAT",n]); money_l-=n*10
    if day<total_days-10 and free_cells and int(seeds.get("MELON",0))<3:
        n=min(5, len(free_cells))
        if money_l>n*80+300: orders.append(["BUY_SEED","MELON",n]); money_l-=n*80

    # 6. Buy land when farm is full (top players unlock all 4 quadrants)
    if len(quadrants)<4 and day<total_days-8:
        lc=_land_cost(me)
        if len(free_cells)<8 and money_l>lc+500: orders.append(["BUY_LAND"]); money_l-=lc

    return orders[:10]

# ══════════════════════════════════════════════════════════════════════════════
# Main agent entry point
# ══════════════════════════════════════════════════════════════════════════════
def _agent(obs):
    player=obs["player"]; day=int(obs.get("day",0)); hour=int(obs.get("hour",0))
    me=obs["farms"][player]; opp=obs["farms"][1-player]
    private=obs.get("private") or {}; market=obs.get("market") or {}
    minv=market.get("inventory") or {}; shops=(obs.get("town") or {}).get("unlocked_shops") or []
    tiles=me.get("tiles") or []; board=len(tiles) or 10; total_days=30
    money=me.get("money",0); shed=private.get("shed") or {}
    seeds=private.get("seeds") or {}; invs=private.get("inventories") or [{}]

    scan=_scan(me,day); free_cells=_free_cells(me,board)
    animals=_count_animals(me, private); n_units=1+len(me.get("hands") or [])
    pipeline=_my_pipeline(me,day,total_days)
    for p in SELL_PRODUCE: pipeline[p]=pipeline.get(p,0)+int(shed.get(p,0))
    opp_flood=read_opponent(opp,day)
    picks=[]
    if day<total_days-3 and free_cells:
        picks=plan_portfolio(len(free_cells),n_units,money,minv,shops,day,total_days,opp_flood,pipeline)

    orders=_build_market_orders(obs,picks,scan,total_days)

    # ── farmer action: RL if loaded, else v2 heuristic ──────────────────────
    if _RL_POLICY is not None and _RL_POLICY.loaded:
        try:
            vec=obs_to_vec(obs,player)
            action_id=_RL_POLICY.predict(vec)
            raw_op=macro_to_farmer_op(action_id,obs,player,seeds)
            farmer_op=resolve_farmer_op(raw_op,obs,player,private)
            # if RL wants to plant, make sure seed purchase is in orders
            if raw_op and str(raw_op[0]).startswith("__PLANT__"):
                crop=str(raw_op[0])[9:]
                if seeds.get(crop,0)==0 and money>CROP_SPECS.get(crop,{}).get("seed",0)+200:
                    orders=[["BUY_SEED",crop,3]]+orders
            orders=orders[:10]
        except Exception:
            farmer_op=["PASS"]
    else:
        # v2 heuristic farmer
        tasks=build_tasks(scan,me,private,picks,free_cells,day,hour,board,total_days)
        positions=[tuple(me.get("farmer") or (board//2-1,board//2-1))]
        positions+=[tuple(h) for h in (me.get("hands") or [])]
        ops_out=[None]*len(positions)
        sheds=shed_adjacent_cells(board)
        for i,pos in enumerate(positions):
            inv=invs[i] if i<len(invs) else {}
            if _drop_task_needed(inv):
                if tuple(pos) in [tuple(c) for c in sheds]: ops_out[i]=["DROP"]
                else:
                    tgt=min(sheds,key=lambda c:manhattan(pos,c))
                    st=step_toward(pos,tgt); ops_out[i]=[st] if st else ["DROP"]
        free_units=[i for i in range(len(positions)) if ops_out[i] is None]
        asgn=assign_tasks([positions[i] for i in free_units],tasks,"f")
        feed_need=max(1,min(6,len(scan["feed"])))
        for li,task in asgn.items():
            gi=free_units[li]; ops_out[gi]=_unit_op(positions[gi],task,private,gi,board,feed_need,me)
        for i in range(len(ops_out)):
            if ops_out[i] is None: ops_out[i]=["PASS"]
        farmer_op=ops_out[0]
        hands_ops=ops_out[1:]
        return {"farmer":farmer_op,"hands":hands_ops,"market":orders}

    # hands still use v2 task system
    tasks=build_tasks(scan,me,private,picks,free_cells,day,hour,board,total_days)
    hands_pos=[tuple(h) for h in (me.get("hands") or [])]
    if not hands_pos:
        return {"farmer":farmer_op,"hands":[],"market":orders}
    asgn=assign_tasks(hands_pos,tasks)
    feed_need=max(1,min(6,len(scan["feed"])))
    hands_ops=[None]*len(hands_pos)
    sheds=shed_adjacent_cells(board)
    for i,pos in enumerate(hands_pos):
        inv=invs[i+1] if i+1<len(invs) else {}
        if _drop_task_needed(inv):
            if tuple(pos) in [tuple(c) for c in sheds]: hands_ops[i]=["DROP"]
            else:
                tgt=min(sheds,key=lambda c:manhattan(pos,c))
                st=step_toward(pos,tgt); hands_ops[i]=[st] if st else ["DROP"]
    for li,task in asgn.items():
        if hands_ops[li] is None:
            hands_ops[li]=_unit_op(hands_pos[li],task,private,li+1,board,feed_need,me)
    for i in range(len(hands_ops)):
        if hands_ops[i] is None: hands_ops[i]=["PASS"]

    return {"farmer":farmer_op,"hands":hands_ops,"market":orders}


def agent(obs):
    return _agent(obs)
