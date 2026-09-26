import argparse
import json
import re
from pathlib import Path

SIGNALS={
 'shock':('increíble','increible','brutal','locura','madre mía','dios mío'),
 'conflict':('polémica','polemica','humilla','humilló','explota','se lía','se lia'),
 'reveal':('resulta que','nadie sabía','nadie esperaba','al final','descubrimos'),
 'reaction':('qué coño','que coño','no puede ser','wtf')}

def score(text):
 t=re.sub(r'\s+',' ',(text or '').lower().strip()); n=0; labels=[]
 for label,terms in SIGNALS.items():
  hits=sum(term in t for term in terms)
  if hits: n+=min(25,hits*10); labels.append(label)
 if '?' in t: n+=8; labels.append('question')
 if '!' in t: n+=5; labels.append('exclamation')
 return min(100,n),labels

def main():
 p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--output',required=True); args=p.parse_args()
 data=json.loads(Path(args.input).read_text(encoding='utf-8')); segs=data.get('segments',[]); moments=[]
 for i,s in enumerate(segs):
  st=float(s['start']); en=float(s['end']); context=[x for x in segs if float(x['end'])>=st-8 and float(x['start'])<=en+27]
  txt=' '.join(x.get('text','') for x in context); sc,labels=score(txt)
  if sc>=18: moments.append({'moment_id':f'moment:{i}:{int(st*1000)}','start':round(max(0,st-2.5),3),'end':round(max(en+8,st+15),3),'score':sc,'signals':sorted(set(labels)),'hook_text':s.get('text','').strip(),'context_text':txt.strip()})
 moments.sort(key=lambda x:x['score'],reverse=True); selected=[]
 for m in moments:
  if all(abs(m['start']-x['start'])>12 for x in selected): selected.append(m)
  if len(selected)>=20: break
 Path(args.output).write_text(json.dumps({'schema_version':1,'source':data.get('source'),'moments':selected},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'Moment detector: {len(selected)} moments selected')

if __name__=='__main__': main()
