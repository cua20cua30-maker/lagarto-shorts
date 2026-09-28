import json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CANDIDATES=ROOT/"data/candidates.json"; PROFILES=ROOT/"config/creator_style_profiles.json"; PATTERNS=ROOT/"data/learned_patterns.json"; TRENDS=ROOT/"data/trend_research.json"; OUT=ROOT/"data/edit_strategies.json"
def load(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return d
def main():
    candidates=load(CANDIDATES,{"candidates":[]}).get("candidates",[]); profiles=load(PROFILES,{"profiles":{}}).get("profiles",{})
    learned=load(PATTERNS,{"patterns":[],"creator_patterns":{},"emotion_patterns":[],"creator_emotion_patterns":{}}); trends=load(TRENDS,{"research":{},"hook_examples":[]})
    global_best=learned.get("patterns",[None])[0] if learned.get("patterns") else None; strategies=[]
    for c in candidates:
        creator=c.get("source_creator",""); profile=profiles.get(creator,{}); cp=learned.get("creator_patterns",{}).get(creator,[]); ce=learned.get("creator_emotion_patterns",{}).get(creator,[])
        best=cp[0] if cp else global_best; hook=(best or {}).get("hook_type") or profile.get("hook_types",[{"pattern":"context_open"}])[0].get("pattern")
        strategies.append({"candidate_id":c["candidate_id"],"source_creator":creator,"hook_pattern":hook,"trend_hook_examples":trends.get("hook_examples",[])[:5],"pacing_pattern":profile.get("pacing",[{"pattern":"short_hook"}])[0].get("pattern"),"learned_edit_style":(best or {}).get("edit_style","emotion_driven_pencil_animation"),"learned_format":"vertical_9_16","max_duration_seconds":58.5,"transformation":["cold_open_to_strongest_moment","remove_dead_air","original_audio_primary","pencil_character_visuals","vertical_9_16","captions_with_readable_timing","payoff_before_end","emotion_aware_selection","trend_informed_metadata"],"global_learning_pattern":global_best,"creator_learning_pattern":cp[0] if cp else None,"emotion_learning_pattern":ce[0] if ce else ((learned.get("emotion_patterns") or [None])[0]),"trend_research_timestamp":trends.get("generated_at"),"publish_gate":{"authorization_required":True,"transformative_edit_required":True}})
    OUT.write_text(json.dumps({"schema_version":2,"generated_at":datetime.now(timezone.utc).isoformat(),"strategies":strategies},ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(f"Strategy engine: generated {len(strategies)} strategies")
if __name__=="__main__":main()
