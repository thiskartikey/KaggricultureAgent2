with open("policy.py", "r") as f:
    content = f.read()

old_loop = """    # 2. Fill the rest tier by tier, closest pair first.
    for tier in range(N_TIERS):
        pool = [t for t in tasks
                if TASK_TIER.get(t[0], 3) == tier and (t[0], _task_cell(t)) not in taken]
        if not pool:
            continue
        # A hungry animal can only be fed by somebody actually holding wheat.
        # Sending the merely-closest worker meant it arrived empty, did the
        # care/collect chores instead, and left the animal to starve.
        feed_cells = feed_cells or set()
        have_wheat = any(int((invs[ui] if ui < len(invs) else {}).get("WHEAT", 0)) > 0
                         for ui in free)
        pairs = []
        for ui in free:
            for t in pool:
                cell = _task_cell(t)
                if cell is None:
                    continue
                inv = invs[ui] if ui < len(invs) else {}
                carrying = int(inv.get("WHEAT", 0)) > 0
                if t[0] == "fertilize" and int(inv.get("FERTILIZER", 0)) <= 0:
                    continue      # only workers already carrying fertilizer
                hungry = t[0] in ("service", "service_soon") and cell in feed_cells
                if hungry and have_wheat and not carrying:
                    continue      # let a worker with feed take this one
                d = manhattan(positions[ui], cell)
                if hungry and carrying:
                    d -= 3
                pairs.append((d, ui, (t[0], cell), t))
        pairs.sort(key=lambda p: (p[0], p[1]))
        for d, ui, key, t in pairs:
            if ui not in free or key in taken:
                continue
            assignment[ui] = t
            taken.add(key)
            free.discard(ui)
        if not free:
            break"""

new_loop = """    # 2. Fill the rest by a global score, strongly preferring d=0 for non-urgent tasks.
    feed_cells = feed_cells or set()
    have_wheat = any(int((invs[ui] if ui < len(invs) else {}).get("WHEAT", 0)) > 0 for ui in free)
    pairs = []
    
    for ui in free:
        for t in tasks:
            key = (t[0], _task_cell(t))
            if key in taken:
                continue
            tier = TASK_TIER.get(t[0], 3)
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
        free.discard(ui)"""

content = content.replace(old_loop, new_loop)
with open("policy.py", "w") as f:
    f.write(content)
print("Updated routing in policy.py")
