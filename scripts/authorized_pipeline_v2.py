import json
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data/candidates.json"
AUTH = ROOT / "data/authorization_manifest.json"
MOMENTS = ROOT / "data/moments.json"
PLANS = ROOT / "data/clip_plans.json"
SCREAMS = ROOT / "data/scream_events.json"
EMOTIONS = ROOT / "data/emotion_events.json"
WORK = ROOT / ".work"


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except (OSError, json.JSONDecodeError):
        return default


def run(command):
    return subprocess.run(command, check=False)


def acquire(source_url, output):
    result = run([
        "yt-dlp", "--no-playlist",
        "--retries", "3", "--fragment-retries", "3",
        "--socket-timeout", "30",
        "--extractor-retries", "3",
        "-f", "bv*+ba/b", "--merge-output-format", "mp4",
        "-o", str(output), source_url,
    ])
    return result


def main():
    candidates = load(CANDIDATES, {"candidates": []}).get("candidates", [])
    allowed = set(load(AUTH, {"authorized_sources": []}).get("authorized_sources", []))
    licensed = load(ROOT / "data/licensed_sources.json", {"sources": []}).get("sources", [])
    allowed.update(
        s.get("source_url") for s in licensed if s.get("license_verified") and s.get("source_url")
    )

    published = {
        x.get("clip_id")
        for x in load(ROOT / "data/published.json", {"items": []}).get("items", [])
        if x.get("clip_id")
    }
    selected = [
        c for c in candidates
        if c.get("source_kind") == "vod"
        and (c.get("source_url") in allowed or c.get("authorization_status") == "authorized_owner")
        and c.get("acquirable", False)
        and c.get("acquisition_url")
        and f"clip:{c.get('candidate_id')}" not in published
    ]
    selected.sort(key=lambda item: float(item.get("score", 0) or 0), reverse=True)
    selected = selected[:5]

    all_moments = []
    all_plans = []
    all_screams = []
    all_emotions = []
    WORK.mkdir(exist_ok=True)

    for candidate in selected:
        candidate_id = str(candidate["candidate_id"])
        cid = candidate_id.replace(":", "_")
        source = WORK / f"{cid}.mp4"
        transcript = WORK / f"{cid}.json"
        scream_file = WORK / f"{cid}_screams.json"
        emotion_file = WORK / f"{cid}_emotions.json"
        moment_file = WORK / f"{cid}_moments.json"
        plan_file = WORK / f"{cid}_plans.json"

        if source.exists() and source.stat().st_size < 100000:
            source.unlink()
        if not source.exists():
            acquisition = acquire(candidate["acquisition_url"], source)
            if acquisition.returncode:
                print("Authorized acquisition failed:", candidate.get("source_url"))
                continue

        cached = plan_file.exists() and moment_file.exists() and emotion_file.exists() and scream_file.exists()
        if not cached:
            commands = [
                ["python", "scripts/scream_detector.py", "--input", str(source), "--output", str(scream_file)],
                ["python", "scripts/transcriber.py", "--input", str(source), "--output", str(transcript)],
                ["python", "scripts/emotion_detector.py", "--input", str(source), "--transcript", str(transcript), "--output", str(emotion_file)],
                ["python", "scripts/moment_detector.py", "--input", str(transcript), "--output", str(moment_file), "--screams", str(scream_file), "--emotions", str(emotion_file)],
                ["python", "scripts/clip_planner.py", "--input", str(moment_file), "--output", str(plan_file), "--max-clips", "6"],
            ]
            failed = False
            for command in commands:
                if run(command).returncode:
                    failed = True
                    break
            if failed:
                continue

        sd = load(scream_file, {"events": []})
        ed = load(emotion_file, {"events": []})
        md = load(moment_file, {"moments": []})
        pd = load(plan_file, {"plans": []})

        for event in sd.get("events", []):
            event.update(candidate_id=candidate_id, source_path=str(source), source_creator=candidate.get("source_creator"))
            all_screams.append(event)

        for event in ed.get("events", []):
            event.update(candidate_id=candidate_id, source_path=str(source), source_creator=candidate.get("source_creator"))
            all_emotions.append(event)

        for moment in md.get("moments", []):
            moment.update(candidate_id=candidate_id, source_path=str(source), source_creator=candidate.get("source_creator"), transcript_path=str(transcript))
            all_moments.append(moment)

        for plan in pd.get("plans", []):
            plan.update(
                candidate_id=candidate_id,
                source_path=str(source),
                source_creator=candidate.get("source_creator"),
                transcript_path=str(transcript),
                license=candidate.get("license"),
                license_verified=bool(candidate.get("license_verified")),
                attribution_required=bool(candidate.get("attribution_required")),
            )
            all_plans.append(plan)

    EMOTIONS.write_text(json.dumps({"schema_version": 1, "events": all_emotions}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SCREAMS.write_text(json.dumps({"schema_version": 1, "events": all_screams}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MOMENTS.write_text(json.dumps({"schema_version": 4, "moments": all_moments}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PLANS.write_text(json.dumps({"schema_version": 1, "plans": all_plans}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Authorized pipeline v2: selected={len(selected)} screams={len(all_screams)} moments={len(all_moments)} plans={len(all_plans)}")


if __name__ == "__main__":
    main()
