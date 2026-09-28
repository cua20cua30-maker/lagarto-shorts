import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "data" / "state.json"


def main():
    now = datetime.now(timezone.utc).isoformat()
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {}

    state["schema_version"] = 1
    state["last_run"] = now
    state["last_success"] = now
    state["runs"] = int(state.get("runs", 0)) + 1
    state["failures"] = int(state.get("failures", 0))
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"State: runs={state['runs']} failures={state['failures']}")


if __name__ == "__main__":
    main()
