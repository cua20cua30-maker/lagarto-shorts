"""YouTube licensed-source discovery is intentionally disabled for the stream-first factory."""
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    path=ROOT/"data/candidates.json"
    data=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema_version":3,"candidates":[]}
    data["candidates"]=[x for x in data.get("candidates",[]) if x.get("source_platform") in {"twitch","kick"}]
    data["source_priority"]=["twitch","kick"]
    data["generated_at"]=datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Licensed candidate radar: disabled; stream sources only.")
if __name__=="__main__":
    main()
