import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / "data" / "analytics_snapshots.json"

def main():
    if SNAPSHOTS.exists():
        data = json.loads(SNAPSHOTS.read_text(encoding="utf-8"))
    else:
        data = {"schema_version": 1, "snapshots": []}

    assert data["schema_version"] == 1
    snapshots = data.setdefault("snapshots", [])

    # The collector is deliberately schema-first until OAuth/YouTube Analytics
    # credentials are connected. No synthetic metrics are ever generated.
    print(f"Analytics: {len(snapshots)} real snapshots stored")
    print(f"Checked at: {datetime.now(timezone.utc).isoformat()}")

if __name__ == "__main__":
    main()
