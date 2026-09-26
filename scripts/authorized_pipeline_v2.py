import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];CANDIDATES=ROOT/'data/candidates.json';AUTH=ROOT/'data/authorization_manifest.json';MOMENTS=ROOT/'data/moments.json';PLANS=ROOT/'data/clip_plans.json';SCREAMS=ROOT/'data/scream_events.json';EMOTIONS=ROOT/'data/emotion_events.json';WORK=ROOT/'.work'
def load(path,default):return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
def run(c):return subprocess.run(c,check=False)
def main():
 candidates=load(CANDIDATES,{'candidates':[]}).get('candidates',[]);allowed=set(load(AUTH,{'authorized_sources':[]}).get('authorized_sources',[]));selected=[c for c in candidates if c.get('source_url') in allowed];all_moments=[];all_plans=[];all_screams=[];all_emotions=[];WORK.mkdir(exist_ok=True)
 for c in selected:
  cid=c['candidate_id'].replace(':','_');source=WORK/f'{cid}.mp4';transcript=WORK/f'{cid}.json';sf=WORK/f'{cid}_screams.json';ef=WORK/f'{cid}_emotions.json';mf=WORK/f'{cid}_moments.json';pf=WORK/f'{cid}_plans.json'
  if not source.exists():
   if run(['yt-dlp','--no-playlist','-f','bv*+ba/b','--merge-output-format','mp4','-o',str(source),c['source_url']]).returncode:continue
  if run(['python','scripts/scream_detector.py','--input',str(source),'--output',str(sf)]).returncode:continue
  if run(['python','scripts/transcriber.py','--input',str(source),'--output',str(transcript)]).returncode:continue
  if run(['python','scripts/emotion_detector.py','--input',str(source),'--transcript',str(transcript),'--output',str(ef)]).returncode:continue
  if run(['python','scripts/moment_detector.py','--input',str(transcript),'--output',str(mf),'--screams',str(sf),'--emotions',str(ef)]).returncode:continue
  if run(['python','scripts/clip_planner.py','--input',str(mf),'--output',str(pf)]).returncode:continue
  sd=load(sf,{'events':[]});ed=load(ef,{'events':[]});md=load(mf,{'moments':[]});pd=load(pf,{'plans':[]})
  for e in sd.get('events',[]):e.update(candidate_id=c['candidate_id'],source_path=str(source),source_creator=c['source_creator']);all_screams.append(e)
  for e in ed.get('events',[]):e.update(candidate_id=c['candidate_id'],source_path=str(source),source_creator=c['source_creator']);all_emotions.append(e)
  for m in md.get('moments',[]):m.update(candidate_id=c['candidate_id'],source_path=str(source),source_creator=c['source_creator'],transcript_path=str(transcript));all_moments.append(m)
  for p in pd.get('plans',[]):p.update(candidate_id=c['candidate_id'],source_path=str(source),source_creator=c['source_creator'],transcript_path=str(transcript));all_plans.append(p)
 EMOTIONS.write_text(json.dumps({'schema_version':1,'events':all_emotions},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');SCREAMS.write_text(json.dumps({'schema_version':1,'events':all_screams},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');MOMENTS.write_text(json.dumps({'schema_version':2,'moments':all_moments},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');PLANS.write_text(json.dumps({'schema_version':1,'plans':all_plans},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(f'Authorized pipeline v2: selected={len(selected)} screams={len(all_screams)} moments={len(all_moments)} plans={len(all_plans)}')
if __name__=='__main__':main()
