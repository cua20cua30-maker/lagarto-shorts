"""Merge official Twitch VOD discovery with official Kick API live discovery."""
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data/candidates.json"
KICK_CANDIDATES = ROOT / "data/kick_candidates.json"
TWITCH_DIAG = ROOT / "data/stream_radar_diagnostics.json"
KICK_DIAG = ROOT / "data/kick_radar_diagnostics.json"
CONFIG = ROOT / "config/factory.json"

def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default

def main():
    kick = subprocess.run(
        ["python", "scripts/kick_radar.py"],
        cwd=ROOT,
        check=False,
    )
    if kick.returncode:
        print("Kick radar exited with code", kick.returncode)

    twitch_data = load(CANDIDATES, {"candidates": []})
    twitch = list(twitch_data.get("candidates", []))
    kick_candidates = load(KICK_CANDIDATES, {"candidates": []}).get("candidates", [])

    merged = {}
    for item in twitch + kick_candidates:
        candidate_id = item.get("candidate_id")
        if candidate_id:
            merged[candidate_id] = item

    ranked = sorted(
        merged.values(),
        key=lambda item: (
            float(item.get("score", 0) or 0),
            1 if item.get("source_platform") == "twitch" else 0,
        ),
        reverse=True,
    )

    limit = int(
        load(CONFIG, {}).get("limits", {}).get("max_candidates_per_run", 20) or 20
    )
    names = [
        creator["name"]
        for creator in load(ROOT / "config/creators.json", {"creators": []}).get("creators", [])
        if creator.get("enabled", True)
    ]

    selected = []
    ids = set()
    counts = Counter()

    # Guarantee representation from every creator when a source has a candidate.
    for name in names:
        options = [x for x in ranked if x.get("source_creator") == name]
        if options:
            selected.append(options[0])
            ids.add(options[0]["candidate_id"])
            counts[name] += 1

    cap = max(3, (limit + len(names) - 1) // max(1, len(names)))
    for item in ranked:
        if len(selected) >= limit:
            break
        cid = item.get("candidate_id")
        creator = item.get("source_creator")
        if cid in ids or counts[creator] >= cap:
            continue
        selected.append(item)
        ids.add(cid)
        counts[creator] += 1

    now = datetime.now(timezone.utc)
    diagnostics = load(TWITCH_DIAG, {"results": []}).get("results", [])
    diagnostics += load(KICK_DIAG, {"results": []}).get("results", [])

    CANDIDATES.write_text(
        json.dumps(
            {
                "schema_version": 4,
                "generated_at": now.isoformat(),
                "source_priority": ["twitch", "kick"],
                "discovery_policy": {
                    "twitch": "official Twitch API VOD discovery",
                    "kick": "official Kick Developer Public API live metadata discovery",
                    "kick_vod_history": "not available from the current official public API",
                    "undocumented_kick_scraping": False,
                },
                "total_discovered": len(ranked),
                "selection_limit": limit,
                "creator_coverage": {
                    name: sum(1 for item in selected if item.get("source_creator") == name)
                    for name in names
                },
                "platform_coverage": {
                    "twitch": sum(1 for item in selected if item.get("source_platform") == "twitch"),
                    "kick": sum(1 for item in selected if item.get("source_platform") == "kick"),
                },
                "candidates": selected,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Keep the combined diagnostics in the same file consumed by the self-test.
    (ROOT / "data/multisource_diagnostics.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "generated_at": now.isoformat(),
                "results": diagnostics,
                "platforms": {
                    "twitch": sum(1 for x in diagnostics if x.get("platform") == "twitch"),
                    "kick": sum(1 for x in diagnostics if x.get("platform") == "kick"),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"Multisource radar: twitch={sum(1 for x in selected if x.get('source_platform') == 'twitch')} "
        f"kick={sum(1 for x in selected if x.get('source_platform') == 'kick')} "
        f"total={len(selected)}"
    )

if __name__ == "__main__":
    main()
