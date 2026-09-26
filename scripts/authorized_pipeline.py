import json
import os
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CANDIDATES=ROOT/'data'/'candidates.json'
AUTH=ROOT/'data'/'authorization_manifest.json'
MOMENTS=ROOT/'data'/'moments.json'
PLANS=ROOT/'data'/'clip_plans.json'
WORK=ROOT/'.work'

def load(path,default):
    if not path.exists(): return default
    return json.loads(path.read_text(encoding='utf-8'))

def run(cmd):
    return subprocess.run(cmd,check=False)

def main():
    candidates=load(CANDIDATES,{'candidates':[]}).get('candidates',[])
    allowed=set(load(AUTH,{'authorized_sources':[]}).get('authorized_sources',[]))
    selected=[c for c in candidates if c.get('source_url') in allowed]
    if not selected:
        MOMENTS.write_text(json.dumps({'schema_version':1,'moments':[]},indent=2)+'\n',encoding='utf-8')
        PLANS.write_text(json.dumps({'schema_version':1,'plans':[]},indent=2)+'\n',encoding='utf-8')
        print('Authorized pipeline: no authorized sources; nothing downloaded or processed.')
        return
    WORK.mkdir(exist_ok=True)
    all_moments=[]
    all_plans=[]
    for candidate in selected:
        cid=candidate['candidate_id'].replace(':','_')
        source=WORK/f'{cid}.mp4'; transcript=WORK/f'{cid}.json'; moments=WORK/f'{cid}_moments.json'; plans=WORK/f'{cid}_plans.json'
        if not source.exists():
            result=run(['yt-dlp','--no-playlist','-f','bv*+ba/b','--merge-output-format','mp4','-o',str(source),candidate['source_url']])
            if result.returncode: continue
        result=run(['python','scripts/transcriber.py','--input',str(source),'--output',str(transcript)])
        if result.returncode: continue
        result=run(['python','scripts/moment_detector.py','--input',str(transcript),'--output',str(moments)])
        if result.returncode: continue
        result=run(['python','scripts/clip_planner.py','--input',str(moments),'--output',str(plans)])
        if result.returncode: continue
        all_moments.extend(load(moments,{'moments':[]}).get('moments',[]))
        all_plans.extend(load(plans,{'plans':[]}).get('plans',[]))
    MOMENTS.write_text(json.dumps({'schema_version':1,'moments':all_moments},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    PLANS.write_text(json.dumps({'schema_version':1,'plans':all_plans},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Authorized pipeline: processed {len(selected)} authorized candidates; moments={len(all_moments)} plans={len(all_plans)}')

if __name__=='__main__': main()
