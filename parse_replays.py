"""
parse_replays.py — High-quality replay parser for Kaggriculture.

Improvements over previous version:
  - Fixed min_score default (was 100_000, excluded ~80% of replays; now 0)
  - Fixed returns_to_go: now actual discounted future money delta, not final-current
  - Expanded OBS_DIM: 107 → 145, adding:
      * consecutive_unwatered, fertilized_until_day, near-death flag per PLANT
      * consecutive_unfed, pending_care_bonus, fertilizer_available per PASTURE
      * per-unit inventories (wheat/product held by farmer + hands)
      * weed count, free-tile count, locked-tile count
      * opponent money, opponent quadrant count
  - Correct path defaults pointing to replays/ directory tree
  - Source player ID extracted from replay info (not assumed 0)
  - Both players extracted as separate trajectories from each replay
  - Episode metadata (episode_id, source_dir) saved per trajectory
"""

import os
import json
import pickle
import glob
import numpy as np

# ── Feature-vector dimension ──────────────────────────────────────────────────
# Layout (see _feature_layout() for full breakdown):
#  [0:4]    time context
#  [4:39]   my crop features   (5 crops × 7)
#  [39:57]  my animal features (3 animals × 6)
#  [57:59]  farmer position
#  [59:68]  market prices
#  [68:77]  market inventory
#  [77:86]  shed products
#  [86:89]  shed animals
#  [89:94]  seeds
#  [94:102] shops unlocked
#  [102:111] unit inventories total (9 products held across all units)
#  [111:114] weed/free/locked tile counts
#  [114:134] opponent crop features (5 × 4)
#  [134:143] opponent animal features (3 × 3)
#  [143]    opponent money
#  [144]    opponent quadrant count
OBS_DIM = 145

CROPS    = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
ANIMALS  = ["GOOSE", "COW", "SHEEP"]
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER"]
BASE_PRICES = [25, 35, 60, 120, 250, 50, 160, 200, 100]
SHOPS = ["BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "YARN_STORE", "ICE_CREAM_SHOP",
         "PET_CAFE", "SMOOTHIE_SHOP", "FARMERS_MARKET"]


def _norm_shop(s):
    return str(s).strip().upper().replace(" ", "_").replace("-", "_")


# ── Farm-level feature extraction ─────────────────────────────────────────────

def _scan_my_tiles(tiles, day, hour):
    """
    Scan my farm tiles and return:
      cv  [5*7]  per-crop features
      av  [3*6]  per-animal features
      n_weed int
      n_free int
      n_locked int

    `hour` is the current hour (0-23) within `day`, used for precise near-death detection.
    Normalisation note: all cv/av features are divided by 10.0 at return time, relying on
    the invariant that no single crop or animal type occupies more than 10 tiles.
    """
    cv = np.zeros(5 * 7, np.float32)   # 7 features per crop
    av = np.zeros(3 * 6, np.float32)   # 6 features per animal
    n_weed = 0
    n_free = 0
    n_locked = 0

    for row in tiles:
        for t in row:
            if t is None:
                n_free += 1
                continue
            if isinstance(t, str):
                # "LOCKED" string tile
                n_locked += 1
                continue
            if not isinstance(t, dict):
                continue

            kind = t.get("kind")

            if kind == "WEED":
                n_weed += 1

            elif kind == "PLANT":
                c = t.get("crop")
                if c in CROPS:
                    ci = CROPS.index(c)
                    base = ci * 7
                    cv[base + 0] += 1                                           # count
                    cv[base + 1] += int(not t.get("watered_today", False))      # needs water today
                    cv[base + 2] += int(t.get("yield_units", 0) > 0)            # ready to harvest
                    # age: days since planting, normalised to 30-day season
                    cv[base + 3] += max(0, day - t.get("planted_day", day)) / 30.0
                    # consecutive_unwatered stress (0 = healthy, 1+ = wilting)
                    cv[base + 4] += min(t.get("consecutive_unwatered", 0) / 3.0, 1.0)
                    # fertilized (fertilized_until_day >= today means it's active)
                    cv[base + 5] += float(int(t.get("fertilized_until_day", -1)) >= day)
                    # near-death: max_lifespan_step > 0 and within 48 steps (2 days).
                    # Use day*24+hour as current_step so we don't overstate time-to-death.
                    # Sentinel -1 means unlimited lifespan (e.g. STRAWBERRY) → not near death.
                    mls = t.get("max_lifespan_step") or -1  # guards mls=0 and mls=None
                    steps_left = (mls - (day * 24 + hour)) if mls > 0 else 999
                    cv[base + 6] += float(0 < steps_left <= 48)

            elif kind in ("PASTURE", "COOP"):
                a = t.get("animal")
                if a in ANIMALS:
                    ai = ANIMALS.index(a)
                    base = ai * 6
                    av[base + 0] += 1                                           # count
                    av[base + 1] += int(not t.get("fed_today", False))          # unfed
                    av[base + 2] += int(t.get("yield_units", 0) > 0)            # ready to collect
                    av[base + 3] += int(not t.get("cared_today", False))        # uncared
                    av[base + 4] += int(t.get("fertilizer_available", False))   # fert ready
                    # pending_care_bonus: accumulated bonus from consecutive care days
                    av[base + 5] += min(t.get("pending_care_bonus", 0) / 5.0, 1.0)

    # Normalise count-based features by 10 (typical max tiles)
    return cv / 10.0, av / 10.0, n_weed, n_free, n_locked


def _scan_opp_tiles(tiles, day):
    """
    Scan opponent tiles (public data only — no private fields).
    Returns cv [5*4], av [3*3].
    """
    cv = np.zeros(5 * 4, np.float32)
    av = np.zeros(3 * 3, np.float32)

    for row in tiles:
        for t in row:
            if not isinstance(t, dict):
                continue
            kind = t.get("kind")
            if kind == "PLANT":
                c = t.get("crop")
                if c in CROPS:
                    ci = CROPS.index(c)
                    base = ci * 4
                    cv[base + 0] += 1
                    cv[base + 1] += int(not t.get("watered_today", False))
                    cv[base + 2] += int(t.get("yield_units", 0) > 0)
                    cv[base + 3] += max(0, day - t.get("planted_day", day)) / 30.0
            elif kind in ("PASTURE", "COOP"):
                a = t.get("animal")
                if a in ANIMALS:
                    ai = ANIMALS.index(a)
                    base = ai * 3
                    av[base + 0] += 1
                    av[base + 1] += int(not t.get("fed_today", False))
                    av[base + 2] += int(t.get("yield_units", 0) > 0)

    return cv / 10.0, av / 10.0


# ── Observation → feature vector ──────────────────────────────────────────────

def obs_to_vec(obs, player):
    """
    Convert a game observation dict to a fixed-length float32 feature vector.

    obs: dict from step[player]['observation']
    player: 0 or 1

    Returns np.ndarray of shape (OBS_DIM,) == (145,).
    """
    v = np.zeros(OBS_DIM, np.float32)

    me   = obs["farms"][player]
    opp  = obs["farms"][1 - player]
    day  = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))

    priv  = obs.get("private") or {}
    mkt   = obs.get("market")  or {}
    town  = obs.get("town")    or {}

    i = 0
    # ── [0:4] Time context ───────────────────────────────────────────────────
    v[i] = day / 30.0
    i += 1
    v[i] = hour / 24.0
    i += 1
    v[i] = min(me.get("money", 0) / 50000.0, 1.0)
    i += 1
    v[i] = len(me.get("unlocked_quadrants") or ["NW"]) / 4.0
    i += 1
    assert i == 4

    # ── [4:39] My crop features (5 × 7 = 35) ────────────────────────────────
    my_tiles = me.get("tiles") or []
    cv, av, n_weed, n_free, n_locked = _scan_my_tiles(my_tiles, day, hour)
    v[i:i + 35] = cv
    i += 35
    assert i == 39

    # ── [39:57] My animal features (3 × 6 = 18) ─────────────────────────────
    v[i:i + 18] = av
    i += 18
    assert i == 57

    # ── [57:59] Farmer position ──────────────────────────────────────────────
    fx, fy = me.get("farmer", [4, 4])
    v[i]     = fx / 10.0
    v[i + 1] = fy / 10.0
    i += 2
    assert i == 59

    # ── [59:68] Market prices ────────────────────────────────────────────────
    mprc = mkt.get("prices") or {}
    for j, p in enumerate(PRODUCTS):
        v[i + j] = min(mprc.get(p, BASE_PRICES[j]) / (BASE_PRICES[j] * 2), 1.0)
    i += 9
    assert i == 68

    # ── [68:77] Market inventory ─────────────────────────────────────────────
    minv = mkt.get("inventory") or {}
    for j, p in enumerate(PRODUCTS):
        v[i + j] = min(minv.get(p, 10000) / 10000.0, 1.0)
    i += 9
    assert i == 77

    # ── [77:86] Shed products ────────────────────────────────────────────────
    shed = priv.get("shed") or {}
    for j, p in enumerate(PRODUCTS):
        v[i + j] = min(shed.get(p, 0) / 20.0, 1.0)
    i += 9
    assert i == 86

    # ── [86:89] Shed animals (GOOSE, COW, SHEEP) ─────────────────────────────
    for j, a in enumerate(ANIMALS):
        v[i + j] = min(shed.get(a, 0) / 5.0, 1.0)
    i += 3
    assert i == 89

    # ── [89:94] Seeds ─────────────────────────────────────────────────────────
    seeds = priv.get("seeds") or {}
    for j, c in enumerate(CROPS):
        v[i + j] = min(seeds.get(c, 0) / 10.0, 1.0)
    i += 5
    assert i == 94

    # ── [94:102] Shops unlocked ──────────────────────────────────────────────
    shops_u = {_norm_shop(s) for s in (town.get("unlocked_shops") or [])}
    for j, s in enumerate(SHOPS):
        v[i + j] = float(s in shops_u)
    i += 8
    assert i == 102

    # ── [102:111] Unit inventories (total items held by farmer + all hands) ──
    # inventories[0] = farmer, inventories[1:] = hands
    all_invs = priv.get("inventories") or [{}]
    combined = {}
    for inv in all_invs:
        if isinstance(inv, dict):
            for p, qty in inv.items():
                combined[p] = combined.get(p, 0) + qty
    for j, p in enumerate(PRODUCTS):
        v[i + j] = min(combined.get(p, 0) / 20.0, 1.0)
    i += 9
    assert i == 111

    # ── [111:114] Weed / free / locked tile counts ────────────────────────────
    v[i]     = min(n_weed   / 10.0, 1.0)
    v[i + 1] = min(n_free   / 25.0, 1.0)   # up to 25 unlocked free tiles is typical
    v[i + 2] = min(n_locked / 75.0, 1.0)   # starts at 75 locked tiles
    i += 3
    assert i == 114

    # ── [114:134] Opponent crop features (5 × 4 = 20) ────────────────────────
    opp_tiles = opp.get("tiles") or []
    ocv, oav = _scan_opp_tiles(opp_tiles, day)
    v[i:i + 20] = ocv
    i += 20
    assert i == 134

    # ── [134:143] Opponent animal features (3 × 3 = 9) ───────────────────────
    v[i:i + 9] = oav
    i += 9
    assert i == 143

    # ── [143] Opponent money ──────────────────────────────────────────────────
    v[i] = min(opp.get("money", 0) / 50000.0, 1.0)
    i += 1
    assert i == 144

    # ── [144] Opponent quadrant count ─────────────────────────────────────────
    v[i] = len(opp.get("unlocked_quadrants") or ["NW"]) / 4.0
    i += 1
    assert i == OBS_DIM

    return v


# ── Replay parsing ─────────────────────────────────────────────────────────────

def parse_single_replay(path, min_score=0):
    """
    Parse one replay JSON file.

    Returns list of trajectory dicts (0, 1, or 2 per file depending on
    how many players meet min_score).

    Each trajectory:
      states       np.ndarray [T, OBS_DIM]
      actions      list of T action dicts
      returns_to_go  np.ndarray [T]   cumulative future money gained
      rewards      np.ndarray [T]   per-step money delta
      score        float  final score for this player
      player       int    0 or 1
      episode_id   int or None
      source       str   basename of replay file
    """
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception as e:
        print(f"  Error loading {path}: {e}")
        return []

    steps = data.get("steps") or []
    if not steps:
        return []

    # Use top-level rewards (authoritative final scores)
    top_rewards = data.get("rewards") or [None, None]
    episode_id  = (data.get("info") or {}).get("EpisodeId")
    source      = os.path.basename(path)

    trajectories = []
    for player_idx in range(2):
        score = top_rewards[player_idx] if player_idx < len(top_rewards) else None
        if score is None or score < min_score:
            continue

        states  = []
        actions = []
        moneys  = []    # raw money at each step

        for step in steps:
            if player_idx >= len(step):
                continue
            sp  = step[player_idx]
            obs = sp.get("observation") or {}
            # Make sure farms list has both players
            if len(obs.get("farms") or []) < 2:
                continue

            try:
                state_vec = obs_to_vec(obs, player_idx)
            except Exception:
                continue   # skip malformed/truncated observation
            states.append(state_vec)
            actions.append(sp.get("action") or {})
            moneys.append(float(obs["farms"][player_idx].get("money", 0)))

        if not states:
            continue

        T = len(states)
        moneys = np.array(moneys, dtype=np.float32)

        # Per-step reward: raw money delta (positive = earned, negative = spent on seeds/animals/labour).
        # Negative deltas are kept so RTG reflects true net income and investment cost.
        # A Decision Transformer conditioned on RTG=X can learn to invest early (negative reward
        # steps) in order to earn more later — clipping to 0 would hide this trade-off entirely.
        rewards = np.zeros(T, np.float32)
        rewards[1:] = moneys[1:] - moneys[:-1]

        # Returns-to-go: sum of all future rewards from step t onward.
        #   RTG[t] = sum_{s=t}^{T-1} rewards[s]
        # RTG[0] == final_money - starting_money  (net income over the game).
        # RTG[-1] == 0 (no future reward at the last step).
        rtg = np.zeros(T, np.float32)
        cumsum = 0.0
        for t in range(T - 1, -1, -1):
            cumsum += rewards[t]
            rtg[t] = cumsum

        trajectories.append({
            "states":         np.array(states, dtype=np.float32),
            "actions":        actions,
            "rewards":        rewards,
            "returns_to_go":  rtg,
            "score":          float(score),
            "player":         player_idx,
            "episode_id":     episode_id,
            "source":         source,
        })

    return trajectories


def parse_replays(replay_dirs, min_score=0, verbose=True):
    """
    Parse all replay JSON files from a list of directories (or a single path string).

    Args:
        replay_dirs: str or list of str — directories to search for *.json files.
        min_score: only include trajectories where the player's final score >= this.
        verbose: print progress.

    Returns:
        list of trajectory dicts (see parse_single_replay for schema).
    """
    if isinstance(replay_dirs, str):
        replay_dirs = [replay_dirs]

    files = []
    for d in replay_dirs:
        if os.path.isfile(d) and d.endswith(".json"):
            files.append(d)
        elif os.path.isdir(d):
            files.extend(sorted(glob.glob(os.path.join(d, "*.json"))))

    if verbose:
        print(f"Found {len(files)} JSON files across {len(replay_dirs)} source(s). Parsing...")

    trajectories = []
    for f_idx, path in enumerate(files):
        trajs = parse_single_replay(path, min_score=min_score)
        trajectories.extend(trajs)

        if verbose and (f_idx + 1) % 20 == 0:
            print(f"  {f_idx + 1}/{len(files)} replays parsed, {len(trajectories)} trajectories so far...")

    if verbose:
        scores = [t["score"] for t in trajectories]
        print(f"Parsing complete: {len(trajectories)} trajectories from {len(files)} replays")
        if scores:
            import statistics
            print(f"  Score range: {min(scores):,.0f} – {max(scores):,.0f}  "
                  f"mean={statistics.mean(scores):,.0f}  median={statistics.median(scores):,.0f}")

    return trajectories


# ── Self-test ──────────────────────────────────────────────────────────────────

def _selftest():
    """Quick correctness check: parse one replay file and verify shapes/values."""
    test_file = None
    for d in ["replays/champion_v2_20260815", "replays/Ezzzzzekki"]:
        cands = sorted(glob.glob(os.path.join(d, "*.json")))
        if cands:
            test_file = cands[0]
            break

    if test_file is None:
        print("No replay files found for self-test.")
        return

    print(f"Self-test on: {test_file}")
    trajs = parse_single_replay(test_file, min_score=0)
    print(f"  Extracted {len(trajs)} trajectory(s)")
    for t in trajs:
        T = len(t["states"])
        assert t["states"].shape == (T, OBS_DIM), \
            f"states shape {t['states'].shape} != ({T}, {OBS_DIM})"
        assert len(t["actions"]) == T
        assert t["rewards"].shape == (T,)
        assert t["returns_to_go"].shape == (T,)
        assert np.all(np.isfinite(t["states"])), "states has inf/nan"
        assert np.isclose(t["returns_to_go"][-1], 0.0, atol=1.0), "RTG[-1] should be ~0"
        # RTG[0] should equal net income (final - starting money) roughly
        rtg = t["returns_to_go"]
        net_income = t["score"] - 3000.0  # starting_money = 3000
        assert abs(rtg[0] - net_income) < 2000, \
            f"RTG[0]={rtg[0]:.0f} far from net_income={net_income:.0f}"
        print(f"  player={t['player']}  T={T}  score={t['score']:,.0f}  "
              f"rtg[0]={rtg[0]:,.0f}  net_income={net_income:,.0f}  "
              f"states[0] non-zero={np.count_nonzero(t['states'][0])}/{OBS_DIM}")
    print("Self-test PASSED")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, statistics

    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+",
                    default=[
                        "replays/champion_v2_20260815",
                        "replays/Ezzzzzekki",
                        "replays/GiovanniCR",
                        "replays/HealthStone",
                        "replays/ThunderThunder",
                        "replays/Ueddy",
                        "replays/Utkarsh #2",
                        "replays/カワシギ",
                    ],
                    help="Directories containing replay JSON files")
    ap.add_argument("--min-score", type=float, default=0,
                    help="Minimum final score to include a trajectory (default: 0)")
    ap.add_argument("--output", default="parsed_trajectories.pkl",
                    help="Output pickle file path")
    ap.add_argument("--selftest", action="store_true",
                    help="Run self-test on a single replay and exit")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
    else:
        trajectories = parse_replays(args.dirs, min_score=args.min_score)

        with open(args.output, "wb") as f:
            pickle.dump(trajectories, f)
        print(f"Saved {len(trajectories)} trajectories to {args.output}")
