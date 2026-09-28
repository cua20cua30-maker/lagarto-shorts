import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def main():
    candidates = load(ROOT / "data" / "candidates.json", {"candidates": []}).get("candidates", [])
    allowed = set(load(ROOT / "data" / "authorization_manifest.json", {"authorized_sources": []}).get("authorized_sources", []))
    cc_sources = load(ROOT / "data" / "licensed_sources.json", {"sources": []}).get("sources", [])
    allowed.update(s.get("source_url") for s in cc_sources if s.get("license_verified"))
    published = load(ROOT / "data" / "published.json", {"items": []}).get("items", [])
    published_clips = {item.get("clip_id") for item in published if item.get("clip_id")}

    strategies_data = load(ROOT / "data" / "edit_strategies.json", {"strategies": []})
    strategies = {item["candidate_id"]: item for item in strategies_data.get("strategies", []) if item.get("candidate_id")}

    render = []
    publish = []

    for candidate in candidates:
        candidate_id = candidate.get("candidate_id")
        source_url = candidate.get("source_url")
        if not candidate_id or (source_url not in allowed and candidate.get("authorization_status") != "authorized_owner") or not candidate.get("acquirable", False):
            continue

        strategy = strategies.get(candidate_id)
        if not strategy:
            continue

        clip_id = f"clip:{candidate_id}"
        if clip_id in published_clips:
            continue

        render.append({
            "job_id": f"render:{clip_id}",
            "clip_id": clip_id,
            "candidate_id": candidate_id,
            "source_url": source_url,
            "source_creator": candidate.get("source_creator"),
            "title": candidate.get("title"),
            "strategy": strategy,
            "status": "queued",
            "idempotency_key": f"render:{clip_id}",
        })

        publish.append({
            "job_id": f"publish:{clip_id}",
            "clip_id": clip_id,
            "candidate_id": candidate_id,
            "source_creator": candidate.get("source_creator"),
            "title": strategy.get("generated_title") or f"Lagarto | {candidate.get('source_creator', 'Short')}",
            "description": "Short transformado a partir de material autorizado, con edición y contexto original.",
            "status": "blocked_until_rendered",
            "authorization_status": "authorized",
            "transformative_edit_required": True,
            "idempotency_key": f"publish:{clip_id}",
        })

    now = datetime.now(timezone.utc).isoformat()
    (ROOT / "data" / "render_queue.json").write_text(
        json.dumps({"schema_version": 1, "generated_at": now, "jobs": render}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (ROOT / "data" / "publish_queue.json").write_text(
        json.dumps({"schema_version": 1, "generated_at": now, "jobs": publish}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Factory v3: authorized render={len(render)} publish={len(publish)}")

if __name__ == "__main__":main()
