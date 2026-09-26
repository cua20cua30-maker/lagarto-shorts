import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCHEMA = {
    "schema_version": 1,
    "description": "Learning record for every generated Short.",
    "fields": {
        "source_creator": "Creator/source identifier.",
        "source_url": "Original source URL or asset reference.",
        "candidate_id": "Stable candidate identifier.",
        "format": "Observed content format/pattern.",
        "duration_seconds": "Final Short duration.",
        "hook_type": "Hook pattern used in the opening.",
        "edit_style": "Transformation/editing recipe identifier.",
        "published_at": "Publication timestamp.",
        "metrics": {
            "views": "Views at snapshot time.",
            "likes": "Likes at snapshot time.",
            "comments": "Comments at snapshot time.",
            "shares": "Shares when available.",
            "average_view_duration": "Average view duration when available.",
            "average_percentage_viewed": "Average percentage viewed when available.",
            "retention_3s": "Retention at 3 seconds when available.",
            "retention_end": "Retention near the end when available."
        },
        "outcome": "Observed performance label after sufficient data.",
        "experiment_id": "Experiment/variant identifier.",
        "learning_tags": "Patterns extracted from the result."
    }
}

def main():
    path = ROOT / "data" / "learning_schema.json"
    path.write_text(json.dumps(SCHEMA, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Learning schema ready: {path}")

if __name__ == "__main__":
    main()
