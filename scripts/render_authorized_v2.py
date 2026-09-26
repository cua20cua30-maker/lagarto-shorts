import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; WORK=ROOT/'.work'; PLANS=ROOT/'data'/'clip_plans.json'; OUT=ROOT/'data'/'render_queue.json'

def main():
 plans=json.loads(PLANS.read_text(encoding='utf-8')).get('plans',[]) if PLANS.exists() else []; jobs=[]
 for p in plans:
  source=Path(p['source_path']); output=WORK/f"{p['clip_id'].replace(':','_')}.mp4"
  if not source.exists(): continue
  cmd=['ffmpeg','-y','-ss',str(p['start']),'-i',str(source),'-t',str(p['duration']),'-vf','scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920','-c:v','libx264','-preset','veryfast','-crf','21','-c:a','aac','-b:a','128k','-movflags','+faststart',str(output)]
  result=subprocess.run(cmd,capture_output=True,text=True)
  if result.returncode: continue
  jobs.append({'job_id':f"rendered:{p['clip_id']}",'clip_id':p['clip_id'],'candidate_id':p['candidate_id'],'source_creator':p['source_creator'],'output':str(output),'status':'rendered','idempotency_key':f"rendered:{p['clip_id']}"})
 OUT.write_text(json.dumps({'schema_version':1,'jobs':jobs},ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(f'Render authorized v2: {len(jobs)} clips rendered')

if __name__=='__main__': main()
