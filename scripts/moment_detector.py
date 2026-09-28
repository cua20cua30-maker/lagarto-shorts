import argparse
import json
import re
from pathlib import Path

SIGNALS = {
    "shock": ("increíble", "increible", "brutal", "locura", "madre mía", "dios mío"),
    "conflict": ("polémica", "polemica", "humilla", "humilló", "explota", "se lía", "se lia"),
    "reveal": ("resulta que", "nadie sabía", "nadie esperaba", "al final", "descubrimos"),
    "reaction": ("qué coño", "que coño", "no puede ser", "wtf"),
}


def score(text):
    t = re.sub(r"\s+", " ", (text or "").lower().strip())
    n = 0
    labels = []
    for label, terms in SIGNALS.items():
        hits = sum(term in t for term in terms)
        if hits:
            n += min(25, hits * 10)
            labels.append(label)
    if "?" in t:
        n += 8
        labels.append("question")
    if "!" in t:
        n += 5
        labels.append("exclamation")
    return min(100, n), labels


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--screams")
    p.add_argument("--emotions")
    args = p.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    segs = data.get("segments", [])
    screams = []
    emotions = []
    if args.screams and Path(args.screams).exists():
        screams = json.loads(Path(args.screams).read_text(encoding="utf-8")).get("events", [])
    if args.emotions and Path(args.emotions).exists():
        emotions = json.loads(Path(args.emotions).read_text(encoding="utf-8")).get("events", [])

    events = screams + emotions
    moments = []

    for i, segment in enumerate(segs):
        st = float(segment["start"])
        en = float(segment["end"])
        context = [
            x for x in segs
            if float(x["end"]) >= st - 8 and float(x["start"]) <= en + 27
        ]
        text = " ".join(x.get("text", "") for x in context)
        text_score, labels = score(text)
        near = [
            e for e in events
            if float(e.get("end", 0)) >= st - 5 and float(e.get("start", 0)) <= en + 10
        ]

        event_score = max((float(e.get("score", 0)) for e in near), default=0.0)
        event_signals = sorted(set(x for e in near for x in e.get("signals", [])))
        if near:
            labels.extend(event_signals)

        emotion_signals = sorted(set(
            x for e in near
            for x in e.get("signals", [])
            if x in {"laughter", "sadness", "fear", "surprise", "anger_conflict",
                     "joy_triumph", "pain_loss", "emotional", "sentimental",
                     "silence_to_emotion", "rapid_speech", "scream_or_volume_spike"}
        ))
        acoustic_score = max(
            (float(e.get("audio_score", 0)) for e in near),
            default=0.0,
        )

        # Independent signals are deliberately combined instead of allowing
        # raw loudness alone to dominate selection.
        selection_score = (
            text_score * 0.42
            + event_score * 0.33
            + acoustic_score * 0.10
            + min(100, len(set(event_signals)) * 12) * 0.15
        )
        if len(emotion_signals) >= 2:
            selection_score += 7
        if "silence_to_emotion" in event_signals:
            selection_score += 5
        selection_score = round(min(100, selection_score), 1)

        if near:
            strong = max(near, key=lambda e: float(e.get("score", 0)))
            ss = min(float(e.get("start", st)) for e in near)
            ee = max(float(e.get("end", en)) for e in near)
            strong_score = float(strong.get("score", 0))
        else:
            ss = ee = None
            strong_score = 0.0

        if selection_score >= 18:
            start = max(0, st - 2.5)
            end = max(en + 8, st + 15)
            if ss is not None:
                start = min(start, max(0, ss - 1))
                end = max(end, ee + 2)

            duration = end - start
            duration_bonus = 8 if 20 <= duration <= 42 else (3 if 15 <= duration <= 50 else 0)
            selection_score = round(min(100, selection_score + duration_bonus), 1)

            dominant = None
            for candidate in ("sadness", "laughter", "fear", "surprise", "anger_conflict", "joy_triumph"):
                if candidate in emotion_signals:
                    dominant = candidate
                    break

            moments.append({
                "moment_id": f"moment:{i}:{int(st * 1000)}",
                "start": round(start, 3),
                "end": round(end, 3),
                "score": selection_score,
                "selection_score": selection_score,
                "signals": sorted(set(labels)),
                "scream_detected": any(
                    "scream" in " ".join(e.get("signals", []))
                    or "scream_or_volume_spike" in " ".join(e.get("signals", []))
                    for e in near
                ),
                "scream_score": round(max(
                    (e.get("score", 0) for e in near
                     if "scream" in " ".join(e.get("signals", []))
                     or "scream_or_volume_spike" in " ".join(e.get("signals", []))),
                    default=0
                ), 1),
                "emotion_detected": bool(emotion_signals),
                "emotion_score": round(strong_score, 1),
                "emotion_signals": emotion_signals,
                "dominant_emotion": dominant,
                "hook_text": segment.get("text", "").strip(),
                "context_text": text.strip(),
            })

    moments.sort(key=lambda x: x["selection_score"], reverse=True)
    selected = []
    for moment in moments:
        if all(abs(moment["start"] - x["start"]) > 12 for x in selected):
            selected.append(moment)
        if len(selected) >= 20:
            break

    Path(args.output).write_text(
        json.dumps({
            "schema_version": 4,
            "source": data.get("source"),
            "moments": selected,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Moment detector: {len(selected)} moments selected")


if __name__ == "__main__":
    main()
