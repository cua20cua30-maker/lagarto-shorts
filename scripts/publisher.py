import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "publish_queue.json"

def main():
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    jobs = queue.get("jobs", [])

    required = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
    missing = [key for key in required if not os.environ.get(key)]

    if missing:
        print("Publisher: credentials not configured; upload stage remains safely blocked.")
        print("Missing:", ", ".join(missing))
        print(f"Queued jobs: {len(jobs)}")
        return

    # Authentication/upload implementation is intentionally isolated here.
    # It will use resumable YouTube uploads and idempotency keys once OAuth
    # credentials are provisioned.
    print("Publisher: OAuth credentials detected.")
    print(f"Queued jobs: {len(jobs)}")
    print("Publisher: upload adapter ready for OAuth/resumable implementation.")

if __name__ == "__main__":
    main()
