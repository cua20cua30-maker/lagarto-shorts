import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data" / "candidates.json"
AUTH = ROOT / "data" / "authorization_manifest.json"
MOMENTS = ROOT / "data" / "moments.json"
PLANS = ROOT / "data" / "clip_plans.json"
WORK = ROOT / ".work"


def load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def run(command):
    return subprocess.run(command, check=False)


def main():
    candidates = load(CANDIDATES, {"candidates": []}).get("candidates", [])
    allowed = set(load(AUTH, {"authorized_sources": []}).get("authorized_sources", []))
    selected = [c for c in candidates if c.get("source_url") in allowed]

    all_moments = []
    all_plans = []
    WORK.mkdir(exist_ok=True)

    for candidate in selected:
        candidate_id = candidate["candidate_id"].replace(":", "_")
        source = WORK / f"{candidate_id}.mp4"
        transcript = WORK / f"{candidate_id}.json"
        moments_file = WORK / f"{candidate_id}_moments.json"
        plans_file = WORK / f"{candidate_id}_plans.json"

        if not source.exists():
            result = run([
                "yt-dlp", "--no-playlist", "-f", "bv*+ba/b",
                "--merge-output-format", "mp4", "-o", str(source),
                candidate["source_url"],
            ])
            if result.returncode:
                continue

        if run(["python", "scripts/transcriber.py", "--input", str(source), "--output", str(transcript)]).returncode:
            continue
        if run(["python", "scripts/moment_detector.py", "--input", str(transcript), "--output", str(moments_file)]).returncode:
            continue
        if run(["python", "scripts/clip_planner.py", "--input", str(moments_file), "--output", str(plans_file)]).returncode:
            continue

        moment_data = load(moments_file, {"moments": []})
        plan_data = load(plans_file, {"plans": []})

        for moment in moment_data.get("moments", []):
            moment["candidate_id"] = candidate["candidate_id"]
            moment["source_path"] = str(source)
            moment["source_creator"] = candidate["source_creator"]
            moment["transcript_path"] = str(transcript)
            all_moments.append(moment)

        for plan in plan_data.get("plans", []):
            plan["candidate_id"] = candidate["candidate_id"]
            plan["source_path"] = str(source)
            plan["source_creator"] = candidate["source_creator"]
            plan["transcript_path"] = str(transcript)
            all_plans.append(plan)

    MOMENTS.write_text(
        json.dumps({"schema_version": 1, "moments": all_moments}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    PLANS.write_text(
        json.dumps({"schema_version": 1, "plans": all_plans}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Authorized pipeline v2: selected={len(selected)} moments={len(all_moments)} plans={len(all_plans)}")


if __name__ == "__main__":
    main()
