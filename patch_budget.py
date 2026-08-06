with open("revancedmain.py", "r") as f:
    code = f.read()

old_hire_loop = """    if hour <= 2:
        h = 0
        while hires_today + h < want:
            c = hire_cost(hires_today + h)
            if money_left < c + 50:
                break
            orders.append(["HIRE"])
            money_left -= c
            h += 1"""

new_hire_loop = """    if hour <= 2:
        h = 0
        expected_picks_cost = sum(CROP_SPECS[name]["seed"] for kind, name in picks if kind == "PLANT")
        expected_picks_cost += sum(ANIMAL_SPECS[name]["cost"] for kind, name in picks if kind == "ANIMAL")
        while hires_today + h < want:
            c = hire_cost(hires_today + h)
            if money_left - expected_picks_cost < c + 50:
                break
            orders.append(["HIRE"])
            money_left -= c
            h += 1"""

code = code.replace(old_hire_loop, new_hire_loop)

old_seed_buy = """    for c, n in want_seeds.items():
        n -= int(seeds.get(c, 0))
        n = min(n, 30)
        if n > 0 and money_left > CROP_SPECS[c]["seed"] * n + 100:
            orders.append(["BUY_SEED", c, n])
            money_left -= CROP_SPECS[c]["seed"] * n"""

new_seed_buy = """    for c, n in want_seeds.items():
        n -= int(seeds.get(c, 0))
        n = min(n, 30)
        if n > 0:
            affordable = int((money_left - 100) // CROP_SPECS[c]["seed"])
            buy_n = min(n, affordable)
            if buy_n > 0:
                orders.append(["BUY_SEED", c, buy_n])
                money_left -= CROP_SPECS[c]["seed"] * buy_n"""

code = code.replace(old_seed_buy, new_seed_buy)

with open("revancedmain.py", "w") as f:
    f.write(code)
print("Patched budget!")
