import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "creators.json"
OUT = ROOT / "data" / "candidates.json"

def load():
    with CONFIG.open("r", encoding="utf-8") as f:
        return json.load(f)

def search(query, limit=10):
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-single-json",
        "--playlist-end", str(limit),
        f"ytsearch{limit}:{query}",
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if p.returncode != 0:
        return []
    try:
        data = json.loads(p.stdout)
    except json.JSONDecodeError:
        return []
    return data.get("entries", [])

def score(item):
    title = (item.get("title") or "").lower()
    signals = ["reacción", "reaccion", "increíble", "increible", "última hora",
               "ultima hora", "polémica", "polemica", "humilla", "humilló",
               "explota", "locura", "nadie esperaba", "se lía", "se lia", "viral"]
    return min(100, sum(12 for s in signals if s in title))

def main():
    config = load()
    candidates = []
    now = datetime.now(timezone.utc).isoformat()

    for creator in config["creators"]:
        if not creator.get("enabled", True):
            continue
        query = creator.get("search_query", creator["name"])
        for item in search(query):
            if not item.get("id"):
                continue
            candidates.append({
                "candidate_id": f"yt:{item['id']}",
                "source_creator": creator["name"],
                "source_url": f"https://www.youtube.com/watch?v={item['id']}",
                "title": item.get("title", ""),
                "duration_seconds": item.get("duration"),
                "score": score(item),
                "detected_at": now,
                "status": "discovered",
                "authorization_status": "unknown",
                "publishable": False
            })

    dedup = {x["candidate_id"]: x for x in candidates}
    result = {
        "schema_version": 1,
        "generated_at": now,
        "candidates": sorted(dedup.values(), key=lambda x: x["score"], reverse=True)
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Radar: {len(result['candidates'])} candidates discovered")

if __name__ == "__main__":
    main()
