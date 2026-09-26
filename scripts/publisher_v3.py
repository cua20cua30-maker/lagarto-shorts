import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "publish_queue.json"
RENDER = ROOT / "data" / "render_queue.json"
LEDGER = ROOT / "data" / "published.json"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def main():
    queue = load(QUEUE, {"schema_version": 1, "jobs": []})
    render = load(RENDER, {"schema_version": 1, "jobs": []})
    ledger = load(LEDGER, {"schema_version": 1, "items": []})

    done = {
        item.get("idempotency_key"): item
        for item in ledger.get("items", [])
        if item.get("idempotency_key")
    }
    rendered = {
        item.get("clip_id"): item
        for item in render.get("jobs", [])
        if item.get("status") == "rendered" and item.get("clip_id")
    }

    if os.getenv("YOUTUBE_AUTO_PUBLISH", "false").lower() != "true":
        print("Publisher v3: auto-publish disabled; dry-run.")
        return

    required = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print("Publisher v3: OAuth secrets missing; blocked.")
        return

    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    creds.refresh(Request())
    youtube = build("youtube", "v3", credentials=creds)

    changed = False
    privacy = os.getenv("YOUTUBE_PRIVACY_STATUS", "unlisted")

    for job in queue.get("jobs", []):
        key = job.get("idempotency_key")
        clip_id = job.get("clip_id")
        item = rendered.get(clip_id)

        if not key or not clip_id or key in done or not item:
            continue

        path = Path(item["output"])
        if not path.exists():
            continue

        creator = item.get("source_creator", "Short")
        title = job.get("title") or f"Lagarto | {creator}"
        description = job.get(
            "description",
            "Short transformado a partir de material autorizado, con edición y contexto original.",
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title[:100],
                    "description": description[:5000],
                    "categoryId": "24",
                },
                "status": {
                    "privacyStatus": privacy,
                    "selfDeclaredMadeForKids": False,
                },
            },
            media_body=MediaFileUpload(
                str(path),
                mimetype="video/mp4",
                resumable=True,
            ),
        )

        response = None
        while response is None:
            _, response = request.next_chunk()

        record = {
            "idempotency_key": key,
            "clip_id": clip_id,
            "candidate_id": job.get("candidate_id"),
            "source_creator": creator,
            "video_id": response["id"],
            "privacy_status": privacy,
        }
        ledger["items"].append(record)
        done[key] = record
        job["status"] = "uploaded"
        job["video_id"] = response["id"]
        changed = True

    if changed:
        LEDGER.write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        QUEUE.write_text(
            json.dumps(queue, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(f"Publisher v3: ledger={len(ledger.get('items', []))}")


if __name__ == "__main__":
    main()
