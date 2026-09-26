import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data" / "candidates.json"
PROFILES = ROOT / "config" / "creator_style_profiles.json"

HOOK_RULES = [
    ("question_open", [r"\?", r"\bpor qué\b", r"\bcomo puede\b"]),
    ("shock_claim", [r"\bno puede ser\b", r"\bbrutal\b", r"\bincre[ií]ble\b", r"\blocura\b"]),
    ("conflict", [r"\bpol[eé]mica\b", r"\bse l[ií]a\b", r"\bexplota\b", r"\bhumill"]),
    ("reveal", [r"\bnadie esperaba\b", r"\bresulta que\b", r"\bal final\b"]),
    ("reaction", [r"\breacci[oó]n\b", r"\breacciona\b", r"\bse queda\b"]),
]

def load_json(path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def classify_title(title):
    text = (title or "").strip().lower()
    matches = []
    for label, patterns in HOOK_RULES:
        if any(re.search(pattern, text) for pattern in patterns):
            matches.append(label)
    return matches or ["context_open"]

def pacing_bucket(title):
    words = re.findall(r"\w+", (title or ""), flags=re.UNICODE)
    n = len(words)
    if n <= 5:
        return "ultra_short_hook"
    if n <= 9:
        return "short_hook"
    if n <= 15:
        return "medium_hook"
    return "long_context_hook"

def language_features(title):
    text = (title or "").lower()
    features = []
    if any(x in text for x in ("qué", "como", "por qué", "cómo")):
        features.append("question_language")
    if "!" in text:
        features.append("exclamation")
    if re.search(r"\b(no|nunca|nadie|jam[aá]s)\b", text):
        features.append("negation")
    if re.search(r"\b(viral|pol[eé]mica|brutal|locura|incre[ií]ble)\b", text):
        features.append("high_intensity_lexicon")
    return features

def main():
    candidates = load_json(CANDIDATES, {"candidates": []}).get("candidates", [])
    profiles_doc = load_json(PROFILES, {"schema_version": 1, "profiles": {}})
    profiles = profiles_doc.setdefault("profiles", {})

    grouped = {}
    for candidate in candidates:
        creator = candidate.get("source_creator")
        if not creator:
            continue
        grouped.setdefault(creator, []).append(candidate)

    for creator, items in grouped.items():
        profile = profiles.setdefault(creator, {
            "hook_types": [], "pacing": [], "language": [],
            "reaction_patterns": [], "story_structures": [], "learned_examples": []
        })
        hooks = Counter()
        pacing = Counter()
        language = Counter()
        for item in items:
            title = item.get("title", "")
            hooks.update(classify_title(title))
            pacing[pacing_bucket(title)] += 1
            language.update(language_features(title))

        profile["hook_types"] = [{"pattern": k, "observations": v} for k, v in hooks.most_common()]
        profile["pacing"] = [{"pattern": k, "observations": v} for k, v in pacing.most_common()]
        profile["language"] = [{"pattern": k, "observations": v} for k, v in language.most_common()]
        profile["sample_count"] = len(items)
        profile["updated_at"] = datetime.now(timezone.utc).isoformat()

    profiles_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    PROFILES.write_text(json.dumps(profiles_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Style learner: analysed {len(candidates)} candidates across {len(grouped)} creators")

if __name__ == "__main__":
    main()
