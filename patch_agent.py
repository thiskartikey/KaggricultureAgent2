import re

with open("revancedmain.py", "r") as f:
    code = f.read()

# We need to move the HIRE block up.
# Find the HIRE block:
hire_pattern = r"""    work = len\(scan\["water"\]\) \+ len\(scan\["feed"\]\) \+ len\(scan\["harvest_crop"\]\) \\
        \+ len\(scan\["harvest_animal"\]\) \+ min\(len\(picks\), len\(free_cells\)\) \+ len\(scan\["weeds"\]\) \\
        \+ len\(scan\["care"\]\) \+ len\(scan\["collect"\]\)
    want = _desired_hands\(work, money_left\)
    hires_today = int\(me\.get\("hires_today", 0\)\)
    if hour <= 2:
        h = 0
        while hires_today \+ h < want:
            c = hire_cost\(hires_today \+ h\)
            if money_left < c \+ 50:
                break
            orders\.append\(\["HIRE"\]\)
            money_left -= c
            h \+= 1
"""

if re.search(hire_pattern, code):
    code = re.sub(hire_pattern, "", code)
    
    # Now insert it right before `orders += plan_sells`? No, after plan_sells so we know money_left?
    # Actually, before we buy WHEAT.
    insert_point = r"    orders \+= plan_sells\(shed, minv, day, hour, total_days, hold\)\n"
    new_code = insert_point + hire_pattern.replace(r"\(", "(").replace(r"\)", ")").replace(r"\+", "+").replace(r"\[", "[").replace(r"\]", "]").replace(r"\.", ".")
    
    code = re.sub(insert_point, new_code, code)
    
    with open("revancedmain.py", "w") as f:
        f.write(code)
    print("Patched!")
else:
    print("Could not find hire block!")
