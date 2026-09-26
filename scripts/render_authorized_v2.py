import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".work"
PLANS = ROOT / "data" / "clip_plans.json"
OUT = ROOT / "data" / "render_queue.json"


def load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def stamp(seconds):
    ms = max(0, int(float(seconds) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def make_srt(plan):
    path = plan.get("transcript_path")
    if not path:
        return None
    data = load(Path(path), {})
    start = float(plan["start"])
    end = start + float(plan["duration"])
    rows = []
    for segment in data.get("segments", []):
        text = str(segment.get("text", "")).strip()
        a = float(segment.get("start", 0))
        b = float(segment.get("end", a))
        if text and b > start and a < end:
            rows.append((max(a, start) - start, min(b, end) - start, text))
    if not rows:
        return None
    out = WORK / (plan["clip_id"].replace(":", "_") + ".srt")
    with out.open("w", encoding="utf-8") as f:
        for i, row in enumerate(rows, 1):
            f.write(f"{i}\n{stamp(row[0])} --> {stamp(row[1])}\n{row[2]}\n\n")
    return out


def main():
    plans = load(PLANS, {"plans": []}).get("plans", [])
    jobs = []
    WORK.mkdir(exist_ok=True)

    for plan in plans:
        source = Path(plan["source_path"])
        output = WORK / (plan["clip_id"].replace(":", "_") + ".mp4")
        if not source.exists():
            continue

        subtitle = make_srt(plan)
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        if subtitle:
            vf += ",subtitles=" + str(subtitle)

        command = [
            "ffmpeg", "-y", "-ss", str(plan["start"]), "-i", str(source),
            "-t", str(plan["duration"]), "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
            str(output),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            print(result.stderr[-1000:])
            continue

        jobs.append({
            "job_id": "rendered:" + plan["clip_id"],
            "clip_id": plan["clip_id"],
            "candidate_id": plan.get("candidate_id"),
            "source_creator": plan.get("source_creator"),
            "output": str(output),
            "status": "rendered",
            "captions": bool(subtitle),
            "idempotency_key": "rendered:" + plan["clip_id"],
        })

    OUT.write_text(json.dumps({"schema_version": 1, "jobs": jobs}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Render authorized v2: {len(jobs)} clips rendered")


if __name__ == "__main__":
    main()
