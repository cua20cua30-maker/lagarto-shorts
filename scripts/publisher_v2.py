import json
import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT=Path(__file__).resolve().parents[1]; QUEUE=ROOT/'data'/'publish_queue.json'; RENDER=ROOT/'data'/'render_queue.json'
SCOPES=['https://www.googleapis.com/auth/youtube.upload']

def main():
 queue=json.loads(QUEUE.read_text(encoding='utf-8')) if QUEUE.exists() else {'jobs':[]}; rendered=json.loads(RENDER.read_text(encoding='utf-8')) if RENDER.exists() else {'jobs':[]}; files={x.get('candidate_id'):x for x in rendered.get('jobs',[]) if x.get('status')=='rendered'}
 if os.getenv('YOUTUBE_AUTO_PUBLISH','false').lower()!='true': print('Publisher v2: auto-publish disabled; safe dry-run.'); return
 required=('YOUTUBE_CLIENT_ID','YOUTUBE_CLIENT_SECRET','YOUTUBE_REFRESH_TOKEN')
 if any(not os.getenv(x) for x in required): print('Publisher v2: OAuth secrets missing; safely blocked.'); return
 creds=Credentials(None,refresh_token=os.environ['YOUTUBE_REFRESH_TOKEN'],token_uri='https://oauth2.googleapis.com/token',client_id=os.environ['YOUTUBE_CLIENT_ID'],client_secret=os.environ['YOUTUBE_CLIENT_SECRET'],scopes=SCOPES)
 creds.refresh(Request()); youtube=build('youtube','v3',credentials=creds)
 changed=False
 for job in queue.get('jobs',[]):
  if job.get('status') not in ('blocked_until_rendered','queued'): continue
  item=files.get(job.get('candidate_id'))
  if not item: continue
  path=Path(item['output'])
  if not path.exists(): continue
  title=(job.get('title') or 'Lagarto Short').strip()[:100]
  body={'snippet':{'title':title,'description':'Transformación original a partir de material autorizado.','categoryId':'24'},'status':{'privacyStatus':os.getenv('YOUTUBE_PRIVACY_STATUS','unlisted'),'selfDeclaredMadeForKids':False}}
  request=youtube.videos().insert(part='snippet,status',body=body,media_body=MediaFileUpload(str(path),mimetype='video/mp4',resumable=True))
  response=None
  while response is None:
   _,response=request.next_chunk()
  job['status']='uploaded'; job['video_id']=response['id']; job['privacy_status']=body['status']['privacyStatus']; changed=True
 if changed: QUEUE.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f"Publisher v2: uploaded={sum(1 for j in queue.get('jobs',[]) if j.get('status')=='uploaded')}")

if __name__=='__main__': main()
