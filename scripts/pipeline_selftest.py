import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    with (ROOT / path).open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    creators = read(Path("config/creators.json"))
    auth = read(Path("data/authorization_manifest.json"))
    characters = read(Path("config/character_profiles.json"))
    appearances = read(Path("config/character_appearances.json"))
    candidates = read(Path("data/candidates.json"))
    moments = read(Path("data/moments.json"))
    plans = read(Path("data/clip_plans.json"))
    publish_queue = read(Path("data/publish_queue.json"))
    queue = read(Path("data/render_queue.json"))
    analytics = read(Path("data/analytics_snapshots.json"))
    learning = read(Path("data/learning_records.json"))
    published = read(Path("data/published.json"))
    emotions = read(Path("data/emotion_events.json"))
    trends = read(Path("data/hashtag_trends.json"))
    recovery = read(Path("data/publication_recovery.json"))
    radar_diagnostics = read(Path("data/radar_diagnostics.json"))

    assert len(creators["creators"]) == 11
    assert len(characters["characters"]) == 11
    assert len(appearances["characters"]) == 11
    assert appearances["style"]["body"] == "stick"
    assert auth["schema_version"] == 1 and isinstance(auth["authorized_sources"], list)
    assert candidates["schema_version"] >= 1 and isinstance(candidates["candidates"], list)
    assert moments["schema_version"] >= 2 and isinstance(moments["moments"], list)
    assert plans["schema_version"] == 1 and isinstance(plans["plans"], list)
    assert queue["schema_version"] == 1 and isinstance(queue["jobs"], list)
    assert publish_queue["schema_version"] == 1 and isinstance(publish_queue["jobs"], list)
    assert analytics["schema_version"] >= 1 and isinstance(analytics["snapshots"], list)
    assert isinstance(learning, list) or isinstance(learning.get("records"), list)
    assert emotions["schema_version"] == 1 and isinstance(emotions["events"], list)
    assert trends["schema_version"] == 1 and isinstance(trends["jobs"], list)
    assert recovery["schema_version"] == 1 and isinstance(recovery["items"], list)
    assert published["schema_version"] == 1 and isinstance(published["items"], list)
    assert radar_diagnostics["schema_version"] == 1
    assert radar_diagnostics["creators_configured"] == 11
    assert isinstance(radar_diagnostics["results"], list)
    assert len(radar_diagnostics["results"]) == radar_diagnostics["creators_enabled"]

    configured = {creator["name"] for creator in creators["creators"]}
    assert len(configured) == 11

    authorized = set(auth["authorized_sources"])
    for c in candidates["candidates"]:
        assert c["publishable"] is False or c["authorization_status"] == "authorized"
        if c["source_url"] not in authorized:
            assert c["publishable"] is False

    selected_creators = set(candidates.get("creator_coverage", {}))
    assert selected_creators.issubset(configured)

    print(
        f"Pipeline self-test: OK; creators={len(configured)} "
        f"candidates={len(candidates['candidates'])} "
        f"covered={len(selected_creators)} "
        f"moments={len(moments['moments'])} plans={len(plans['plans'])}"
    )


if __name__ == "__main__":
    main()
