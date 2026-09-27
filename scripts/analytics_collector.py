import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "published.json"
SNAPSHOTS = ROOT / "data" / "analytics_snapshots.json"
LEARNING = ROOT / "data" / "learning_records.json"
STRATEGIES = ROOT / "data" / "edit_strategies.json"

# Current YouTube Analytics reports.query authorization requires youtube.readonly.
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

METRICS = ",".join([
    "views", "engagedViews", "likes", "comments", "shares",
    "estimatedMinutesWatched", "averageViewDuration",
    "averageViewPercentage", "subscribersGained",
])

CHECKPOINTS = (1, 3, 7, 30)


def load(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def credentials():
    required = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
    if any(not os.getenv(name) for name in required):
        return None
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def checkpoint_for(published_at):
    try:
        published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    age = (datetime.now(timezone.utc) - published).total_seconds() / 86400
    eligible = [days for days in CHECKPOINTS if age >= days]
    return max(eligible) if eligible else None


def main():
    if not all(os.getenv(name) for name in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")):
        print("Analytics collector: OAuth secrets missing; skipped safely.")
        return

    ledger = load(LEDGER, {"schema_version": 1, "items": []})
    snapshots = load(SNAPSHOTS, {"schema_version": 2, "snapshots": []})
    learning = load(LEARNING, [])
    strategies = {
        item.get("candidate_id"): item
        for item in load(STRATEGIES, {"strategies": []}).get("strategies", [])
    }
    if not isinstance(learning, list):
        learning = learning.get("records", [])

    try:
        creds = credentials()
        analytics = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    except Exception as exc:
        print(f"Analytics collector: OAuth/API setup failed; skipped safely: {exc}")
        return

    existing_snapshot_keys = {
        item.get("snapshot_key")
        for item in snapshots.get("snapshots", [])
        if item.get("snapshot_key")
    }
    existing_learning_keys = {
        item.get("record_id")
        for item in learning
        if isinstance(item, dict) and item.get("record_id")
    }

    changed = False
    learning_changed = False

    for item in ledger.get("items", []):
        video_id = item.get("video_id")
        published_at = item.get("published_at")
        if not video_id:
            continue

        if not published_at:
            try:
                details = youtube.videos().list(part="snippet", id=video_id).execute().get("items", [])
                published_at = details[0]["snippet"]["publishedAt"] if details else None
            except Exception as exc:
                print(f"Analytics collector: cannot resolve publish date for {video_id}: {exc}")
                continue

        checkpoint = checkpoint_for(published_at)
        if checkpoint is None:
            continue

        snapshot_key = f"{video_id}:d{checkpoint}"
        if snapshot_key in existing_snapshot_keys:
            continue

        try:
            published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            start_date = published.date().isoformat()
        except (AttributeError, ValueError):
            continue

        checkpoint_end = (published + timedelta(days=checkpoint)).date()
        latest_complete = datetime.now(timezone.utc).date() - timedelta(days=1)
        end_date = min(checkpoint_end, latest_complete).isoformat()
        if end_date < start_date:
            continue

        try:
            response = analytics.reports().query(
                ids="channel==MINE",
                startDate=start_date,
                endDate=end_date,
                metrics=METRICS,
                dimensions="video",
                filters=f"video=={video_id}",
            ).execute()
        except HttpError as exc:
            print(f"Analytics collector: video {video_id} query failed: {exc}")
            continue
        except Exception as exc:
            print(f"Analytics collector: video {video_id} query failed: {exc}")
            continue

        rows = response.get("rows", [])
        if not rows:
            print(f"Analytics collector: no data yet for {video_id}")
            continue

        headers = response.get("columnHeaders", [])
        row = dict(zip((h.get("name") for h in headers), rows[0]))

        snapshot = {
            "snapshot_key": snapshot_key,
            "schema_version": 2,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "checkpoint_days": checkpoint,
            "video_id": video_id,
            "clip_id": item.get("clip_id"),
            "candidate_id": item.get("candidate_id"),
            "source_creator": item.get("source_creator"),
            "published_at": published_at,
            "metrics": {
                key: row.get(key)
                for key in (
                    "views", "engagedViews", "likes", "comments", "shares",
                    "estimatedMinutesWatched", "averageViewDuration",
                    "averageViewPercentage", "subscribersGained"
                )
                if key in row
            },
        }
        snapshots.setdefault("snapshots", []).append(snapshot)
        existing_snapshot_keys.add(snapshot_key)
        changed = True

        metadata = item.get("learning_metadata") or {}
        if not metadata:
            metadata = strategies.get(item.get("candidate_id"), {})

        record = {
            "record_id": snapshot_key,
            "source_creator": item.get("source_creator", "unknown"),
            "source_url": "",
            "candidate_id": item.get("candidate_id"),
            "format": metadata.get("format", "vertical_9_16"),
            "duration_seconds": metadata.get("duration_seconds"),
            "hook_type": metadata.get("hook_type", "unknown"),
            "edit_style": metadata.get("edit_style", "unknown"),
            "published_at": published_at,
            "metrics": {
                "views": row.get("views"),
                "likes": row.get("likes"),
                "comments": row.get("comments"),
                "shares": row.get("shares"),
                "average_view_duration": row.get("averageViewDuration"),
                "average_percentage_viewed": row.get("averageViewPercentage"),
                "subscribers_gained": row.get("subscribersGained"),
                "engaged_views": row.get("engagedViews"),
            },
            "outcome": "checkpoint",
            "experiment_id": f"d{checkpoint}",
            "learning_tags": ["youtube_analytics", f"checkpoint_{checkpoint}d"],
            "emotion_signals": metadata.get("emotion_signals", []),
            "emotion_score": metadata.get("emotion_score", 0),
            "hashtags": metadata.get("hashtags", []),
            "hashtag_sources": metadata.get("hashtag_sources", []),
        }
        if snapshot_key not in existing_learning_keys:
            learning.append(record)
            existing_learning_keys.add(snapshot_key)
            learning_changed = True

    if changed:
        snapshots["schema_version"] = 2
        snapshots["updated_at"] = datetime.now(timezone.utc).isoformat()
        save(SNAPSHOTS, snapshots)
    if learning_changed:
        save(LEARNING, learning)

    print(
        f"Analytics collector: snapshots={len(snapshots.get('snapshots', []))} "
        f"learning_records={len(learning)}"
    )


if __name__ == "__main__":
    main()
