import json
import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT=Path(__file__).resolve().parents[1]; QUEUE=ROOT/'data'/'publish_queue.json'; RENDER=ROOT/'data'/'render_queue.json'; LEDGER=ROOT/'data'/'published.json'; SCOPES=['https://www.googleapis.com/auth/youtube.upload']
def load(p,d): return json.loads(p.read_text(encoding='utf-8')) if p.exists() else d
def main():
 q=load(QUEUE,{'jobs':[]}); r=load(RENDER,{'jobs':[]}); ledger=load(LEDGER,{'schema_version':1,'items':[]}); done={x.get('idempotency_key'):x for x in ledger.get('items',[])}; rendered={x.get('candidate_id'):x for x in r.get('jobs',[]) if x.get('status')=='rendered'}
 if os.getenv('YOUTUBE_AUTO_PUBLISH','false').lower()!='true': print('Publisher v3: auto-publish disabled; dry-run.'); return
 if any(not os.getenv(x) for x in ('YOUTUBE_CLIENT_ID','YOUTUBE_CLIENT_SECRET','YOUTUBE_REFRESH_TOKEN')): print('Publisher v3: OAuth secrets missing; blocked.'); return
 creds=Credentials(None,refresh_token=os.environ['YOUTUBE_REFRESH_TOKEN'],token_uri='https://oauth2.googleapis.com/token',client_id=os.environ['YOUTUBE_CLIENT_ID'],client_secret=os.environ['YOUTUBE_CLIENT_SECRET'],scopes=SCOPES); creds.refresh(Request()); yt=build('youtube','v3',credentials=creds); changed=False
 for job in q.get('jobs',[]):
  key=job.get('idempotency_key'); item=rendered.get(job.get('candidate_id')); 
  if not key or key in done or not item: continue
  path=Path(item['output'])
  if not path.exists(): continue
  request=yt.videos().insert(part='snippet,status',body={'snippet':{'title':f"Lagarto | {item.get('source_creator','Short')}",'description':'Contenido transformado a partir de material autorizado.','categoryId':'24'},'status':{'privacyStatus':os.getenv('YOUTUBE_PRIVACY_STATUS','unlisted'),'selfDeclaredMadeForKids':False}},media_body=MediaFileUpload(str(path),mimetype='video/mp4',resumable=True)); response=None
  while response is None: _,response=request.next_chunk()
  record={'idempotency_key':key,'candidate_id':job.get('candidate_id'),'video_id':response['id'],'privacy_status':os.getenv('YOUTUBE_PRIVACY_STATUS','unlisted')}; ledger['items'].append(record); done[key]=record; job['status']='uploaded'; job['video_id']=response['id']; changed=True
 if changed: LEDGER.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); QUEUE.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f"Publisher v3: ledger={len(ledger['items'])}")
if __name__=='__main__': main()
