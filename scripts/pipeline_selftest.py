import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    with (ROOT / path).open("r", encoding="utf-8") as f:
        return json.load(f)

def main():
    creators = read(Path("config/creators.json"))
    auth = read(Path("data/authorization_manifest.json"))
    licensed = read(Path("data/licensed_sources.json"))
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
    trend_research = read(Path("data/trend_research.json")) if (ROOT / "data" / "trend_research.json").exists() else {"schema_version": 0}
    radar_path = ROOT / "data" / "multisource_diagnostics.json"
    if radar_path.exists():
        radar_diagnostics = read(Path("data/multisource_diagnostics.json"))
    else:
        radar_diagnostics = read(Path("data/stream_radar_diagnostics.json"))

    assert len(creators["creators"]) == 11
    assert len(characters["characters"]) == 11
    assert len(appearances["characters"]) == 11
    assert appearances["style"]["body_style"] == "stick"
    assert auth["schema_version"] == 1 and isinstance(auth["authorized_sources"], list)
    assert licensed["schema_version"] == 1 and isinstance(licensed["sources"], list)
    assert all(s.get("license_verified") is True for s in licensed["sources"])
    assert candidates["schema_version"] >= 1 and isinstance(candidates["candidates"], list)
    assert candidates.get("mode") == "vod_only"
    assert all(c.get("source_kind") == "vod" for c in candidates["candidates"])
    assert moments["schema_version"] >= 2 and isinstance(moments["moments"], list)
    assert plans["schema_version"] == 1 and isinstance(plans["plans"], list)
    assert queue["schema_version"] == 1 and isinstance(queue["jobs"], list)
    assert publish_queue["schema_version"] == 1 and isinstance(publish_queue["jobs"], list)
    assert analytics["schema_version"] >= 1 and isinstance(analytics["snapshots"], list)
    assert isinstance(learning, list) or isinstance(learning.get("records"), list)
    assert emotions["schema_version"] == 1 and isinstance(emotions["events"], list)
    assert trends["schema_version"] == 1 and isinstance(trends["jobs"], list)
    assert recovery["schema_version"] == 1 and isinstance(recovery["items"], list)
    assert trend_research["schema_version"] >= 2
    assert isinstance(radar_diagnostics["results"], list)

    radar_results = radar_diagnostics["results"]
    twitch_results = [r for r in radar_results if r.get("platform") == "twitch"]
    kick_results = [r for r in radar_results if r.get("platform") == "kick"]
    assert twitch_results
    assert all(r.get("status") == "vod_unavailable_official_api" for r in kick_results)

    configured = {creator["name"] for creator in creators["creators"]}
    assert len(configured) == 11

    authorized = set(auth["authorized_sources"]) | {
        s.get("source_url")
        for s in licensed["sources"]
        if s.get("license_verified")
    }
    for c in candidates["candidates"]:
        assert c["publishable"] is False or c["authorization_status"] in {"authorized", "authorized_owner"}
        if c["source_url"] not in authorized and c.get("authorization_status") != "authorized_owner":
            assert c["publishable"] is False
        if c.get("license_verified"):
            assert c["authorization_status"] == "authorized"

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
