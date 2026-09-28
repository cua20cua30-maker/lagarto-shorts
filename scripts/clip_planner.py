import argparse
import json
from collections import Counter
from pathlib import Path

LABELS = {
    "sadness": "Un momento que toca la fibra",
    "pain_loss": "Un momento que deja huella",
    "emotional": "Un momento especialmente emotivo",
    "sentimental": "Un momento que toca la fibra",
    "laughter": "Aquí se descontroló la cosa",
    "fear": "La tensión empezó a subir",
    "surprise": "Nadie esperaba lo que pasó",
    "anger_conflict": "La conversación se calentó",
    "joy_triumph": "El momento de la celebración",
    "scream_or_volume_spike": "La reacción lo cambió todo",
    "rapid_speech": "Todo empezó a ir demasiado rápido",
}

QUIET_EMOTIONS = {"sadness", "pain_loss", "emotional", "sentimental"}


def build_plan(moment):
    start = max(0.0, float(moment["start"]))
    duration = max(15.0, min(60.0, float(moment["end"]) - start))
    emotions = list(moment.get("emotion_signals", []))
    context = next((LABELS[x] for x in emotions if x in LABELS), "El momento clave de la historia")

    return {
        "clip_id": f"clip:{moment['moment_id']}",
        "moment_id": moment["moment_id"],
        "start": round(start, 3),
        "duration": round(duration, 3),
        "hook": moment.get("hook_text", ""),
        "original_context": context,
        "signals": moment.get("signals", []),
        "emotion_signals": emotions,
        "emotion_score": moment.get("emotion_score", 0),
        "emotion_detected": moment.get("emotion_detected", False),
        "dominant_emotion": moment.get("dominant_emotion"),
        "selection_score": moment.get("selection_score", moment.get("score", 0)),
        "edit_recipe": {
            "format": "9:16",
            "remove_dead_air": True,
            "captions": True,
            "caption_style": "high_readability",
            "hook_first": True,
            "payoff_before_end": True,
            "original_context_or_commentary_required": True,
        },
        "status": "planned",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--max-clips", type=int, default=10)
    args = p.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    moments = data.get("moments", [])

    # Preserve emotional diversity instead of allowing loud/action moments
    # to consume the entire batch.
    selected = []
    counts = Counter()

    for moment in moments:
        dominant = moment.get("dominant_emotion") or "other"
        limit = 3 if dominant in QUIET_EMOTIONS else 2
        if counts[dominant] >= limit:
            continue
        if all(abs(float(moment["start"]) - float(x["start"])) > 12 for x in selected):
            selected.append(moment)
            counts[dominant] += 1
        if len(selected) >= args.max_clips:
            break

    # Guarantee one quiet emotional candidate whenever one exists.
    quiet = next(
        (
            m for m in moments
            if m.get("dominant_emotion") in QUIET_EMOTIONS
            and not m.get("scream_detected")
        ),
        None,
    )
    if quiet and not any(m["moment_id"] == quiet["moment_id"] for m in selected):
        if len(selected) >= args.max_clips:
            selected[-1] = quiet
        else:
            selected.append(quiet)

    # Keep strongest moments first while preserving the rescued emotional clip.
    selected.sort(key=lambda m: (m.get("score", 0), m.get("emotion_score", 0)), reverse=True)
    plans = [build_plan(m) for m in selected[:args.max_clips]]

    Path(args.output).write_text(
        json.dumps({"schema_version": 1, "plans": plans}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Clip planner: {len(plans)} clips planned")


if __name__ == "__main__":
    main()
