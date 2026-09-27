import html
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "publish_queue.json"
LEARNING = ROOT / "data" / "learning_records.json"
OUT = ROOT / "data" / "hashtag_trends.json"

TIKTOK_URL = "https://ads.tiktok.com/creative/creativeCenter/trends/hashtag?region=ES"
TIMEOUT = 15
MAX_HASHTAGS = 8
MIN_HASHTAGS = 3
GENERIC = {"viral","fyp","foryou","foryoupage","parati","trending","trend","xyzbca","fy","shorts","short","youtube"}

def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default

def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; LagartoShortsFactory/1.0)",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", errors="replace")

def normalize_tag(value):
    value = html.unescape(str(value or "")).strip().lower().lstrip("#").replace(" ", "")
    value = re.sub(r"[^a-z0-9_áéíóúüñ-]", "", value)
    if not value or value in GENERIC or len(value) < 3 or len(value) > 45:
        return None
    return "#" + value

def tiktok_trends():
    try:
        raw = fetch(TIKTOK_URL)
    except Exception as exc:
        return {"source":"tiktok_creative_center","status":"unavailable","error":str(exc),"items":[]}
    found = {}
    for pattern in (r'"hashtagName"\s*:\s*"([^"]+)"', r'"hashtag"\s*:\s*"([^"]+)"'):
        for match in re.findall(pattern, raw, flags=re.I):
            tag = normalize_tag(match)
            if tag:
                found[tag] = found.get(tag, 0) + 1
    if not found:
        for match in re.findall(r"(?<![A-Za-z0-9_])#([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_]{3,45})", raw):
            tag = normalize_tag(match)
            if tag:
                found[tag] = found.get(tag, 0) + 1
    ranked = sorted(found.items(), key=lambda x:x[1], reverse=True)[:100]
    return {"source":"tiktok_creative_center","status":"ok" if ranked else "no_data","url":TIKTOK_URL,
            "items":[{"hashtag":tag,"source_score":count} for tag,count in ranked]}

def youtube_trends():
    required=("YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_REFRESH_TOKEN")
    if any(not os.getenv(name) for name in required):
        return {"source":"youtube_most_popular","status":"unavailable","items":[],"reason":"oauth_missing"}
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds=Credentials(token=None,refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
            token_uri="https://oauth2.googleapis.com/token",client_id=os.environ["YOUTUBE_CLIENT_ID"],
            client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],scopes=["https://www.googleapis.com/auth/youtube.readonly"])
        creds.refresh(Request())
        youtube=build("youtube","v3",credentials=creds,cache_discovery=False)
        response=youtube.videos().list(part="snippet",chart="mostPopular",regionCode="ES",maxResults=50).execute()
    except Exception as exc:
        return {"source":"youtube_most_popular","status":"unavailable","items":[],"error":str(exc)}
    counts={}
    for item in response.get("items",[]):
        text=" ".join([str(item.get("snippet",{}).get("title","")),str(item.get("snippet",{}).get("description",""))])
        for raw_tag in re.findall(r"(?<![A-Za-z0-9_])#([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_]{3,45})",text):
            tag=normalize_tag(raw_tag)
            if tag: counts[tag]=counts.get(tag,0)+1
    ranked=sorted(counts.items(),key=lambda x:x[1],reverse=True)[:100]
    return {"source":"youtube_most_popular","status":"ok" if ranked else "no_data",
            "items":[{"hashtag":tag,"source_score":count} for tag,count in ranked]}

def tokenize(text):
    return {w for w in re.findall(r"[a-záéíóúüñ0-9]{3,}",str(text or "").lower()) if w not in GENERIC}

def historical_scores():
    records=load(LEARNING,[])
    if not isinstance(records,list): records=records.get("records",[])
    stats={}
    for record in records:
        try: retention=float(record.get("metrics",{}).get("average_percentage_viewed"))
        except (TypeError,ValueError): continue
        for raw in (record.get("hashtags",[]) or record.get("hashtag_set",[])):
            tag=normalize_tag(raw)
            if tag: stats.setdefault(tag,[]).append(retention)
    return {tag:sum(values)/len(values) for tag,values in stats.items() if values}

def choose_tags(job, source_items, historical):
    meta=job.get("learning_metadata",{})
    text=" ".join([job.get("title",""),job.get("description",""),job.get("source_creator",""),
                   meta.get("original_context","")," ".join(meta.get("emotion_signals",[]))]).lower()
    tokens=tokenize(text)
    candidates={}
    for source_name,items in source_items.items():
        for rank,item in enumerate(items[:100]):
            tag=item["hashtag"]; bare=tag[1:].lower()
            relevance=25 if bare in tokens else 0
            if any(token in bare or bare in token for token in tokens if len(token)>=4): relevance+=10
            trend=max(0,30-rank*0.3)
            hist=min(20,max(0,historical.get(tag,0)/5))
            data=candidates.setdefault(tag,{"score":0,"sources":set(),"trend_score":0,"historical_score":historical.get(tag,0)})
            data["score"]+=relevance+trend+hist
            data["sources"].add(source_name)
            data["trend_score"]+=trend
    ranked=sorted(candidates.items(),key=lambda x:x[1]["score"],reverse=True)
    selected=[tag for tag,_ in ranked[:MAX_HASHTAGS]]
    if len(selected)<MIN_HASHTAGS:
        for tag in ("#reaccion","#momento","#clips"):
            if tag not in selected: selected.append(tag)
            if len(selected)>=MIN_HASHTAGS: break
    details=[]
    for tag in selected[:MAX_HASHTAGS]:
        data=candidates.get(tag,{"score":0,"sources":set(),"trend_score":0,"historical_score":0})
        details.append({"hashtag":tag,"score":round(data["score"],2),"trend_score":round(data["trend_score"],2),
                        "historical_retention":round(data["historical_score"],2),"sources":sorted(data["sources"])})
    return selected[:MAX_HASHTAGS],details

def main():
    queue=load(QUEUE,{"schema_version":1,"jobs":[]})
    historical=historical_scores()
    tiktok=tiktok_trends(); youtube=youtube_trends()
    sources={"tiktok_creative_center":tiktok.get("items",[]),"youtube_most_popular":youtube.get("items",[])}
    generated=[]
    for job in queue.get("jobs",[]):
        if job.get("status")=="uploaded": continue
        tags,details=choose_tags(job,sources,historical)
        job["hashtags"]=tags; job["hashtag_sources"]=details
        metadata=job.setdefault("learning_metadata",{})
        metadata["hashtags"]=tags; metadata["hashtag_sources"]=details
        metadata["trend_snapshot_at"]=datetime.now(timezone.utc).isoformat()
        description=str(job.get("description","")).strip()
        tag_line=" ".join(tags)
        if tag_line and tag_line not in description: job["description"]=(description+"\n\n"+tag_line)[:5000]
        generated.append({"clip_id":job.get("clip_id"),"hashtags":tags,"details":details})
    QUEUE.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    OUT.write_text(json.dumps({"schema_version":1,"generated_at":datetime.now(timezone.utc).isoformat(),
        "sources":{"tiktok_creative_center":{k:v for k,v in tiktok.items() if k!="items"},
                   "youtube_most_popular":{k:v for k,v in youtube.items() if k!="items"}},
        "jobs":generated},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Trend/hashtag engine: jobs={len(generated)}")

if __name__=="__main__": main()
