import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "creators.json"
OUT = ROOT / "data" / "candidates.json"

def norm(value):
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())

def search(name, youtube_url=None, limit=20):
    query = youtube_url or f'ytsearchdate{limit}:"{name}"'
    process = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--dump-single-json", "--playlist-end", str(limit), query],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if process.returncode:
        return []
    try:
        return json.loads(process.stdout).get("entries", [])
    except json.JSONDecodeError:
        return []

def score(title):
    text = (title or "").lower()
    signals = (
        "reacción", "reaccion", "increíble", "increible", "polémica", "polemica",
        "humilla", "humilló", "explota", "locura", "nadie esperaba", "se lía",
        "se lia", "viral", "wtf", "qué coño", "que coño", "no puede ser",
        "llora", "llorando", "triste", "enfado", "cabreado", "sorpresa", "brutal",
    )
    return min(100, sum(10 for signal in signals if signal in text))

def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    candidates = []

    for creator in cfg["creators"]:
        if not creator.get("enabled", True):
            continue

        name = creator["name"]
        for item in search(name, creator.get("youtube_url")):
            video_id = item.get("id")
            if not video_id:
                continue

            uploader = item.get("channel") or item.get("uploader") or ""
            uploader_id = item.get("channel_id") or item.get("uploader_id") or ""
            verified = bool(uploader and norm(uploader) == norm(name))
            if uploader and not verified:
                continue

            date = item.get("upload_date")
            if date:
                try:
                    published = datetime.strptime(date, "%Y%m%d").replace(tzinfo=timezone.utc)
                    if published < cutoff:
                        continue
                except ValueError:
                    pass

            title = item.get("title", "")
            candidates.append({
                "candidate_id": f"yt:{video_id}",
                "source_creator": name,
                "source_url": f"https://www.youtube.com/watch?v={video_id}",
                "title": title,
                "duration_seconds": item.get("duration"),
                "score": score(title),
                "detected_at": now.isoformat(),
                "status": "discovered",
                "authorization_status": "unknown",
                "publishable": False,
                "uploader_verified": verified,
                "uploader": uploader,
                "uploader_id": uploader_id,
            })

    dedup = {candidate["candidate_id"]: candidate for candidate in candidates}
    ranked = sorted(dedup.values(), key=lambda item: item["score"], reverse=True)

    max_candidates = 20
    try:
        factory = json.loads((ROOT / "config" / "factory.json").read_text(encoding="utf-8"))
        max_candidates = max(
            1,
            int(factory.get("limits", {}).get("max_candidates_per_run", 20)),
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass

    selected = []
    per_creator = Counter()
    per_creator_cap = max(3, (max_candidates + len(cfg["creators"]) - 1) // len(cfg["creators"]))

    for candidate in ranked:
        creator = candidate["source_creator"]
        if per_creator[creator] >= per_creator_cap:
            continue
        selected.append(candidate)
        per_creator[creator] += 1
        if len(selected) >= max_candidates:
            break

    OUT.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": now.isoformat(),
                "total_discovered": len(ranked),
                "selection_limit": max_candidates,
                "candidates": selected,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"Radar v2: discovered={len(ranked)} selected={len(selected)}")

if __name__ == "__main__":
    main()
