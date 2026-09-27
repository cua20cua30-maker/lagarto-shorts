import json
import os
from datetime import datetime, timezone
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"data"/"published.json"
QUEUE=ROOT/"data"/"publish_queue.json"
OUT=ROOT/"data"/"publication_recovery.json"
SCOPES=["https://www.googleapis.com/auth/youtube.readonly"]
MAX_REMEDIATIONS=3

def load(path,default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError): return default

def classify(video):
    status=video.get("status",{}); processing=video.get("processingDetails",{})
    upload=status.get("uploadStatus"); rejection=status.get("rejectionReason"); failure=status.get("failureReason")
    pstatus=processing.get("processingStatus"); pfailure=processing.get("processingFailureReason")
    if upload=="rejected":
        if rejection in {"claim","copyright"}: return "copyright_or_claim",rejection
        if rejection=="duplicate": return "duplicate",rejection
        return "policy_or_metadata",rejection or "unknown"
    if upload=="failed": return "upload_failure",failure or "unknown"
    if pstatus=="failed": return "processing_failure",pfailure or "unknown"
    if pstatus=="succeeded" or upload=="processed": return "healthy",None
    return "processing",pstatus or upload or "unknown"

def remediation(state):
    if state=="processing_failure":
        return {"action":"rerender_technical_fallback","allowed":True,
                "notes":"Re-render with conservative MP4/H.264/AAC settings; never alter content to evade detection."}
    if state=="upload_failure":
        return {"action":"retry_upload","allowed":True,"notes":"Retry only transient delivery failures."}
    if state=="copyright_or_claim":
        return {"action":"rights_review_or_audio_replacement","allowed":False,
                "notes":"Only trim, mute or replace claimed material when lawful and rights are clear."}
    if state=="policy_or_metadata":
        return {"action":"manual_review_metadata","allowed":False,
                "notes":"Review the policy/rejection reason before retrying."}
    if state=="duplicate":
        return {"action":"do_not_reupload","allowed":False,"notes":"Do not repeatedly upload the same asset."}
    return {"action":"wait","allowed":False,"notes":"YouTube is still processing the upload."}

def main():
    required=("YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_REFRESH_TOKEN")
    if any(not os.getenv(name) for name in required):
        print("Publication monitor: OAuth secrets missing; skipped safely."); return
    creds=Credentials(token=None,refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],scopes=SCOPES)
    try:
        creds.refresh(Request()); youtube=build("youtube","v3",credentials=creds,cache_discovery=False)
    except Exception as exc:
        print(f"Publication monitor: OAuth/API setup failed; skipped safely: {exc}"); return
    ledger=load(LEDGER,{"schema_version":1,"items":[]}); queue=load(QUEUE,{"schema_version":1,"jobs":[]})
    history=load(OUT,{"schema_version":1,"updated_at":None,"items":[]})
    previous={x.get("video_id"):x for x in history.get("items",[]) if x.get("video_id")}
    queue_by_clip={x.get("clip_id"):x for x in queue.get("jobs",[]) if x.get("clip_id")}
    for item in ledger.get("items",[]):
        video_id=item.get("video_id")
        if not video_id: continue
        try: videos=youtube.videos().list(part="status,processingDetails",id=video_id).execute().get("items",[])
        except Exception as exc:
            print(f"Publication monitor: {video_id}: API error: {exc}"); continue
        if not videos: continue
        state,detail=classify(videos[0]); action=remediation(state)
        old=previous.get(video_id,{})
        record={"video_id":video_id,"clip_id":item.get("clip_id"),
                "checked_at":datetime.now(timezone.utc).isoformat(),"state":state,"detail":detail,
                "remediation":action,"attempts":int(old.get("attempts",0))}
        if state in {"processing_failure","upload_failure"} and action["allowed"]:
            if record["attempts"]<MAX_REMEDIATIONS:
                record["attempts"]+=1; record["remediation_status"]="queued"
            else: record["remediation_status"]="stopped_after_limit"
        elif state in {"copyright_or_claim","policy_or_metadata"}:
            record["remediation_status"]="blocked_pending_rights_or_review"
        else: record["remediation_status"]="none"
        previous[video_id]=record
        job=queue_by_clip.get(item.get("clip_id"))
        if job:
            job["publication_state"]=state; job["publication_detail"]=detail; job["remediation"]=action
    history["updated_at"]=datetime.now(timezone.utc).isoformat(); history["items"]=list(previous.values())
    OUT.write_text(json.dumps(history,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    QUEUE.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Publication monitor: checked={len(previous)}")

if __name__=="__main__": main()
