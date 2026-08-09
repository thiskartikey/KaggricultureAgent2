import os
import json
import pickle
import numpy as np

# Dimension of flat observation vector (same as env_wrapper)
OBS_DIM = 107

CROPS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
ANIMALS = ["GOOSE", "COW", "SHEEP"]
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
BASE_PRICES = [25, 35, 60, 120, 250, 50, 160, 200, 100]
SHOPS = ["BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "YARN_STORE", "ICE_CREAM_SHOP",
         "PET_CAFE", "SMOOTHIE_SHOP", "FARMERS_MARKET"]


def _norm_shop(s):
    return str(s).strip().upper().replace(" ", "_").replace("-", "_")


def _farm_summary(tiles, day):
    cv = np.zeros(20, np.float32)
    av = np.zeros(9, np.float32)
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            if not isinstance(t, dict):
                continue
            k = t.get("kind")
            if k == "PLANT":
                c = t.get("crop")
                if c in CROPS:
                    ci = CROPS.index(c)
                    cv[ci * 4] += 1
                    cv[ci * 4 + 1] += int(not t.get("watered_today", False))
                    cv[ci * 4 + 2] += int(t.get("yield_units", 0) > 0)
                    cv[ci * 4 + 3] += max(0, day - t.get("planted_day", day)) / 30.0
            elif k in ("COOP", "PASTURE"):
                a = t.get("animal")
                if a in ANIMALS:
                    ai = ANIMALS.index(a)
                    av[ai * 3] += 1
                    av[ai * 3 + 1] += int(not t.get("fed_today", False))
                    av[ai * 3 + 2] += int(t.get("yield_units", 0) > 0)
    return cv, av


def obs_to_vec(obs, player):
    v = np.zeros(OBS_DIM, np.float32)
    me = obs["farms"][player]
    opp = obs["farms"][1 - player]
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    priv = obs.get("private", {}) or {}
    mkt = obs.get("market", {}) or {}
    town = obs.get("town", {}) or {}

    i = 0
    v[i] = day / 30.0
    i += 1
    v[i] = hour / 24.0
    i += 1
    v[i] = min(me.get("money", 0) / 50000.0, 1.0)
    i += 1
    v[i] = len(me.get("unlocked_quadrants", ["NW"])) / 4.0
    i += 1

    tiles = me.get("tiles") or []
    cv, av = _farm_summary(tiles, day)
    v[i:i + 20] = cv / 10.0
    i += 20
    v[i:i + 9] = av / 10.0
    i += 9

    fx, fy = me.get("farmer", [4, 4])
    v[i] = fx / 10.0
    v[i + 1] = fy / 10.0
    i += 2

    minv = mkt.get("inventory", {}) or {}
    mprc = mkt.get("prices", {}) or {}
    for j, p in enumerate(PRODUCTS):
        v[i + j] = min(mprc.get(p, BASE_PRICES[j]) / (BASE_PRICES[j] * 2), 1.0)
    i += 9
    for j, p in enumerate(PRODUCTS):
        v[i + j] = min(minv.get(p, 10000) / 10000.0, 1.0)
    i += 9

    shed = priv.get("shed", {}) or {}
    seeds = priv.get("seeds", {}) or {}
    for j, p in enumerate(PRODUCTS):
        v[i + j] = min(shed.get(p, 0) / 20.0, 1.0)
    i += 9
    for j, a in enumerate(ANIMALS):
        v[i + j] = min(shed.get(a, 0) / 5.0, 1.0)
    i += 3

    for j, c in enumerate(CROPS):
        v[i + j] = min(seeds.get(c, 0) / 10.0, 1.0)
    i += 5

    shops_u = {_norm_shop(s) for s in (town.get("unlocked_shops") or [])}
    for j, s in enumerate(SHOPS):
        v[i + j] = float(s in shops_u)
    i += 8

    opp_tiles = opp.get("tiles") or []
    ocv, oav = _farm_summary(opp_tiles, day)
    v[i:i + 20] = ocv / 10.0
    i += 20
    v[i:i + 9] = oav / 10.0
    i += 9

    return v


def parse_replays(training_dir, min_score=100000):
    trajectories = []
    files = [f for f in os.listdir(training_dir) if f.endswith('.json')]
    print(f"Found {len(files)} JSON files. Starting parsing...")

    for f_idx, filename in enumerate(files):
        path = os.path.join(training_dir, filename)
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            continue

        steps = data.get("steps", [])
        if not steps:
            continue

        # Extract final rewards (cash)
        final_step = steps[-1]
        r0 = final_step[0].get("reward", 0)
        r1 = final_step[1].get("reward", 0)

        # Process each player separately if they satisfy the score criteria
        for player_idx, score in enumerate([r0, r1]):
            if score is not None and score >= min_score:
                states = []
                actions = []
                rewards = []

                for t, step in enumerate(steps):
                    # Record state
                    obs = step[player_idx]["observation"]
                    # Add player index context to obs
                    obs["player"] = player_idx
                    state_vec = obs_to_vec(obs, player_idx)
                    states.append(state_vec)

                    # Record action executed at this step
                    act = step[player_idx].get("action", {})
                    actions.append(act)

                    # Current money/cash at this step
                    money = obs["farms"][player_idx].get("money", 0)
                    rewards.append(money)

                # Calculate returns-to-go (R_t = final_score - current_money_accumulated)
                returns_to_go = []
                for t in range(len(rewards)):
                    returns_to_go.append(score - rewards[t])

                trajectories.append({
                    "states": np.array(states, dtype=np.float32),
                    "actions": actions,  # list of action dicts
                    "returns_to_go": np.array(returns_to_go, dtype=np.float32),
                    "score": score
                })

        if (f_idx + 1) % 10 == 0:
            print(f"Parsed {f_idx + 1}/{len(files)} replays...")

    print(f"Parsing complete. Extracted {len(trajectories)} expert trajectories.")
    return trajectories


if __name__ == "__main__":
    training_dir = "downloads/training"
    trajectories = parse_replays(training_dir, min_score=100000)

    # Save to a pickle file
    output_path = "parsed_trajectories.pkl"
    with open(output_path, "wb") as f:
        pickle.dump(trajectories, f)
    print(f"Saved parsed trajectories to {output_path}")
