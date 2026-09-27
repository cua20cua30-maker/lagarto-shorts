import json
import re
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "creators.json"
OUT = ROOT / "data" / "candidates.json"

def norm(value):
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())

def search(name, limit=12):
    query = f'ytsearchdate{limit}:"{name}"'
    process = subprocess.run(
        ["yt-dlp", "--dump-single-json", "--skip-download", "--playlist-end", str(limit), query],
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
    strong = (
        "reacción", "reaccion", "increíble", "increible", "polémica", "polemica",
        "humilla", "humilló", "explota", "locura", "nadie esperaba", "se lía",
        "se lia", "viral", "wtf", "qué coño", "que coño", "no puede ser",
        "llora", "llorando", "triste", "enfado", "cabreado", "sorpresa", "brutal",
    )
    return min(100, sum(10 for signal in strong if signal in text))

def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    candidates = []

    for creator in cfg["creators"]:
        if not creator.get("enabled", True):
            continue

        name = creator["name"]
        for item in search(name):
            video_id = item.get("id")
            if not video_id:
                continue

            uploader = item.get("channel") or item.get("uploader") or ""
            uploader_id = item.get("channel_id") or item.get("uploader_id") or ""

            # Full metadata mode normally supplies the uploader. If it does not,
            # keep the candidate in radar but mark attribution as unverified.
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
    OUT.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": now.isoformat(),
                "candidates": sorted(
                    dedup.values(),
                    key=lambda item: item["score"],
                    reverse=True,
                ),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"Radar v2: {len(dedup)} candidates")

if __name__ == "__main__":
    main()
