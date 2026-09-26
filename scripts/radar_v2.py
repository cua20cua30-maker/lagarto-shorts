import json
import re
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'config'/'creators.json'
OUT=ROOT/'data'/'candidates.json'

def norm(v): return re.sub(r'[^a-z0-9]','',(v or '').lower())

def search(name,limit=20):
 p=subprocess.run(['yt-dlp','--flat-playlist','--dump-single-json','--playlist-end',str(limit),f'ytsearchdate{limit}:{name}'],capture_output=True,text=True,timeout=120)
 if p.returncode: return []
 try: return json.loads(p.stdout).get('entries',[])
 except json.JSONDecodeError: return []

def score(title):
 t=(title or '').lower(); signals=('reacción','reaccion','increíble','increible','polémica','polemica','humilla','humilló','explota','locura','nadie esperaba','se lía','se lia','viral','wtf','qué coño','que coño','no puede ser')
 return min(100,sum(10 for s in signals if s in t))

def main():
 cfg=json.loads(CONFIG.read_text(encoding='utf-8')); now=datetime.now(timezone.utc); cutoff=now-timedelta(days=7); candidates=[]
 for creator in cfg['creators']:
  if not creator.get('enabled',True): continue
  name=creator['name']
  for item in search(name):
   if not item.get('id'): continue
   uploader=item.get('channel') or item.get('uploader') or ''
   if norm(uploader)!=norm(name): continue
   date=item.get('upload_date')
   if date:
    try:
     published=datetime.strptime(date,'%Y%m%d').replace(tzinfo=timezone.utc)
     if published<cutoff: continue
    except ValueError: pass
   candidates.append({'candidate_id':f"yt:{item['id']}",'source_creator':name,'source_url':f"https://www.youtube.com/watch?v={item['id']}",'title':item.get('title',''),'duration_seconds':item.get('duration'),'score':score(item.get('title','')),'detected_at':now.isoformat(),'status':'discovered','authorization_status':'unknown','publishable':False})
 dedup={x['candidate_id']:x for x in candidates}
 OUT.write_text(json.dumps({'schema_version':1,'generated_at':now.isoformat(),'candidates':sorted(dedup.values(),key=lambda x:x['score'],reverse=True)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f"Radar v2: {len(dedup)} candidates")

if __name__=='__main__': main()
