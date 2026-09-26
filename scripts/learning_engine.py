import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LEARNING_RECORDS = DATA / "learning_records.json"
LEARNED_PATTERNS = DATA / "learned_patterns.json"

DEFAULT_PATTERNS = {
    "schema_version": 1,
    "updated_at": None,
    "minimum_samples": 5,
    "patterns": [],
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
    groups = {}
    for record in records:
        key = (
            record.get("hook_type", "unknown"),
            record.get("edit_style", "unknown"),
            record.get("format", "unknown"),
        )
        value = metric_value(record)
        if value is not None:
            groups.setdefault(key, []).append(value)

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

    patterns.sort(key=lambda item: item["median_retention"], reverse=True)
    return patterns

def main():
    records = load_records()
    patterns = learn(records)

    result = DEFAULT_PATTERNS.copy()
    result["patterns"] = patterns

    LEARNED_PATTERNS.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Learning engine: {len(records)} records analysed")
    print(f"Learned patterns: {len(patterns)}")

if __name__ == "__main__":
    main()
