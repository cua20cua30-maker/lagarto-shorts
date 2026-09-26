import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    with (ROOT / path).open("r", encoding="utf-8") as f:
        return json.load(f)

def main():
    creators = read("config/creators.json")
    factory = read("config/factory.json")
    candidates = read("data/candidates.json")
    records = read("data/learning_records.json")
    patterns = read("data/learned_patterns.json")

    assert len(creators["creators"]) == 11
    assert factory["content_policy"]["require_authorization"] is True
    assert factory["content_policy"]["allow_unlicensed_reposting"] is False
    assert candidates["schema_version"] == 1
    assert isinstance(candidates["candidates"], list)
    assert isinstance(records, list)
    assert patterns["schema_version"] == 1
    assert isinstance(patterns["patterns"], list)

    for candidate in candidates["candidates"]:
        assert candidate["authorization_status"] in {"unknown", "authorized", "rejected"}
        assert candidate["publishable"] is False or candidate["authorization_status"] == "authorized"

    print("Self-test: OK")
    print(f"Candidates: {len(candidates['candidates'])}")
    print(f"Learned patterns: {len(patterns['patterns'])}")

if __name__ == "__main__":
    main()
