"""Merge VOD candidates from supported sources.

Twitch uses official VOD discovery. Kick is checked only for API availability;
live metadata is never promoted into the VOD pipeline.
"""
import json,subprocess
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CANDIDATES=ROOT/"data/candidates.json"
KICK_CANDIDATES=ROOT/"data/kick_candidates.json"
TWITCH_DIAG=ROOT/"data/stream_radar_diagnostics.json"
KICK_DIAG=ROOT/"data/kick_radar_diagnostics.json"
CONFIG=ROOT/"config/factory.json"

def load(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError):return default

def main():
    result=subprocess.run(["python","scripts/kick_radar.py"],cwd=ROOT,check=False)
    if result.returncode:print("Kick VOD radar exited with code",result.returncode)
    twitch=load(CANDIDATES,{"candidates":[]}).get("candidates",[])
    kick=load(KICK_CANDIDATES,{"candidates":[]}).get("candidates",[])
    merged={}
    for item in twitch+kick:
        cid=item.get("candidate_id")
        if cid:merged[cid]=item
    ranked=sorted(merged.values(),key=lambda x:float(x.get("score",0) or 0),reverse=True)
    limit=int(load(CONFIG,{}).get("limits",{}).get("max_candidates_per_run",20) or 20)
    creators=[c["name"] for c in load(ROOT/"config/creators.json",{"creators":[]}).get("creators",[]) if c.get("enabled",True)]
    selected=[];ids=set();counts=Counter()
    for name in creators:
        options=[x for x in ranked if x.get("source_creator")==name]
        if options:
            selected.append(options[0]);ids.add(options[0]["candidate_id"]);counts[name]+=1
    cap=max(3,(limit+len(creators)-1)//max(1,len(creators)))
    for item in ranked:
        if len(selected)>=limit:break
        cid=item.get("candidate_id");name=item.get("source_creator")
        if cid in ids or counts[name]>=cap:continue
        selected.append(item);ids.add(cid);counts[name]+=1
    now=datetime.now(timezone.utc)
    diagnostics=load(TWITCH_DIAG,{"results":[]}).get("results",[])+load(KICK_DIAG,{"results":[]}).get("results",[])
    CANDIDATES.write_text(json.dumps({
        "schema_version":5,"generated_at":now.isoformat(),"mode":"vod_only",
        "source_priority":["twitch","kick"],
        "discovery_policy":{"twitch":"official Twitch API VOD discovery",
                            "kick":"official Kick API checked; public VOD listing/media unavailable",
                            "live_processing":False},
        "total_discovered":len(ranked),"selection_limit":limit,
        "creator_coverage":{n:sum(1 for x in selected if x.get("source_creator")==n) for n in creators},
        "platform_coverage":{"twitch":sum(1 for x in selected if x.get("source_platform")=="twitch"),
                             "kick":sum(1 for x in selected if x.get("source_platform")=="kick")},
        "candidates":selected},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (ROOT/"data/multisource_diagnostics.json").write_text(json.dumps({
        "schema_version":3,"generated_at":now.isoformat(),"mode":"vod_only","results":diagnostics,
        "platforms":{"twitch":sum(1 for x in diagnostics if x.get("platform")=="twitch"),
                     "kick":sum(1 for x in diagnostics if x.get("platform")=="kick")}},
        ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Multisource VOD radar: twitch={sum(1 for x in selected if x.get('source_platform')=='twitch')} kick={sum(1 for x in selected if x.get('source_platform')=='kick')} total={len(selected)}")

if __name__=="__main__":main()
