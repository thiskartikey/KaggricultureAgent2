import tarfile
import os

files_to_add = [
    ("ml_main.py", "main.py"),  # rename to main.py inside the tar
    ("policy.py", "policy.py"),
    ("rl_weights.npz", "rl_weights.npz"),
]

with tarfile.open("ml_submission.tar.gz", "w:gz") as tar:
    for local_path, tar_path in files_to_add:
        if os.path.exists(local_path):
            tar.add(local_path, arcname=tar_path)
        else:
            print(f"Warning: {local_path} not found.")

print("Created ml_submission.tar.gz")
