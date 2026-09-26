import json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; CANDIDATES=ROOT/'data'/'candidates.json'; AUTH=ROOT/'data'/'authorization_manifest.json'; STRATEGIES=ROOT/'data'/'edit_strategies.json'; RQ=ROOT/'data'/'render_queue.json'; PQ=ROOT/'data'/'publish_queue.json'
def load(p,d): return json.loads(p.read_text(encoding='utf-8')) if p.exists() else d
def main():
 candidates=load(CANDIDATES,{'candidates':[]}).get('candidates',[]); allowed=set(load(AUTH,{'authorized_sources':[]}).get('authorized_sources',[])); strategies={x['candidate_id']:x for x in load(STRATEGIES,{'strategies':[]}).get('strategies',[]).get('strategies',[]) }
 # Accept only explicit URLs in the authorization manifest.
 render=[]; publish=[]
 for c in candidates:
  if c.get('source_url') not in allowed: continue
  s=strategies.get(c.get('candidate_id')); 
  if not s: continue
  render.append({'job_id':f"render:{c['candidate_id']}",'candidate_id':c['candidate_id'],'source_url':c['source_url'],'source_creator':c['source_creator'],'title':c.get('title'),'strategy':s,'status':'queued','idempotency_key':f"short:{c['candidate_id']}"})
  publish.append({'job_id':f"publish:{c['candidate_id']}",'candidate_id':c['candidate_id'],'status':'blocked_until_rendered','authorization_status':'authorized','transformative_edit_required':True,'idempotency_key':f"publish:{c['candidate_id']}"})
 now=datetime.now(timezone.utc).isoformat(); RQ.write_text(json.dumps({'schema_version':1,'generated_at':now,'jobs':render},ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); PQ.write_text(json.dumps({'schema_version':1,'generated_at':now,'jobs':publish},ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(f'Factory v2: authorized render={len(render)} publish={len(publish)}')
if __name__=='__main__': main()
