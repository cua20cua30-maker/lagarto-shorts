import json, os, re, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; CONFIG=ROOT/"config/creators.json"; OUT=ROOT/"data/candidates.json"; DIAG=ROOT/"data/stream_radar_diagnostics.json"
TOKEN_URL="https://id.twitch.tv/oauth2/token"; API="https://api.twitch.tv/helix"
def load(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError):return d
def norm(v):return re.sub(r"[^a-z0-9]","",(v or "").lower())
def token():
    cid,sec=os.getenv("TWITCH_CLIENT_ID"),os.getenv("TWITCH_CLIENT_SECRET")
    if not cid or not sec:return None,"missing Twitch credentials"
    data=urllib.parse.urlencode({"client_id":cid,"client_secret":sec,"grant_type":"client_credentials"}).encode()
    req=urllib.request.Request(TOKEN_URL,data=data,headers={"Content-Type":"application/x-www-form-urlencoded"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read().decode()).get("access_token"),None
    except Exception as e:return None,str(e)
def get(path,t,params):
    req=urllib.request.Request(API+path+"?"+urllib.parse.urlencode(params),headers={"Authorization":"Bearer "+t,"Client-Id":os.environ["TWITCH_CLIENT_ID"],"User-Agent":"LagartoShortsFactory/2.0"})
    with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode())
def score(title,views,when):
    s=sum(9 for x in ("reacción","reaccion","increíble","increible","polémica","polemica","humilla","explota","locura","nadie esperaba","se lía","se lia","viral","wtf","qué coño","que coño","no puede ser","llora","llorando","triste","enfado","cabreado","sorpresa","brutal","😂","😭","🥹","💔","😱","😡","😳","💀","🤯") if x in (title or "").lower())
    v=min(25,(max(0,int(views or 0))/10000)**0.5*5)
    try:age=max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(when.replace("Z","+00:00"))).total_seconds()/3600)
    except Exception:age=168
    return round(min(100,s+v+max(0,25-age/7)),2)
def main():
    cfg=load(CONFIG,{"creators":[]}); now=datetime.now(timezone.utc); cutoff=now-timedelta(days=7); t,err=token(); candidates=[]; diagnostics=[]
    if t:
        for c in cfg["creators"]:
            if not c.get("enabled",True):continue
            login=c.get("twitch_login")
            try:
                users=get("/users",t,{"login":login}).get("data",[]) if login else []
                if not users:raise RuntimeError("Twitch user not found")
                u=users[0]; videos=get("/videos",t,{"user_id":u["id"],"type":"archive","first":20,"sort":"time"}).get("data",[]); kept=0
                for rank,v in enumerate(videos):
                    published=v.get("published_at") or v.get("created_at")
                    if published and datetime.fromisoformat(published.replace("Z","+00:00"))<cutoff:continue
                    kept+=1; vid=v["id"]
                    candidates.append({"candidate_id":f"twitch:vod:{vid}","source_platform":"twitch","source_creator":c["name"],"source_kind":"vod","source_url":v["url"],"owner_authorized":bool(c.get("owner_authorized",False)),"acquisition_url":v["url"],"source_id":vid,"title":v.get("title",""),"duration_raw":v.get("duration"),"score":score(v.get("title"),v.get("view_count"),published or now.isoformat()),"radar_rank":rank,"detected_at":now.isoformat(),"published_at":published,"status":"discovered","authorization_status":"authorized_owner" if c.get("owner_authorized") else "unknown","publishable":bool(c.get("owner_authorized",False)),"acquirable":True,"uploader_verified":norm(v.get("user_name"))==norm(c["name"]),"uploader":v.get("user_name",""),"uploader_id":v.get("user_id",""),"view_count":v.get("view_count",0),"thumbnail_url":v.get("thumbnail_url")})
                diagnostics.append({"creator":c["name"],"platform":"twitch","status":"ok","login":login,"vods_seen":len(videos),"recent_vods":kept})
            except Exception as e:diagnostics.append({"creator":c["name"],"platform":"twitch","status":"error","login":login,"error":str(e)})
    else:diagnostics.append({"platform":"twitch","status":"not_configured","error":err})
    ranked=sorted({x["candidate_id"]:x for x in candidates}.values(),key=lambda x:x["score"],reverse=True)
    DIAG.write_text(json.dumps({"schema_version":1,"generated_at":now.isoformat(),"results":diagnostics},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    OUT.write_text(json.dumps({"schema_version":3,"generated_at":now.isoformat(),"source_priority":["twitch","kick"],"total_discovered":len(ranked),"selection_limit":int(load(ROOT/"config/factory.json",{}).get("limits",{}).get("max_candidates_per_run",20) or 20),"creator_coverage":{n:sum(1 for x in ranked if x["source_creator"]==n) for n in [c["name"] for c in cfg["creators"] if c.get("enabled",True)]},"mode":"vod_only","live_processing":False,"candidates":ranked},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Stream radar: discovered={len(ranked)} twitch_configured={bool(t)}")
if __name__=="__main__":main()
