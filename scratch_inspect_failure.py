import json

def peek_actions(file_path):
    print(f"\n--- Peeking actions for {file_path} ---")
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    steps = data.get("steps", [])
    if not steps:
        print("No steps found.")
        return

    for t, step in enumerate(steps[:15]):
        print(f"Step {t}:")
        for p_idx in [0, 1]:
            action = step[p_idx].get("action")
            if action:
                print(f"  Player {p_idx} action: type={type(action)} -> {action}")
        print("-" * 20)

if __name__ == "__main__":
    peek_actions("downloads/p2_v2_failure/f2/91734538.json")
