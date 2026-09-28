import argparse, json
from collections import Counter
from pathlib import Path
LABELS={"sadness":"Un momento que toca la fibra","pain_loss":"Un momento que deja huella","emotional":"Un momento especialmente emotivo","sentimental":"Un momento que toca la fibra","laughter":"Aquí se descontroló la cosa","fear":"La tensión empezó a subir","surprise":"Nadie esperaba lo que pasó","anger_conflict":"La conversación se calentó","joy_triumph":"El momento de la celebración","scream_or_volume_spike":"La reacción lo cambió todo","rapid_speech":"Todo empezó a ir demasiado rápido"}
QUIET_EMOTIONS={"sadness","pain_loss","emotional","sentimental"}; MAX_DURATION=58.5
def build_plan(m):
    start=max(0.0,float(m["start"])); duration=max(15.0,min(MAX_DURATION,float(m["end"])-start)); emotions=list(m.get("emotion_signals",[]))
    return {"clip_id":f"clip:{m['moment_id']}","moment_id":m["moment_id"],"start":round(start,3),"duration":round(duration,3),"hook":m.get("hook_text",""),"original_context":next((LABELS[x] for x in emotions if x in LABELS),"El momento clave de la historia"),"signals":m.get("signals",[]),"emotion_signals":emotions,"emotion_score":m.get("emotion_score",0),"emotion_detected":m.get("emotion_detected",False),"dominant_emotion":m.get("dominant_emotion"),"selection_score":m.get("selection_score",m.get("score",0)),"edit_recipe":{"format":"9:16","max_duration_seconds":MAX_DURATION,"remove_dead_air":True,"captions":True,"caption_style":"high_readability","hook_first":True,"payoff_before_end":True,"original_audio_primary":True,"original_context_or_commentary_required":True,"pencil_character_visuals":True},"status":"planned"}
def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output",required=True); p.add_argument("--max-clips",type=int,default=10); a=p.parse_args()
    data=json.loads(Path(a.input).read_text(encoding="utf-8")); selected=[]; counts=Counter()
    for m in data.get("moments",[]):
        d=m.get("dominant_emotion") or "other"; limit=3 if d in QUIET_EMOTIONS else 2
        if counts[d]>=limit or any(abs(float(m["start"])-float(x["start"]))<=12 for x in selected): continue
        selected.append(m); counts[d]+=1
        if len(selected)>=a.max_clips: break
    quiet=next((m for m in data.get("moments",[]) if m.get("dominant_emotion") in QUIET_EMOTIONS and not m.get("scream_detected")),None)
    if quiet and not any(m["moment_id"]==quiet["moment_id"] for m in selected):
        if len(selected)>=a.max_clips:selected[-1]=quiet
        else:selected.append(quiet)
    selected.sort(key=lambda m:(m.get("score",0),m.get("emotion_score",0)),reverse=True)
    plans=[build_plan(m) for m in selected[:a.max_clips]]
    Path(a.output).write_text(json.dumps({"schema_version":2,"max_duration_seconds":MAX_DURATION,"plans":plans},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Clip planner: {len(plans)} clips planned; max_duration={MAX_DURATION}s")
if __name__=="__main__": main()
