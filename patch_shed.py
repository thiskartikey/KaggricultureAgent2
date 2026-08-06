with open("revancedmain.py", "r") as f:
    code = f.read()

# 1. Update shed_adjacent_cells
old_shed = """def shed_adjacent_cells(board_size=10):
    c1, c2 = board_size // 2 - 1, board_size // 2
    return [(c1, c1), (c1, c2), (c2, c1), (c2, c2)]"""

new_shed = """def shed_adjacent_cells(board_size, me):
    c1, c2 = board_size // 2 - 1, board_size // 2
    sheds = [(c1, c1), (c1, c2), (c2, c1), (c2, c2)]
    tiles = me.get("tiles", [])
    valid_sheds = []
    for (x, y) in sheds:
        if y < len(tiles) and x < len(tiles[y]) and tiles[y][x] != "LOCKED":
            valid_sheds.append((x, y))
    return valid_sheds if valid_sheds else sheds"""
code = code.replace(old_shed, new_shed)

# 2. Update at_shed
old_at = """def at_shed(pos, board_size):
    for c in shed_adjacent_cells(board_size):
        if pos == tuple(c): return True
    return False"""

new_at = """def at_shed(pos, board_size, me):
    for c in shed_adjacent_cells(board_size, me):
        if pos == tuple(c): return True
    return False"""
code = code.replace(old_at, new_at)

# 3. Update _go_to_shed
old_go = """def _go_to_shed(pos, board_size):
    sheds = shed_adjacent_cells(board_size)"""
new_go = """def _go_to_shed(pos, board_size, me):
    sheds = shed_adjacent_cells(board_size, me)"""
code = code.replace(old_go, new_go)

# 4. Update usages in _unit_op
old_unit_op_def = """def _unit_op(pos, task, private, gi, board_size, feed_need=1):"""
new_unit_op_def = """def _unit_op(pos, task, private, gi, board_size, me, feed_need=1):"""
code = code.replace(old_unit_op_def, new_unit_op_def)

code = code.replace("at_shed(pos, board_size)", "at_shed(pos, board_size, me)")
code = code.replace("_go_to_shed(pos, board_size)", "_go_to_shed(pos, board_size, me)")

# 5. Update _unit_op call in _agent
old_call = """ops_out[gi] = _unit_op(positions[gi], task, private, gi, board, feed_need)"""
new_call = """ops_out[gi] = _unit_op(positions[gi], task, private, gi, board, me, feed_need)"""
code = code.replace(old_call, new_call)

# 6. Update shed_adjacent_cells calls in _agent
old_agent_shed = """sheds = shed_adjacent_cells(board)"""
new_agent_shed = """sheds = shed_adjacent_cells(board, me)"""
code = code.replace(old_agent_shed, new_agent_shed)

# 7. Update assign_tasks call
old_assign_def = """def assign_tasks(unit_positions, tasks, day, hour, invs, board_size):"""
new_assign_def = """def assign_tasks(unit_positions, tasks, day, hour, invs, board_size, me):"""
code = code.replace(old_assign_def, new_assign_def)

old_assign_shed = """sheds = shed_adjacent_cells(board_size)"""
new_assign_shed = """sheds = shed_adjacent_cells(board_size, me)"""
code = code.replace(old_assign_shed, new_assign_shed)

old_assign_call = """assign = assign_tasks([positions[i] for i in free_units], tasks, day, hour, [invs[i] if i < len(invs) else {} for i in free_units], board)"""
new_assign_call = """assign = assign_tasks([positions[i] for i in free_units], tasks, day, hour, [invs[i] if i < len(invs) else {} for i in free_units], board, me)"""
code = code.replace(old_assign_call, new_assign_call)


with open("revancedmain.py", "w") as f:
    f.write(code)
print("Patched!")
