import re

with open("policy.py", "r") as f:
    content = f.read()
    
# 1. Add ROI functions
roi_funcs = """
def should_plant(crop, day, total_days, market_inv):
    \"\"\"True if planting `crop` today will earn back seed cost before game ends.\"\"\"
    return plant_expected_profit(crop, day, total_days, market_inv) > 0

def plant_expected_profit(crop, day, total_days, market_inv):
    \"\"\"Returns the expected profit from planting a crop today, factoring in market prices.\"\"\"
    spec = CROP_SPECS[crop]
    left = total_days - day
    if left <= spec["first"]:
        return -9999
        
    if spec["ongoing"] and spec["interval"] > 0:
        harvests = max(0, (left - spec["first"]) // spec["interval"]) + 1
    else:
        harvests = 1
        
    revenue = harvests * spec["max_yield"] * price(crop, int(market_inv.get(crop, 10000)))
    return revenue - spec["seed"]

def should_buy_animal(animal, day, total_days, market_inv):
    \"\"\"True if buying an animal today is expected to be profitable.\"\"\"
    spec = ANIMAL_SPECS[animal]
    left = total_days - day
    if left <= spec["first"]:
        return False
        
    harvests = max(0, (left - spec["first"]) // spec["interval"]) + 1
    revenue = harvests * price(spec["product"], int(market_inv.get(spec["product"], 10000)))
    # Animal cost includes feed (approx 1 wheat per day)
    feed_cost = left * price("WHEAT", int(market_inv.get("WHEAT", 10000)))
    return (revenue - spec["cost"] - feed_cost) > 0

def sell_revenue"""
content = content.replace("def sell_revenue", roi_funcs)


# 2. Update _seed_targets
old_targets = """def _seed_targets(day, total_days, planted, free_n, harvest_crop_n=0):
    \"\"\"How many seeds of each crop we still want to hold.\"\"\"
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
        # Wheat fills the rest, but always keep a minimum buffer of 15
        rest = target_free - want.get("MELON", 0) - want.get("STRAWBERRY", 0)
        want["WHEAT"] = max(15, min(max(0, rest), 30))
    return want"""

new_targets = """def _seed_targets(day, total_days, planted, free_n, harvest_crop_n, market_inv):
    \"\"\"How many seeds of each crop we still want to hold.\"\"\"
    want = {}
    target_free = free_n + harvest_crop_n
    
    # Only want Melon if it's profitable (yields before game ends)
    if plant_expected_profit("MELON", day, total_days, market_inv) > 0:
        want["MELON"] = max(0, min(TARGET_MELON - planted.get("MELON", 0), target_free))
    else:
        want["MELON"] = 0
        
    # Only want Strawberry if profitable
    if plant_expected_profit("STRAWBERRY", day, total_days, market_inv) > 0:
        want["STRAWBERRY"] = max(0, min(TARGET_STRAWBERRY - planted.get("STRAWBERRY", 0), target_free - want["MELON"]))
    else:
        want["STRAWBERRY"] = 0
        
    # Fallback to wheat if profitable
    if plant_expected_profit("WHEAT", day, total_days, market_inv) > 0:
        rest = target_free - want.get("MELON", 0) - want.get("STRAWBERRY", 0)
        want["WHEAT"] = max(15, min(max(0, rest), 30))
    else:
        want["WHEAT"] = 0
        
    return want"""
content = content.replace(old_targets, new_targets)


# 3. Update _plant_choice
old_choice = """def _plant_choice(day, total_days, planted, seeds):
    \"\"\"Pick the crop with the best remaining payback for one free tile.\"\"\"
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
    # WHEAT: sown and harvested inside 5 days, ~4-6 units from a 10 seed, and
    # sells near ~25 per unit. Great short-term fill.
    if (left >= 5 and int(seeds.get("WHEAT", 0)) > 0):
        return "WHEAT"
    return None"""

new_choice = """def _plant_choice(day, total_days, planted, seeds, market_inv):
    \"\"\"Pick the crop with the best remaining payback for one free tile.\"\"\"
    if int(seeds.get("MELON", 0)) > 0 and planted.get("MELON", 0) < TARGET_MELON:
        if plant_expected_profit("MELON", day, total_days, market_inv) > 0:
            return "MELON"
            
    if int(seeds.get("STRAWBERRY", 0)) > 0 and planted.get("STRAWBERRY", 0) < TARGET_STRAWBERRY:
        if plant_expected_profit("STRAWBERRY", day, total_days, market_inv) > 0:
            return "STRAWBERRY"
            
    if int(seeds.get("WHEAT", 0)) > 0:
        if plant_expected_profit("WHEAT", day, total_days, market_inv) > 0:
            return "WHEAT"
            
    return None"""
content = content.replace(old_choice, new_choice)


# 4. Update callers of _seed_targets
old_caller = "want_seeds = _seed_targets(day, total_days, planted, len(free_cells), harvest_n)"
new_caller = "want_seeds = _seed_targets(day, total_days, planted, len(free_cells), harvest_n, minv)"
content = content.replace(old_caller, new_caller)

# 5. Update callers of _plant_choice
old_pcaller = "crop = _plant_choice(day, total_days, planted, seeds)"
new_pcaller = "crop = _plant_choice(day, total_days, planted, seeds, minv)"
content = content.replace(old_pcaller, new_pcaller)

# 6. Update callers of should_buy_animal
old_acaller = """if day >= total_days - 6:
                continue"""
new_acaller = """if not should_buy_animal(animal, day, total_days, minv):
                continue"""
content = content.replace(old_acaller, new_acaller)


with open("policy.py", "w") as f:
    f.write(content)
