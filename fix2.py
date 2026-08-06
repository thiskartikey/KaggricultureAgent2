with open("revancedmain.py", "r") as f:
    code = f.read()

# Fix shed_adjacent_cells
old_shed = """def shed_adjacent_cells(board_size=10):
    cells = []
    c1, c2 = board_size // 2 - 1, board_size // 2
    sheds = [(c1, c1), (c1, c2), (c2, c1), (c2, c2)]
    for sx, sy in sheds:
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = sx + dx, sy + dy
            if 0 <= nx < board_size and 0 <= ny < board_size and (nx, ny) not in sheds:
                cells.append((nx, ny))
    return list(set(cells))"""

new_shed = """def shed_adjacent_cells(board_size=10):
    c1, c2 = board_size // 2 - 1, board_size // 2
    return [(c1, c1), (c1, c2), (c2, c1), (c2, c2)]"""

code = code.replace(old_shed, new_shed)

# Fix _drop_task_needed
old_drop = """def _drop_task_needed(inv):
    total = 0
    for k, v in (inv or {}).items():
        if k == "WHEAT":
            continue
        total += int(v)
    return total >= 5 or (int((inv or {}).get("WHEAT", 0)) > 20)"""

new_drop = """def _drop_task_needed(inv):
    total = 0
    for k, v in (inv or {}).items():
        if k in SELL_PRODUCE and k != "WHEAT":
            total += int(v)
    return total >= 5 or (int((inv or {}).get("WHEAT", 0)) > 20)"""

code = code.replace(old_drop, new_drop)

with open("revancedmain.py", "w") as f:
    f.write(code)

print("Fixed!")
