import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "creators.json"
OUT = ROOT / "data" / "candidates.json"
DIAGNOSTICS = ROOT / "data" / "radar_diagnostics.json"


def norm(value):
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def search(name, youtube_url=None, limit=20):
    query = youtube_url or f'ytsearchdate{limit}:"{name}"'
    process = subprocess.run(
        [
            "yt-dlp",
            "--flat-playlist",
            "--dump-single-json",
            "--playlist-end",
            str(limit),
            query,
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if process.returncode:
        return [], {
            "status": "error",
            "query": query,
            "returncode": process.returncode,
            "stderr": (process.stderr or "")[-1000:],
        }
    try:
        entries = json.loads(process.stdout).get("entries", [])
        return entries, {
            "status": "ok",
            "query": query,
            "count": len(entries),
        }
    except json.JSONDecodeError:
        return [], {
            "status": "invalid_json",
            "query": query,
            "returncode": process.returncode,
            "stderr": (process.stderr or "")[-1000:],
        }


def score(title, recency_rank=0):
    text = (title or "").lower()
    signals = (
        "reacción", "reaccion", "increíble", "increible", "polémica", "polemica",
        "humilla", "humilló", "explota", "locura", "nadie esperaba", "se lía",
        "se lia", "viral", "wtf", "qué coño", "que coño", "no puede ser",
        "llora", "llorando", "triste", "enfado", "cabreado", "sorpresa", "brutal",
        "😭", "🥹", "💔", "😂", "😱", "😡", "😳", "💀", "🤯",
    )
    signal_score = sum(10 for signal in signals if signal in text)
    recency_score = max(0, 20 - int(recency_rank))
    return min(100, signal_score + recency_score)


def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    candidates = []
    diagnostics = []

    for creator in cfg["creators"]:
        if not creator.get("enabled", True):
            continue

        name = creator["name"]
        entries, diagnostic = search(name, creator.get("youtube_url"))
        diagnostic["creator"] = name
        diagnostic["youtube_url"] = creator.get("youtube_url")
        diagnostics.append(diagnostic)

        for rank, item in enumerate(entries):
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
                "score": score(title, rank),
                "radar_rank": rank,
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

    enabled_creators = [creator["name"] for creator in cfg["creators"] if creator.get("enabled", True)]
    selected = []
    selected_ids = set()
    per_creator = Counter()

    # First guarantee one recent candidate per creator when that creator
    # actually produced a valid candidate. Then use the remaining capacity
    # for the strongest candidates globally, while retaining a per-creator cap.
    for creator in enabled_creators:
        creator_candidates = [item for item in ranked if item["source_creator"] == creator]
        if creator_candidates:
            candidate = creator_candidates[0]
            selected.append(candidate)
            selected_ids.add(candidate["candidate_id"])
            per_creator[creator] += 1

    per_creator_cap = max(3, (max_candidates + len(enabled_creators) - 1) // len(enabled_creators))

    for candidate in ranked:
        if len(selected) >= max_candidates:
            break
        if candidate["candidate_id"] in selected_ids:
            continue
        creator = candidate["source_creator"]
        if per_creator[creator] >= per_creator_cap:
            continue
        selected.append(candidate)
        selected_ids.add(candidate["candidate_id"])
        per_creator[creator] += 1

    DIAGNOSTICS.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": now.isoformat(),
                "creators_configured": len(cfg["creators"]),
                "creators_enabled": len(enabled_creators),
                "creators_with_candidates": sorted(
                    {item["source_creator"] for item in ranked}
                ),
                "creators_selected": sorted(
                    {item["source_creator"] for item in selected}
                ),
                "results": diagnostics,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    OUT.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "generated_at": now.isoformat(),
                "total_discovered": len(ranked),
                "selection_limit": max_candidates,
                "creator_coverage": {
                    creator: sum(1 for item in selected if item["source_creator"] == creator)
                    for creator in enabled_creators
                },
                "candidates": selected,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(
        f"Radar v2: discovered={len(ranked)} selected={len(selected)} "
        f"creators={len(enabled_creators)} covered={len({item['source_creator'] for item in selected})}"
    )


if __name__ == "__main__":
    main()
