import json, os, re
from datetime import datetime, timezone
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
ROOT=Path(__file__).resolve().parents[1]

def iso8601_seconds(value):
 m=re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?", value or "")
 if not m: return 0
 d,h,mi,s=m.groups(); return int(float(d or 0)*86400+float(h or 0)*3600+float(mi or 0)*60+float(s or 0))
CFG=ROOT/"config/licensed_source_discovery.json"; OUT=ROOT/"data/licensed_sources.json"
def load(p,d): return json.loads(p.read_text(encoding="utf-8")) if p.exists() else d
def main():
 cfg=load(CFG,{}); now=datetime.now(timezone.utc).isoformat()
 required=["YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_REFRESH_TOKEN"]
 missing=[x for x in required if not os.getenv(x)]
 if missing:
  OUT.write_text(json.dumps({"schema_version":1,"generated_at":now,"status":"skipped","reason":"missing_oauth","sources":[]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print("CC discovery: OAuth missing; skipped safely."); return
 creds=Credentials(token=None,refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],token_uri="https://oauth2.googleapis.com/token",client_id=os.environ["YOUTUBE_CLIENT_ID"],client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],scopes=["https://www.googleapis.com/auth/youtube.readonly"])
 try: creds.refresh(Request())
 except Exception as exc:
  OUT.write_text(json.dumps({"schema_version":1,"generated_at":now,"status":"failed","reason":"oauth_refresh_failed","sources":[]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  print("CC discovery OAuth failed:",type(exc).__name__,exc); return
 yt=build("youtube","v3",credentials=creds); found={}
 for q in cfg.get("queries",[]):
  try:
   res=yt.search().list(part="snippet",q=q,type="video",videoLicense="creativeCommon",regionCode=cfg.get("region_code","ES"),relevanceLanguage=cfg.get("relevance_language","es"),maxResults=int(cfg.get("max_results_per_query",10))).execute()
  except Exception as exc: print("CC search failed:",q,type(exc).__name__,exc); continue
  for item in res.get("items",[]):
   vid=item.get("id",{}).get("videoId")
   if vid: found[vid]=q
 ids=list(found)
 verified=[]
 for i in range(0,len(ids),50):
  try: res=yt.videos().list(part="snippet,status,contentDetails",id=",".join(ids[i:i+50])).execute()
  except Exception as exc: print("CC verification failed:",type(exc).__name__,exc); continue
  for v in res.get("items",[]):
   s=v.get("status",{}); sn=v.get("snippet",{})
   if s.get("license")!="creativeCommon": continue
   if cfg.get("require_public",True) and s.get("privacyStatus")!="public": continue
   vid=v.get("id"); url="https://www.youtube.com/watch?v="+vid
   verified.append({"source_url":url,"video_id":vid,"title":sn.get("title",""),"source_creator":sn.get("channelTitle",""),"channel_id":sn.get("channelId",""),"duration_seconds":iso8601_seconds(v.get("contentDetails",{}).get("duration","")),"license":"CC BY / Creative Commons","license_verified":True,"verification_source":"YouTube Data API status.license=creativeCommon","discovery_query":found.get(vid),"verified_at":now,"attribution_required":True})
 OUT.write_text(json.dumps({"schema_version":1,"generated_at":now,"status":"ok","sources":verified},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(f"CC discovery: verified={len(verified)}")
if __name__=="__main__": main()
