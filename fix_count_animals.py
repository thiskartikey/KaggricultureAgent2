import re

with open("revancedmain.py", "r") as f:
    content = f.read()

new_func = """def _count_animals(me, private=None):
    n = 0
    # Placed animals
    for row in me.get("tiles") or []:
        for t in row:
            if isinstance(t, dict) and t.get("kind") in ("COOP", "PASTURE") and t.get("animal"):
                n += 1
    # Unplaced animals in shed
    if private and "shed" in private:
        n += int(private["shed"].get("COW", 0))
        n += int(private["shed"].get("GOOSE", 0))
        n += int(private["shed"].get("SHEEP", 0))
    # Unplaced animals in worker inventories
    for inv in me.get("inventories") or []:
        if isinstance(inv, dict):
            n += int(inv.get("COW", 0))
            n += int(inv.get("GOOSE", 0))
            n += int(inv.get("SHEEP", 0))
    return n"""

content = re.sub(r'def _count_animals\(me, private=None\):.*?return n', new_func, content, flags=re.DOTALL)

with open("revancedmain.py", "w") as f:
    f.write(content)
