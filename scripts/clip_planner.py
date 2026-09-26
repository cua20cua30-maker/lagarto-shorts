import argparse
import json
from pathlib import Path

def main():
 p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--output',required=True); p.add_argument('--max-clips',type=int,default=10); args=p.parse_args()
 data=json.loads(Path(args.input).read_text(encoding='utf-8')); plans=[]
 for m in data.get('moments',[])[:args.max_clips]:
  start=max(0,float(m['start'])); duration=max(15,min(60,float(m['end'])-start))
  emotion=m.get('emotion_signals',[])
  labels={'sadness':'Un momento que toca la fibra','laughter':'Aquí se descontroló la cosa','fear':'La tensión empezó a subir','surprise':'Nadie esperaba lo que pasó','anger_conflict':'La conversación se calentó','joy_triumph':'El momento de la celebración','scream_or_volume_spike':'La reacción lo cambió todo','rapid_speech':'Todo empezó a ir demasiado rápido'}
  context=next((labels[x] for x in emotion if x in labels),'El momento clave de la historia')
  plans.append({'clip_id':f"clip:{m['moment_id']}",'moment_id':m['moment_id'],'start':round(start,3),'duration':round(duration,3),'hook':m.get('hook_text',''),'original_context':context,'signals':m.get('signals',[]),'emotion_signals':emotion,'emotion_score':m.get('emotion_score',0),'emotion_detected':m.get('emotion_detected',False),'edit_recipe':{'format':'9:16','remove_dead_air':True,'captions':True,'caption_style':'high_readability','hook_first':True,'payoff_before_end':True,'original_context_or_commentary_required':True},'status':'planned'})
 Path(args.output).write_text(json.dumps({'schema_version':1,'plans':plans},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'Clip planner: {len(plans)} clips planned')

if __name__=='__main__': main()
