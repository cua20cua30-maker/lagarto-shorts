"""Kick VOD discovery gate.

The official Kick Public API currently exposes channel/livestream metadata,
but no public channel-VOD listing/media endpoint. Never turn live metadata
into a VOD candidate.
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config/creators.json"
OUT=ROOT/"data/kick_candidates.json"
DIAG=ROOT/"data/kick_radar_diagnostics.json"
TOKEN_URL="https://id.kick.com/oauth/token"

def load(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError):return default

def token():
    cid,sec=os.getenv("KICK_CLIENT_ID"),os.getenv("KICK_CLIENT_SECRET")
    if not cid or not sec:return None,"missing Kick credentials"
    body=urllib.parse.urlencode({"grant_type":"client_credentials","client_id":cid,"client_secret":sec}).encode()
    req=urllib.request.Request(TOKEN_URL,data=body,headers={"Content-Type":"application/x-www-form-urlencoded"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=20) as r:data=json.loads(r.read().decode())
        return data.get("access_token"),None
    except Exception as e:return None,f"{type(e).__name__}: {e}"

def main():
    cfg=load(CONFIG,{"creators":[]}); now=datetime.now(timezone.utc); tok,err=token()
    reason="Kick Public API has no public channel-VOD listing/media endpoint; live metadata is not treated as VOD."
    results=[]
    for c in cfg.get("creators",[]):
        if c.get("enabled",True) and c.get("kick_slug"):
            results.append({"creator":c["name"],"platform":"kick","status":"vod_unavailable_official_api",
                            "kick_slug":c["kick_slug"],"api_authenticated":bool(tok),
                            "error":err if not tok else None,"reason":reason})
    DIAG.write_text(json.dumps({"schema_version":2,"generated_at":now.isoformat(),"mode":"vod_only","results":results},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    OUT.write_text(json.dumps({"schema_version":2,"generated_at":now.isoformat(),"mode":"vod_only","candidates":[],"note":reason},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Kick VOD radar: discovered=0; official_vod_api=false")

if __name__=="__main__":main()
