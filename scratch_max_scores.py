"""
Quick analysis: find the highest single-player score in all training replays.
Also break down what the top scorers are doing vs our heuristic.
"""
import json, os, glob

REPLAY_DIR = "downloads/training"
PROTECTED_DIR = "downloads/protected"

def get_scores(file_path):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        scores = data.get("rewards", [])
        return scores
    except Exception as e:
        return []

all_scores = []

for replay_dir in [REPLAY_DIR, PROTECTED_DIR]:
    for fp in glob.glob(f"{replay_dir}/*.json"):
        scores = get_scores(fp)
        if scores:
            for i, s in enumerate(scores):
                if isinstance(s, (int, float)):
                    all_scores.append((s, fp, i))

all_scores.sort(reverse=True)
print("Top 20 individual player scores in training/protected replays:")
for score, fp, player_idx in all_scores[:20]:
    print(f"  {score:>10,.0f}  player={player_idx}  {os.path.basename(fp)}")

print(f"\nMedian: {sorted([s for s,_,_ in all_scores])[len(all_scores)//2]:,.0f}")
print(f"Mean: {sum(s for s,_,_ in all_scores) / len(all_scores):,.0f}")
