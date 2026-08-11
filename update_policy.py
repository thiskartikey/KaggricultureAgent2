import re

with open("policy.py", "r") as f:
    content = f.read()

# 1. Update _seed_targets signature and logic
old_seed_targets = """def _seed_targets(day, total_days, planted, free_n):
    \"\"\"How many seeds of each crop we still want to hold.\"\"\"
    left = total_days - day
    want = {}
    if left >= 13:
        want["MELON"] = max(0, min(TARGET_MELON - planted.get("MELON", 0), free_n))
        want["STRAWBERRY"] = max(
            0, min(TARGET_STRAWBERRY - planted.get("STRAWBERRY", 0),
                   free_n - want["MELON"]))
    if left >= 5:
        rest = free_n - want.get("MELON", 0) - want.get("STRAWBERRY", 0)
        want["WHEAT"] = max(8, min(max(0, rest), 30))
    return want"""

new_seed_targets = """def _seed_targets(day, total_days, planted, free_n, harvest_crop_n=0):
    \"\"\"How many seeds of each crop we still want to hold.\"\"\"
    left = total_days - day
    want = {}
    # Anticipate tiles becoming free so seeds are bought BEFORE harvest
    effective_free = free_n + harvest_crop_n
    
    if left >= 13:
        want["MELON"] = max(0, min(TARGET_MELON - planted.get("MELON", 0), effective_free))
        want["STRAWBERRY"] = max(
            0, min(TARGET_STRAWBERRY - planted.get("STRAWBERRY", 0),
                   effective_free - want["MELON"]))
    if left >= 5:
        # Keep a larger buffer of wheat seeds ready to drop into cleared tiles instantly
        rest = effective_free - want.get("MELON", 0) - want.get("STRAWBERRY", 0)
        want["WHEAT"] = max(15, min(max(0, rest), 30))
    return want"""

content = content.replace(old_seed_targets, new_seed_targets)

# 2. Update _make_market_orders signature and call
old_make_market = "def _make_market_orders(obs, player=0, total_days=30):"
new_make_market = "def _make_market_orders(obs, player=0, total_days=30, scan=None):"
content = content.replace(old_make_market, new_make_market)

old_want_seeds = "want_seeds = _seed_targets(day, total_days, planted, len(free_cells))"
new_want_seeds = "harvest_n = len(scan.get('harvest_crop', [])) if scan else 0\n    want_seeds = _seed_targets(day, total_days, planted, len(free_cells), harvest_n)"
content = content.replace(old_want_seeds, new_want_seeds)

# 3. Update the call inside _agent
old_orders = "orders = _make_market_orders(obs, player, total_days)"
new_orders = "orders = _make_market_orders(obs, player, total_days, scan)"
content = content.replace(old_orders, new_orders)


# 4. Melon pricing fix. We dump our own melon price!
# Let's fix R2: Market Pricing Strategy - prevent self-dumping.
# In `plan_sells`, we use `_RESERVE_FRAC`. MELON is 0.50.
# The market price of melon is base=250.
# If we dump, it means we sell so much the price plummets below acceptable value.
# wait, units_sellable_above ensures we don't sell below frac * base.
# 0.50 * 250 = 125. That's quite low.
old_reserve_frac = '"MELON": 0.50,'
new_reserve_frac = '"MELON": 0.80, # don\'t self dump melon'
content = content.replace(old_reserve_frac, new_reserve_frac)

with open("policy.py", "w") as f:
    f.write(content)
print("Updated policy.py")
