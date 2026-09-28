"""Kick VOD discovery gate.

The official Kick Developer Public API currently exposes livestream/channel
metadata but does not expose a public channel-VOD listing/media endpoint.
This module therefore NEVER treats a live stream as a VOD candidate and
returns an explicit diagnostic instead of using undocumented scraping.
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/creators.json"
OUT = ROOT / "data/kick_candidates.json"
DIAG = ROOT / "data/kick_radar_diagnostics.json"
TOKEN_URL = "https://id.kick.com/oauth/token"

def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default

def token():
    client_id = os.getenv("KICK_CLIENT_ID")
    client_secret = os.getenv("KICK_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None, "missing Kick credentials"
    body = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, headers={"Content-Type":"application/x-www-form-urlencoded","User-Agent":"LagartoShortsFactory/3.0"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data=json.loads(response.read().decode())
        access_token=data.get("access_token")
        return (access_token,None) if access_token else (None,"Kick token response did not contain access_token")
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"

def main():
    cfg=load(CONFIG,{"creators":[]})
    now=datetime.now(timezone.utc)
    access_token,auth_error=token()
    diagnostics=[]
    reason=("Kick official Public API currently provides livestream/channel metadata "
            "but no public channel-VOD listing/media endpoint. Live streams are not "
            "converted into VOD candidates. Undocumented website endpoints/scraping "
            "are intentionally disabled.")
    for creator in cfg.get("creators",[]):
        if not creator.get("enabled",True) or not creator.get("kick_slug"):
            continue
        diagnostics.append({"creator":creator["name"],"platform":"kick","status":"vod_unavailable_official_api",
                            "kick_slug":creator["kick_slug"],"api_authenticated":bool(access_token),
                            "error":auth_error if not access_token else None,"reason":reason})
    DIAG.write_text(json.dumps({"schema_version":2,"generated_at":now.isoformat(),"mode":"vod_only",
                                "api":"Kick Developer Public API","results":diagnostics},
                               ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    OUT.write_text(json.dumps({"schema_version":2,"generated_at":now.isoformat(),"mode":"vod_only",
                               "candidates":[],"note":reason},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Kick VOD radar: discovered=0; official_vod_api=false")

if __name__=="__main__":
    main()
