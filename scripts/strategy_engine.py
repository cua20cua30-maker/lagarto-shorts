import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data" / "candidates.json"
PROFILES = ROOT / "config" / "creator_style_profiles.json"
PATTERNS = ROOT / "data" / "learned_patterns.json"
OUT = ROOT / "data" / "edit_strategies.json"

def load(path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def choose_hook(profile):
    hooks = profile.get("hook_types", [])
    return hooks[0]["pattern"] if hooks else "context_open"

def choose_pacing(profile):
    pacing = profile.get("pacing", [])
    return pacing[0]["pattern"] if pacing else "short_hook"

def main():
    candidates = load(CANDIDATES, {"candidates": []}).get("candidates", [])
    profiles = load(PROFILES, {"profiles": {}}).get("profiles", {})
    learned_data = load(PATTERNS, {"patterns": [], "creator_patterns": {}})
    learned = learned_data.get("patterns", [])
    creator_patterns = learned_data.get("creator_patterns", {})

    best_global = learned[0] if learned else None
    strategies = []

    for candidate in candidates:
        creator = candidate.get("source_creator", "")
        profile = profiles.get(creator, {})
        creator_learned = creator_patterns.get(creator, [])
        best_creator = creator_learned[0] if creator_learned else None
        selected = best_creator or best_global
        strategy = {
            "candidate_id": candidate["candidate_id"],
            "source_creator": creator,
            "hook_pattern": (selected or {}).get("hook_type") or choose_hook(profile),
            "pacing_pattern": choose_pacing(profile),
            "learned_edit_style": (selected or {}).get("edit_style", "unknown"),
            "learned_format": (selected or {}).get("format", "vertical_9_16"),
            "transformation": [
                "cold_open_to_strongest_moment",
                "remove_dead_air",
                "add_original_context_or_commentary",
                "vertical_9_16",
                "captions_with_readable_timing",
                "payoff_before_end"
            ],
            "global_learning_pattern": best_global,
            "creator_learning_pattern": best_creator,
            "publish_gate": {
                "authorization_required": True,
                "transformative_edit_required": True
            }
        }
        strategies.append(strategy)

    OUT.write_text(json.dumps({
        "schema_version": 1,
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "strategies": strategies
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Strategy engine: generated {len(strategies)} strategies")

if __name__ == "__main__":
    main()
