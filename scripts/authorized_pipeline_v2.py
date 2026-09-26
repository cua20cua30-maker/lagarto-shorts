import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; CANDIDATES=ROOT/'data'/'candidates.json'; AUTH=ROOT/'data'/'authorization_manifest.json'; MOMENTS=ROOT/'data'/'moments.json'; PLANS=ROOT/'data'/'clip_plans.json'; WORK=ROOT/'.work'

def load(p,d):
 return json.loads(p.read_text(encoding='utf-8')) if p.exists() else d

def run(c): return subprocess.run(c,check=False)

def main():
 candidates=load(CANDIDATES,{'candidates':[]}).get('candidates',[]); allowed=set(load(AUTH,{'authorized_sources':[]}).get('authorized_sources',[])); selected=[c for c in candidates if c.get('source_url') in allowed]
 allm=[]; allp=[]; WORK.mkdir(exist_ok=True)
 for c in selected:
  cid=c['candidate_id'].replace(':','_'); source=WORK/f'{cid}.mp4'; transcript=WORK/f'{cid}.json'; moments=WORK/f'{cid}_moments.json'; plans=WORK/f'{cid}_plans.json'
  if not source.exists() and run(['yt-dlp','--no-playlist','-f','bv*+ba/b','--merge-output-format','mp4','-o',str(source),c['source_url']]).returncode: continue
  if run(['python','scripts/transcriber.py','--input',str(source),'--output',str(transcript)]).returncode: continue
  if run(['python','scripts/moment_detector.py','--input',str(transcript),'--output',str(moments)]).returncode: continue
  if run(['python','scripts/clip_planner.py','--input',str(moments),'--output',str(plans)]).returncode: continue
  md=load(moments,{'moments':[]}); pd=load(plans,{'plans':[]})
  for m in md.get('moments',[]): m['candidate_id']=c['candidate_id']; m['source_path']=str(source); m['source_creator']=c['source_creator']; allm.append(m)
  for p in pd.get('plans',[]): p['candidate_id']=c['candidate_id']; p['source_path']=str(source); p['source_creator']=c['source_creator']; allp.append(p)
 MOMENTS.write_text(json.dumps({'schema_version':1,'moments':allm},ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); PLANS.write_text(json.dumps({'schema_version':1,'plans':allp},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'Authorized pipeline v2: selected={len(selected)} moments={len(allm)} plans={len(allp)}')

if __name__=='__main__': main()
