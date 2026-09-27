import json, subprocess, hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CFG=ROOT/"config/multisource_radar.json"
CAND=ROOT/"data/candidates.json"
DIAG=ROOT/"data/multisource_diagnostics.json"

def load(p,d):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else d

def score(title):
    t=(title or "").lower()
    hits=["reacción","reaccion","impactante","increíble","increible","sorpresa","locura","historia","miedo","risa","triste","brutal","épico","epico","no puede ser","llora","llorar","enfadado","enfadada","cabreo","se emociona","emocionado"]
    return 30+sum(5 for x in hits if x in t)

def extract(url, limit):
    cmd=["yt-dlp","--flat-playlist","--dump-single-json","--playlist-end",str(limit),"--no-warnings","--ignore-errors",url]
    try:
        p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=90)
        if p.returncode!=0 or not p.stdout.strip():
            return [], (p.stderr.strip()[-500:] if p.stderr else "no_output")
        data=json.loads(p.stdout)
        entries=data.get("entries") or []
        if not entries and data.get("id"):
            entries=[data]
        return entries, ""
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"

def main():
    cfg=load(CFG,{})
    existing=load(CAND,{"schema_version":2,"candidates":[]})
    candidates=existing.get("candidates",[])
    existing_urls={x.get("source_url") for x in candidates}
    diagnostics={"schema_version":1,"generated_at":datetime.now(timezone.utc).isoformat(),"platforms":{}}
    additions=[]
    for creator in cfg.get("creators",[]):
        name=creator.get("name","")
        for platform in ("twitch","tiktok","instagram","kick"):
            if not cfg.get("platforms",{}).get(platform,{}).get("enabled"): continue
            url=creator.get(platform)
            if not url: continue
            entries,error=extract(url,int(cfg.get("max_per_platform_creator",5)))
            key=f"{name}:{platform}"
            diagnostics["platforms"][key]={"url":url,"found":len(entries),"error":error}
            for rank,e in enumerate(entries):
                webpage=e.get("webpage_url") or e.get("url")
                if not webpage or webpage in existing_urls or any(a["source_url"]==webpage for a in additions): continue
                title=e.get("title") or e.get("description") or ""
                vid=e.get("id") or ""
                cid=f"{platform}:{vid}" if vid else f"{platform}:{hashlib.sha1(webpage.encode("utf-8")).hexdigest()[:16]}"
                additions.append({
                    "candidate_id":cid,
                    "source_creator":name,
                    "source_platform":platform,
                    "source_url":webpage,
                    "title":title,
                    "duration_seconds":int(e.get("duration") or 0),
                    "score":score(title),
                    "radar_rank":rank,
                    "detected_at":datetime.now(timezone.utc).isoformat(),
                    "status":"multisource_discovered",
                    "authorization_status":"not_authorized",
                    "publishable":False,
                    "uploader_verified":False,
                    "uploader":e.get("channel") or name,
                    "uploader_id":e.get("channel_id") or "",
                    "discovery_method":"yt-dlp_public_profile_metadata"
                })
    additions.sort(key=lambda x:x.get("score",0),reverse=True)
    limit=int(cfg.get("max_total_candidates",20))
    base=[x for x in candidates if x.get("source_url") not in {a["source_url"] for a in additions}]
    combined=base+additions
    combined.sort(key=lambda x:(x.get("authorization_status")=="authorized",x.get("score",0)),reverse=True)
    merged=combined[:limit]
    existing["candidates"]=merged
    existing["selection_limit"]=limit
    existing["multisource_coverage"]={}
    for x in merged:
        p=x.get("source_platform","youtube")
        existing["multisource_coverage"][p]=existing["multisource_coverage"].get(p,0)+1
    CAND.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    DIAG.write_text(json.dumps(diagnostics,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Multisource radar: discovered="+str(len(additions))+" selected="+str(len(merged)))

if __name__=="__main__":
    main()
