"""Near-real-time live/VOD radar for the Shorts factory.
Uses official Twitch Helix and Kick Public API metadata. It never acquires media.
"""
import json, os, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CREATORS=ROOT/"config/creators.json"
OUT=ROOT/"data/live_radar.json"
STATE=ROOT/"data/live_state.json"
TW_TOKEN="https://id.twitch.tv/oauth2/token"
TW_API="https://api.twitch.tv/helix"
KICK_TOKEN="https://id.kick.com/oauth/token"
KICK_API="https://api.kick.com/public/v1"

def load(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return d

def request(url, headers=None, data=None):
    req=urllib.request.Request(url,headers=headers or {},data=data,method="POST" if data else "GET")
    with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read().decode())

def twitch_token():
    cid=os.getenv("TWITCH_CLIENT_ID"); sec=os.getenv("TWITCH_CLIENT_SECRET")
    if not cid or not sec:return None
    data=urllib.parse.urlencode({"client_id":cid,"client_secret":sec,"grant_type":"client_credentials"}).encode()
    return request(TW_TOKEN,{"Content-Type":"application/x-www-form-urlencoded"},data).get("access_token")

def kick_token():
    cid=os.getenv("KICK_CLIENT_ID"); sec=os.getenv("KICK_CLIENT_SECRET")
    if not cid or not sec:return None
    data=urllib.parse.urlencode({"client_id":cid,"client_secret":sec,"grant_type":"client_credentials"}).encode()
    return request(KICK_TOKEN,{"Content-Type":"application/x-www-form-urlencoded"},data).get("access_token")

def api(base,path,token,client=None,params=None):
    q=urllib.parse.urlencode(params or {},doseq=True)
    h={"Authorization":"Bearer "+token}
    if client:h["Client-Id"]=client
    return request(base+path+("?"+q if q else ""),h)

def main():
    cfg=load(CREATORS,{"creators":[]}); now=datetime.now(timezone.utc)
    prev=load(STATE,{"streams":{}})
    streams={}; events=[]; diagnostics=[]
    tt=twitch_token()
    if tt:
        logins=[c.get("twitch_login") for c in cfg["creators"] if c.get("enabled",True) and c.get("twitch_login")]
        try:
            data=api(TW_API,"/streams",tt,os.getenv("TWITCH_CLIENT_ID"),{"user_login":logins,"first":100}).get("data",[])
            for s in data:
                key="twitch:"+str(s["user_id"]); streams[key]=s
                if key not in prev.get("streams",{}):
                    events.append({"event":"stream_online","platform":"twitch","creator":s["user_name"],"stream_id":s["id"],"started_at":s["started_at"]})
            diagnostics.append({"platform":"twitch","status":"ok","live":len(data)})
        except Exception as e: diagnostics.append({"platform":"twitch","status":"error","error":str(e)})
    else: diagnostics.append({"platform":"twitch","status":"not_configured"})
    kt=kick_token()
    if kt:
        for c in cfg["creators"]:
            if not c.get("enabled",True) or not c.get("kick_slug"): continue
            try:
                ch=api(KICK_API,"/channels",kt,None,{"slug":c["kick_slug"]}).get("data",[])
                if not ch: continue
                uid=ch[0].get("broadcaster_user_id") or ch[0].get("user_id")
                live=api(KICK_API,"/livestreams",kt,None,{"broadcaster_user_id":uid}).get("data",[])
                for s in live:
                    key="kick:"+str(uid); streams[key]=s
                    if key not in prev.get("streams",{}):
                        events.append({"event":"stream_online","platform":"kick","creator":c["name"],"stream_id":s.get("id"),"started_at":s.get("created_at") or s.get("started_at")})
                diagnostics.append({"platform":"kick","creator":c["name"],"status":"ok_live" if live else "ok_offline","live":len(live)})
            except Exception as e: diagnostics.append({"platform":"kick","creator":c["name"],"status":"error","error":str(e)})
    else: diagnostics.append({"platform":"kick","status":"not_configured"})
    OUT.write_text(json.dumps({"schema_version":1,"checked_at":now.isoformat(),"live":list(streams.values()),"events":events,"diagnostics":diagnostics},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    STATE.write_text(json.dumps({"schema_version":1,"checked_at":now.isoformat(),"streams":streams},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Live radar: live={len(streams)} new_events={len(events)}")
if __name__=="__main__": main()
