import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LEARNING_RECORDS = DATA / "learning_records.json"
LEARNED_PATTERNS = DATA / "learned_patterns.json"

DEFAULT_PATTERNS = {
    "schema_version": 2,
    "updated_at": None,
    "minimum_samples": 5,
    "patterns": [],
    "creator_patterns": {},
    "experiments": [],
}

def load_records():
    if not LEARNING_RECORDS.exists():
        return []
    with LEARNING_RECORDS.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("records", [])

def metric_value(record):
    metrics = record.get("metrics", {})
    for key in ("average_percentage_viewed", "retention_end"):
        value = metrics.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None

def learn(records):
    groups = defaultdict(list)
    creator_groups = defaultdict(list)

    for record in records:
        value = metric_value(record)
        if value is None:
            continue

        key = (
            record.get("hook_type", "unknown"),
            record.get("edit_style", "unknown"),
            record.get("format", "unknown"),
        )
        groups[key].append(value)

        creator = record.get("source_creator", "unknown")
        creator_groups[(creator, *key)].append(value)

    patterns = []
    for key, values in groups.items():
        if len(values) < 5:
            continue
        patterns.append({
            "hook_type": key[0],
            "edit_style": key[1],
            "format": key[2],
            "samples": len(values),
            "median_retention": round(median(values), 4),
            "recommendation": "promote_for_experiment"
        })

    creator_patterns = defaultdict(list)
    for key, values in creator_groups.items():
        if len(values) < 3:
            continue
        creator, hook, edit_style, fmt = key
        creator_patterns[creator].append({
            "hook_type": hook,
            "edit_style": edit_style,
            "format": fmt,
            "samples": len(values),
            "median_retention": round(median(values), 4),
            "recommendation": "promote_for_creator_experiment"
        })

    patterns.sort(key=lambda item: item["median_retention"], reverse=True)
    for values in creator_patterns.values():
        values.sort(key=lambda item: item["median_retention"], reverse=True)

    return patterns, dict(creator_patterns)

def main():
    records = load_records()
    patterns, creator_patterns = learn(records)

    result = DEFAULT_PATTERNS.copy()
    result["updated_at"] = datetime.now(timezone.utc).isoformat()
    result["patterns"] = patterns
    result["creator_patterns"] = creator_patterns

    LEARNED_PATTERNS.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Learning engine: {len(records)} records analysed")
    print(f"Learned global patterns: {len(patterns)}")
    print(f"Creators with learned performance patterns: {len(creator_patterns)}")

if __name__ == "__main__":
    main()
