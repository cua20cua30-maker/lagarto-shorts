import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_json(relative):
    path = ROOT / relative
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def main():
    creators = load_json("config/creators.json")
    factory = load_json("config/factory.json")
    state = load_json("data/state.json")

    assert creators["version"] == 1
    assert len(creators["creators"]) == 11
    assert factory["content_policy"]["require_authorization"] is True
    assert factory["content_policy"]["allow_unlicensed_reposting"] is False
    assert state["schema_version"] == 1

    print("Lagarto Shorts foundation: OK")
    print(f"Creators configured: {len(creators['creators'])}")
    print(f"Mode: {factory['mode']}")

if __name__ == "__main__":
    main()
