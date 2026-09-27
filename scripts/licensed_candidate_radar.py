import json, re
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p,d): return json.loads(p.read_text(encoding="utf-8")) if p.exists() else d
def score(title):
 t=title.lower(); hits=sum(x in t for x in ["reacción","reaccion","impactante","increíble","increible","sorpresa","locura","historia","miedo","risa","triste","brutal","épico","epico","no puede ser"]); return 30+hits*5
def main():
 path=ROOT/"data/candidates.json"; data=load(path,{"schema_version":2,"candidates":[]}); cc=load(ROOT/"data/licensed_sources.json",{"sources":[]}).get("sources",[])
 existing=data.get("candidates",[]); ids={x.get("candidate_id") for x in existing}; additions=[]
 for rank,s in enumerate(cc[:5]):
  if not s.get("license_verified") or not s.get("source_url") or s.get("video_id") in ids: continue
  additions.append({"candidate_id":"cc:"+s["video_id"],"source_creator":s.get("source_creator") or "Creative Commons source","source_url":s["source_url"],"title":s.get("title",""),"duration_seconds":0,"score":score(s.get("title","")),"radar_rank":rank,"detected_at":datetime.now(timezone.utc).isoformat(),"status":"licensed_discovered","authorization_status":"authorized","publishable":True,"uploader_verified":False,"uploader":s.get("source_creator",""),"uploader_id":s.get("channel_id",""),"license":"CC BY / Creative Commons","license_verified":True})
 if additions:
  keep=max(0,20-len(additions)); non_auth=[x for x in existing if x.get("source_url") not in {a["source_url"] for a in additions}]; existing=non_auth[:keep]+additions
  data["candidates"]=existing; data["selection_limit"]=20; data["licensed_coverage"]=len(additions); data["generated_at"]=datetime.now(timezone.utc).isoformat();
  path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(f"Licensed candidate radar: added={len(additions)}")
if __name__=="__main__": main()
