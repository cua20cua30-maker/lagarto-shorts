"""Web trend research for hooks, titles, topics and hashtags.
Research is advisory: it feeds experiments, never guarantees virality.
"""
import html,json,re,urllib.request
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"data/trend_research.json"; LEARN=ROOT/"data/learning_records.json"
TIMEOUT=15
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"LagartoShortsFactory/2.0","Accept-Language":"es-ES,es;q=0.9"})
    with urllib.request.urlopen(req,timeout=TIMEOUT) as r:return r.read().decode("utf-8","replace")
def load(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return d
def clean(x): return re.sub(r"\\s+"," ",html.unescape(str(x or ""))).strip()
def google_trends():
    try: raw=fetch("https://trends.google.com/trending/rss?geo=ES")
    except Exception as e:return {"status":"unavailable","items":[],"error":str(e)}
    items=[]
    for title in re.findall(r"<title>(.*?)</title>",raw,re.I|re.S)[1:]:
        t=clean(re.sub("<.*?>","",title))
        if t and t not in items:items.append(t)
    return {"status":"ok" if items else "no_data","items":items[:50]}
def youtube_titles():
    import os
    if not all(os.getenv(k) for k in ("YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_REFRESH_TOKEN")):
        return {"status":"unavailable","items":[]}
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        c=Credentials(token=None,refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],token_uri="https://oauth2.googleapis.com/token",client_id=os.environ["YOUTUBE_CLIENT_ID"],client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],scopes=["https://www.googleapis.com/auth/youtube.readonly"])
        c.refresh(Request()); yt=build("youtube","v3",credentials=c,cache_discovery=False)
        data=yt.videos().list(part="snippet",chart="mostPopular",regionCode="ES",maxResults=50).execute()
        return {"status":"ok","items":[clean(x.get("snippet",{}).get("title")) for x in data.get("items",[]) if x.get("snippet",{}).get("title")]}
    except Exception as e:return {"status":"unavailable","items":[],"error":str(e)}
def main():
    gt=google_trends(); yt=youtube_titles(); records=load(LEARN,[])
    if isinstance(records,dict):records=records.get("records",[])
    hooks=[]
    for x in yt.get("items",[]): 
        low=x.lower()
        if any(k in low for k in ("nadie","cómo","como","qué","que","no puede","increíble","increible","última","ultimo","por fin","esto")): hooks.append(x)
    OUT.write_text(json.dumps({"schema_version":2,"generated_at":datetime.now(timezone.utc).isoformat(),"research":{"google_trends_es":gt,"youtube_popular_titles":yt},"hook_examples":hooks[:30],"historical_samples":len(records),"note":"Trend signals guide experiments; no method can guarantee virality."},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Trend research: google={gt.get('status')} youtube={yt.get('status')} hooks={len(hooks)}")
if __name__=="__main__":main()
