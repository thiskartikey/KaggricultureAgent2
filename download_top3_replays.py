"""
Download replays for the live top-3 leaderboard players.

Usage:
    python download_top3_replays.py

Replays are saved to:
    replays/<TeamName>/episode-<id>-replay.json

The script is idempotent: already-downloaded (and valid) files are skipped.
"""

import kaggle
import os
import time
import json
import re
from pathlib import Path

COMPETITION = "kaggriculture"
RETRY_ATTEMPTS = 4
RETRY_BACKOFF = 5  # seconds (multiplied by attempt number)


def safe_dirname(name: str) -> str:
    """Convert a team name to a safe directory name."""
    return re.sub(r'[^\w\-]', '_', name).strip('_') or "team"


def is_valid_replay(path: Path) -> bool:
    """Return True if the file exists, is non-empty, and is valid JSON."""
    if not path.exists() or path.stat().st_size < 10:
        return False
    try:
        content = path.read_text(encoding="utf-8").strip()
        if content == "None":
            return False
        json.loads(content)
        return True
    except Exception:
        return False


def download_episode(api, episode_id: int, out_dir: Path) -> bool:
    """Download one episode replay into out_dir. Returns True on success."""
    dest = out_dir / f"episode-{episode_id}-replay.json"
    if is_valid_replay(dest):
        return True  # already good

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            # This call writes episode-<id>-replay.json into the given path dir
            api.competition_episode_replay(episode_id, path=str(out_dir), quiet=True)
            if is_valid_replay(dest):
                return True
            # File written but content looks wrong — wait and retry
            time.sleep(2)
        except Exception as exc:
            wait = RETRY_BACKOFF * attempt
            print(f"      attempt {attempt}/{RETRY_ATTEMPTS} failed (ep {episode_id}): {exc}")
            time.sleep(wait)

    return False


def main():
    api = kaggle.api
    api.authenticate()

    # ── 1. Fetch live top-3 leaderboard ─────────────────────────────────────
    print(f"Fetching live leaderboard for '{COMPETITION}'...")
    board = api.competition_leaderboard_view(COMPETITION)
    top3 = board[:3]
    print("Top 3:")
    for rank, entry in enumerate(top3, 1):
        print(f"  #{rank}  {entry.team_name}  (teamId={entry.team_id})  score={entry.score}")

    # ── 2. Best submission per team ──────────────────────────────────────────
    print("\nResolving best submission per team...")
    teams = []
    for entry in top3:
        subs = api.competition_team_submissions(entry.team_id)
        best = max(
            subs,
            key=lambda s: float(s.get("publicScore") or 0)
            if isinstance(s, dict)
            else float(getattr(s, "public_score", None) or 0),
        )
        sub_id = best.get("id") if isinstance(best, dict) else best.id
        score  = best.get("publicScore") if isinstance(best, dict) else best.public_score
        # Use the raw team name as the folder name (printable as-is)
        folder = entry.team_name
        print(f"  {entry.team_name!r}  →  submission {sub_id}  (score={score})")
        teams.append({
            "team_name": entry.team_name,
            "folder":    folder,
            "sub_id":    sub_id,
            "score":     score,
        })

    # ── 3. Download replays ───────────────────────────────────────────────────
    for ti in teams:
        out_dir = Path("replays") / ti["folder"]
        out_dir.mkdir(parents=True, exist_ok=True)

        eps = api.competition_list_episodes(ti["sub_id"])
        completed = [e for e in eps if str(e.state).endswith("COMPLETED")]

        # Remove any previously bad files so they get re-downloaded
        for f in out_dir.glob("*.json"):
            if not is_valid_replay(f):
                f.unlink()

        existing = {f.name for f in out_dir.glob("*.json")}
        todo = [e for e in completed if f"episode-{e.id}-replay.json" not in existing]

        print(f"\n[{ti['team_name']}]  {len(completed)} episodes  "
              f"({len(existing)} already good, {len(todo)} to download)  → {out_dir}/")

        failed = []
        for i, ep in enumerate(todo, 1):
            ok = download_episode(api, ep.id, out_dir)
            if not ok:
                failed.append(ep.id)
                print(f"    ✗ FAILED ep {ep.id}")
            if i % 25 == 0:
                print(f"    ... {i}/{len(todo)}")

        total = len(list(out_dir.glob("*.json")))
        print(f"  ✓ {total}/{len(completed)} files on disk"
              + (f"  ({len(failed)} failed: {failed})" if failed else ""))

    print("\nDone.")


if __name__ == "__main__":
    main()
