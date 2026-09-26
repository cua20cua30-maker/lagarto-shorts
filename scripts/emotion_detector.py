import argparse,json,math,re,subprocess,tempfile,wave,array
from pathlib import Path

LAUGHTER=("jajaja","jajaj","jejeje","jiji","risas","se ríe","se rie","risa")
SADNESS=("triste","tristísimo","tristisimo","llorar","llorando","lloró","lloro","lágrimas","lagrimas","pena","dolor","perdí","perdi","perder","murió","murio","muerte","te quiero","te echo de menos","echo de menos","lo siento")
FEAR=("miedo","asusta","susto","terror","temor","qué miedo","que miedo","no mires","cuidado")
SURPRISE=("increíble","increible","no puede ser","qué","que","wow","wtf","dios mío","dios mio","madre mía","madre mia","resulta que","nadie esperaba")
ANGER=("enfadado","enojado","cabreado","cabreé","cabree","rabia","hijo de","imbécil","imbecil","gilipollas","qué coño","que coño","cállate","callate")
POSITIVE=("brutal","épico","epico","increíble","increible","victoria","ganamos","gané","gane","felicidades","feliz","grande")
SILENCE_GAP=1.2

def pct(v,p):
    if not v:return -100.0
    v=sorted(v);x=(len(v)-1)*p;a=int(x);b=min(a+1,len(v)-1)
    return v[a]*(1-x+a)+v[b]*(x-a)

def db(samples,peak=False):
    if not samples:return -100.0
    value=(max(abs(x) for x in samples) if peak else math.sqrt(sum(x*x for x in samples)/len(samples)))/32768.0
    return 20*math.log10(max(value,1e-8))

def zcr(s):
    return sum(1 for a,b in zip(s,s[1:]) if (a<0<=b) or (a>=0>b))/max(1,len(s))

def text_hits(text,terms):
    t=(text or "").lower()
    return sum(1 for term in terms if term in t)

def main():
    p=argparse.ArgumentParser();p.add_argument("--input",required=True);p.add_argument("--transcript",required=True);p.add_argument("--output",required=True)
    a=p.parse_args()
    data=json.loads(Path(a.transcript).read_text(encoding="utf-8"));segs=data.get("segments",[])
    src=Path(a.input);events=[]
    with tempfile.TemporaryDirectory() as td:
        wav=Path(td)/"a.wav"
        r=subprocess.run(["ffmpeg","-v","error","-y","-i",str(src),"-vn","-ac","1","-ar","16000","-sample_fmt","s16",str(wav)],check=False)
        if r.returncode:raise SystemExit("ffmpeg audio decode failed")
        with wave.open(str(wav),"rb") as w:
            rate=w.getframerate();raw=w.readframes(w.getnframes())
    samples=array.array("h");samples.frombytes(raw)
    if __import__("sys").byteorder!="little":samples.byteswap()
    frame=int(rate*.25);hop=int(rate*.10);rows=[]
    for i in range(0,max(0,len(samples)-frame+1),hop):
        c=samples[i:i+frame];rows.append((i/rate,(i+len(c))/rate,db(c),db(c,True),zcr(c)))
    vals=[r[2] for r in rows];base=pct(vals,.50);loud=max(-20,pct(vals,.85),base+8)
    audio=[]
    for st,en,rms,peak,zc in rows:
        rel=rms-base;spike=max(0,rms-(rows[max(0,rows.index((st,en,rms,peak,zc))-5)][2] if rows else base))
        score=(45 if rms>=loud else 25 if rel>=6 else 0)+(20 if rel>=12 else 0)+(15 if peak>=-2 else 0)+(10 if zc>=.035 else 0)
        audio.append((st,en,score,rms,peak,spike))
    def local_text(st,en):
        return " ".join(x.get("text","") for x in segs if float(x.get("end",0))>=st-4 and float(x.get("start",0))<=en+5).strip()
    for i,(st,en,asc,rms,peak,spike) in enumerate(audio):
        txt=local_text(st,en);low=txt.lower()
        words=re.findall(r"\b[\wáéíóúüñ']+\b",txt,re.I)
        signals=[];scores=[]
        if asc>=55:signals.append("scream_or_volume_spike");scores.append(min(100,asc))
        if text_hits(low,LAUGHTER):signals.append("laughter");scores.append(55)
        if text_hits(low,SADNESS):signals.append("sadness");scores.append(70)
        if text_hits(low,FEAR):signals.append("fear");scores.append(65)
        if text_hits(low,SURPRISE):signals.append("surprise");scores.append(60)
        if text_hits(low,ANGER):signals.append("anger_conflict");scores.append(65)
        if text_hits(low,POSITIVE):signals.append("joy_triumph");scores.append(50)
        if len(words)>=10:
            duration=max(.5,en-st);wpm=len(words)/duration*60
            if wpm>=210:signals.append("rapid_speech");scores.append(55)
        prev_end=float(segs[i-1].get("end",0)) if i<len(segs) and i>0 else 0
        silence=max(0,st-prev_end)
        if silence>=SILENCE_GAP and asc>=35:signals.append("silence_to_event");scores.append(60)
        if not signals:continue
        combo=min(20,max(0,(len(set(signals))-1)*7))
        score=min(100,max(scores)+combo)
        if score<45:continue
        start=max(0,st-1.5);end=en+7
        events.append({"event_id":f"emotion:{int(st*1000)}","start":round(start,3),"end":round(end,3),"score":round(score,1),"signals":sorted(set(signals)),"audio_score":round(asc,1),"text":txt,"detector":"audio+transcript"})
    merged=[]
    for e in sorted(events,key=lambda x:x["start"]):
        if merged and e["start"]<=merged[-1]["end"]+.75:
            m=merged[-1];m["end"]=max(m["end"],e["end"]);m["score"]=max(m["score"],e["score"]);m["signals"]=sorted(set(m["signals"]+e["signals"]));m["audio_score"]=max(m["audio_score"],e["audio_score"]);m["text"]=(m["text"]+" "+e["text"]).strip()
        else:merged.append(e)
    Path(a.output).write_text(json.dumps({"schema_version":1,"source":str(src),"events":merged},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Emotion detector: {len(merged)} emotional events")
if __name__=="__main__":main()
