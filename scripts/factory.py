import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data" / "candidates.json"
STRATEGIES = ROOT / "data" / "edit_strategies.json"
RENDER_QUEUE = ROOT / "data" / "render_queue.json"
PUBLISH_QUEUE = ROOT / "data" / "publish_queue.json"

def load(path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def main():
    candidates = load(CANDIDATES, {"candidates": []}).get("candidates", [])
    strategies = {
        x["candidate_id"]: x
        for x in load(STRATEGIES, {"strategies": []}).get("strategies", [])
    }

    render_jobs = []
    publish_jobs = []
    for candidate in candidates:
        cid = candidate.get("candidate_id")
        strategy = strategies.get(cid)
        if not strategy:
            continue

        # Radar may discover aggressively, but publication remains gated.
        authorized = candidate.get("authorization_status") == "authorized"
        if not authorized:
            continue

        job = {
            "job_id": f"render:{cid}",
            "candidate_id": cid,
            "source_url": candidate.get("source_url"),
            "source_creator": candidate.get("source_creator"),
            "title": candidate.get("title"),
            "strategy": strategy,
            "status": "queued",
            "idempotency_key": f"short:{cid}",
        }
        render_jobs.append(job)

        publish_jobs.append({
            "job_id": f"publish:{cid}",
            "candidate_id": cid,
            "status": "blocked_until_rendered",
            "authorization_status": "authorized",
            "transformative_edit_required": True,
            "idempotency_key": f"publish:{cid}",
        })

    now = datetime.now(timezone.utc).isoformat()
    RENDER_QUEUE.write_text(json.dumps({
        "schema_version": 1, "generated_at": now, "jobs": render_jobs
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PUBLISH_QUEUE.write_text(json.dumps({
        "schema_version": 1, "generated_at": now, "jobs": publish_jobs
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Factory: {len(render_jobs)} authorized render jobs queued")
    print(f"Factory: {len(publish_jobs)} publish jobs gated")

if __name__ == "__main__":
    main()
