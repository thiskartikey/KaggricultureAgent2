"""Gymnasium wrapper for Kaggriculture — single-agent (vs 'starter')."""
import numpy as np
try:
    import gymnasium as gym
    from gymnasium import spaces
    BaseEnv = gym.Env
except ImportError:
    gym = None
    spaces = None
    BaseEnv = object
from kaggle_environments import make

# ── observation layout (flat float32 vector, len = OBS_DIM) ─────────────────
# day/hour/money/quadrants: 4
# my farm summary (per crop: count, needs_water, harvestable, avg_age): 5*4 = 20
# animal summary (per animal: count, needs_feed, harvestable): 3*3 = 9
# farmer xy: 2
# market prices normalised (9 products): 9
# market inventory normalised (9): 9
# shed contents normalised (9+3 animals): 12
# seeds (5 crops): 5
# town shops unlocked (8 binary): 8
# opponent farm summary (same as mine): 29
# Total: 4+20+9+2+9+9+12+5+8+29 = 107
OBS_DIM = 107

CROPS    = ["WHEAT","CARROT","TOMATO","STRAWBERRY","MELON"]
ANIMALS  = ["GOOSE","COW","SHEEP"]
PRODUCTS = ["WHEAT","CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER"]
BASE_PRICES = [25, 35, 60, 120, 250, 50, 160, 200, 100]
SHOPS = ["BAKERY","PIZZA_SHOP","BRUNCH_SPOT","YARN_STORE","ICE_CREAM_SHOP",
         "PET_CAFE","SMOOTHIE_SHOP","FARMERS_MARKET"]

# ── high-level macro-actions for the farmer ──────────────────────────────────
# 0  GO_HARVEST    – move toward / harvest nearest harvestable tile
# 1  GO_WATER      – move toward / water nearest unwatered tile
# 2  GO_PLANT_M    – move toward / plant MELON on nearest empty tile
# 3  GO_PLANT_C    – move toward / plant CARROT
# 4  GO_PLANT_W    – move toward / plant WHEAT
# 5  GO_FEED       – move toward / feed nearest hungry animal
# 6  GO_DIG        – move toward / dig nearest weed
# 7  PASS
N_ACTIONS = 8


def _norm_shop(s):
    return str(s).strip().upper().replace(" ","_").replace("-","_")

def _farm_summary(tiles, day):
    """Returns (20-d crop vec, 9-d animal vec, occupied_count)."""
    cv = np.zeros(20, np.float32)   # 4 features per crop
    av = np.zeros(9,  np.float32)   # 3 features per animal
    occ = 0
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            if not isinstance(t, dict):
                continue
            k = t.get("kind")
            if k == "PLANT":
                c = t.get("crop")
                if c in CROPS:
                    ci = CROPS.index(c)
                    cv[ci*4]   += 1                                    # count
                    cv[ci*4+1] += int(not t.get("watered_today",False)) # needs water
                    cv[ci*4+2] += int(t.get("yield_units",0) > 0)      # harvestable
                    cv[ci*4+3] += max(0, day - t.get("planted_day",day)) / 30.0
                occ += 1
            elif k in ("COOP","PASTURE"):
                a = t.get("animal")
                if a in ANIMALS:
                    ai = ANIMALS.index(a)
                    av[ai*3]   += 1
                    av[ai*3+1] += int(not t.get("fed_today",False))
                    av[ai*3+2] += int(t.get("yield_units",0) > 0)
                occ += 1
    return cv, av, occ

def obs_to_vec(obs, player):
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
    cv, av, _ = _farm_summary(tiles, day)
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
    ocv, oav, _ = _farm_summary(opp_tiles, day)
    v[i:i+20] = ocv / 10.0; i+=20
    v[i:i+9]  = oav / 10.0; i+=9

    assert i == OBS_DIM, f"obs dim mismatch: {i}"
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
    """Convert macro action id → farmer op list.  Returns (farmer_op, market_list)."""
    me    = obs["farms"][player]
    priv  = obs.get("private",{}) or {}
    seeds = seeds_override or priv.get("seeds",{}) or {}
    tiles = me.get("tiles") or []
    n     = len(tiles)
    pos   = tuple(me.get("farmer",[4,4]))
    day   = obs.get("day",0)

    # scan
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
    return ["PASS"]  # action 7 = PASS


def resolve_farmer_op(raw_op, obs, player, priv):
    """Turn __PLANT__CROP or regular op into the actual op, handling movement."""
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
        # find nearest empty and move
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


def calc_net_worth(obs, player):
    me = obs["farms"][player]
    priv = obs.get("private", {}) or {}
    money = float(me.get("money", 0.0))
    
    seeds = priv.get("seeds", {}) or {}
    money += seeds.get("MELON", 0) * 80
    money += seeds.get("CARROT", 0) * 20
    money += seeds.get("WHEAT", 0) * 10
    
    shed = priv.get("shed", {}) or {}
    vals = {"MELON": 250, "CARROT": 35, "WHEAT": 25, "TOMATO": 60, "STRAWBERRY": 120}
    for k, v in shed.items():
        money += v * vals.get(k, 50)
        
    tiles = me.get("tiles") or []
    seed_costs = {"MELON": 80, "CARROT": 20, "WHEAT": 10, "TOMATO": 30, "STRAWBERRY": 60}
    for row in tiles:
        for t in row:
            if isinstance(t, dict) and t.get("kind") == "PLANT":
                crop = t.get("crop")
                # Give the full value of the seed, PLUS a bonus for having it in the ground!
                money += seed_costs.get(crop, 20) + (vals.get(crop, 50) * 0.5)
    return money

class KagrEnv(BaseEnv):
    """Single-player Gymnasium env wrapping kaggriculture (player 0 vs 'starter')."""

    metadata = {"render_modes":[]}

    def __init__(self, opponent="starter"):
        if BaseEnv is not object:
            super().__init__()
        self.opponent = opponent
        if spaces is not None:
            self.observation_space = spaces.Box(0.0, 1.0, (OBS_DIM,), np.float32)
            self.action_space = spaces.Discrete(N_ACTIONS)
        self._env = None
        self._obs = None
        self._done = False
        self._prev_money = 3000.0

    def _make_market_orders(self, obs, player=0):
        """Delegate to top-player heuristic strategy."""
        from heuristic import _make_market_orders as h_orders
        return h_orders(obs, player)

    def _buy_seed_if_needed(self, obs, crop, player=0):
        """Return extra market order to buy one seed if we have none."""
        priv = obs.get("private",{}) or {}
        seeds = priv.get("seeds",{}) or {}
        me = obs["farms"][player]
        money = me.get("money",0)
        SEED_COST={"MELON":80,"CARROT":20,"WHEAT":10}
        if seeds.get(crop,0)==0 and money>SEED_COST.get(crop,0)+200:
            return [["BUY_SEED", crop, 3]]
        return []

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._env = make("kaggriculture", debug=False)
        self._trainer = self._env.train([None, self.opponent])
        raw = self._trainer.reset()
        self._obs = dict(raw)
        self._obs.setdefault("player", 0)
        self._prev_money = calc_net_worth(self._obs, 0)
        self._done = False
        return obs_to_vec(self._obs, 0), {}

    def _compose_action(self, action, obs):
        priv  = obs.get("private", {}) or {}
        seeds = priv.get("seeds", {}) or {}
        raw_op    = macro_to_farmer_op(action, obs, 0, seeds)
        farmer_op = resolve_farmer_op(raw_op, obs, 0, priv)
        orders    = self._make_market_orders(obs)
        if raw_op and str(raw_op[0]).startswith("__PLANT__"):
            crop = str(raw_op[0])[9:]
            orders = self._buy_seed_if_needed(obs, crop) + orders
        # hands mirror the farmer's macro so hired help isn't wasted
        n_hands = len(obs["farms"][0].get("hands") or [])
        hands = []
        for _ in range(n_hands):
            hands.append(resolve_farmer_op(raw_op, obs, 0, priv))
        return {"farmer": farmer_op, "hands": hands, "market": orders[:10]}

    def step(self, action):
        if self._done:
            raise RuntimeError("call reset() first")
        obs = self._obs
        act = self._compose_action(int(action), obs)
        new_obs, _kag_reward, done, _info = self._trainer.step(act)
        new_obs = dict(new_obs)
        new_obs.setdefault("player", 0)

        new_money = calc_net_worth(new_obs, 0)
        opp_money = calc_net_worth(new_obs, 1)
        reward = float(new_money - self._prev_money)
        self._prev_money = new_money
        self._obs = new_obs

        if done:
            self._done = True
            reward += 5000.0 if new_obs["farms"][0].get("money", 0) > new_obs["farms"][1].get("money", 0) else -5000.0
        return obs_to_vec(new_obs, 0), reward, bool(done), False, {}
