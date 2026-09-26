import argparse,json,re
from pathlib import Path
SIGNALS={'shock':('increíble','increible','brutal','locura','madre mía','dios mío'),'conflict':('polémica','polemica','humilla','humilló','explota','se lía','se lia'),'reveal':('resulta que','nadie sabía','nadie esperaba','al final','descubrimos'),'reaction':('qué coño','que coño','no puede ser','wtf')}
def score(text):
 t=re.sub(r'\s+',' ',(text or '').lower().strip());n=0;labels=[]
 for label,terms in SIGNALS.items():
  hits=sum(term in t for term in terms)
  if hits:n+=min(25,hits*10);labels.append(label)
 if '?' in t:n+=8;labels.append('question')
 if '!' in t:n+=5;labels.append('exclamation')
 return min(100,n),labels
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--screams');p.add_argument('--emotions');a=p.parse_args()
 data=json.loads(Path(a.input).read_text(encoding='utf-8'));segs=data.get('segments',[]);screams=[];emotions=[]
 if a.screams and Path(a.screams).exists():screams=json.loads(Path(a.screams).read_text(encoding='utf-8')).get('events',[])
 if a.emotions and Path(a.emotions).exists():emotions=json.loads(Path(a.emotions).read_text(encoding='utf-8')).get('events',[])
 events=screams+emotions
 moments=[]
 for i,s in enumerate(segs):
  st=float(s['start']);en=float(s['end']);context=[x for x in segs if float(x['end'])>=st-8 and float(x['start'])<=en+27];txt=' '.join(x.get('text','') for x in context);sc,labels=score(txt);near=[e for e in events if e['end']>=st-5 and e['start']<=en+10]
  if near:
   strong=max(near,key=lambda e:e.get('score',0));sc=min(100,sc+min(45,int(strong.get('score',0)*.45)));labels.append('scream');ss=min(e['start'] for e in near);ee=max(e['end'] for e in near)
  else:ss=ee=None
  if sc>=18:
   start=max(0,st-2.5);end=max(en+8,st+15)
   if ss is not None:start=min(start,max(0,ss-1));end=max(end,ee+2)
   moments.append({'moment_id':f'moment:{i}:{int(st*1000)}','start':round(start,3),'end':round(end,3),'score':sc,'signals':sorted(set(labels)),'scream_detected':any('scream' in ' '.join(e.get('signals',[])) or 'scream_or_volume_spike' in ' '.join(e.get('signals',[])) for e in near),'scream_score':round(max((e.get('score',0) for e in near if 'scream' in ' '.join(e.get('signals',[])) or 'scream_or_volume_spike' in ' '.join(e.get('signals',[]))),default=0),1),'emotion_detected':bool(near),'emotion_score':round(max((e.get('score',0) for e in near),default=0),1),'emotion_signals':sorted(set(x for e in near for x in e.get('signals',[]))),'hook_text':s.get('text','').strip(),'context_text':txt.strip()})
 moments.sort(key=lambda x:x['score'],reverse=True);selected=[]
 for m in moments:
  if all(abs(m['start']-x['start'])>12 for x in selected):selected.append(m)
  if len(selected)>=20:break
 Path(a.output).write_text(json.dumps({'schema_version':3,'source':data.get('source'),'moments':selected},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(f'Moment detector: {len(selected)} moments selected')
if __name__=='__main__':main()
