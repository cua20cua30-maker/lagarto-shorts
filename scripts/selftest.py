import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    with (ROOT / path).open("r", encoding="utf-8") as f:
        return json.load(f)

def main():
    creators = read("config/creators.json")
    factory = read("config/factory.json")
    candidates = read("data/candidates.json")
    records = read("data/learning_records.json")
    patterns = read("data/learned_patterns.json")
    profiles = read("config/creator_style_profiles.json")
    strategies = read("data/edit_strategies.json")
    render_queue = read("data/render_queue.json")
    publish_queue = read("data/publish_queue.json")
    analytics = read("data/analytics_snapshots.json")

    assert len(creators["creators"]) == 11
    creator_names = {c["name"] for c in creators["creators"]}
    assert factory["content_policy"]["require_authorization"] is True
    assert factory["content_policy"]["allow_unlicensed_reposting"] is False
    assert candidates["schema_version"] == 1
    assert isinstance(candidates["candidates"], list)
    assert isinstance(records, list)
    assert patterns["schema_version"] in {1, 2}
    assert isinstance(patterns["patterns"], list)
    assert isinstance(patterns.get("creator_patterns", {}), dict)
    assert set(profiles["profiles"]) == creator_names
    assert isinstance(strategies["strategies"], list)
    assert render_queue["schema_version"] == 1
    assert publish_queue["schema_version"] == 1
    assert analytics["schema_version"] == 1
    assert isinstance(render_queue["jobs"], list)
    assert isinstance(publish_queue["jobs"], list)
    assert isinstance(analytics["snapshots"], list)

    for candidate in candidates["candidates"]:
        assert candidate["authorization_status"] in {"unknown", "authorized", "rejected"}
        assert candidate["publishable"] is False or candidate["authorization_status"] == "authorized"

    for strategy in strategies["strategies"]:
        assert strategy["source_creator"] in creator_names
        assert strategy["publish_gate"]["authorization_required"] is True
        assert strategy["publish_gate"]["transformative_edit_required"] is True

    print("Self-test: OK")
    print(f"Candidates: {len(candidates['candidates'])}")
    print(f"Learned patterns: {len(patterns['patterns'])}")
    print(f"Strategies: {len(strategies['strategies'])}")

if __name__ == "__main__":
    main()
