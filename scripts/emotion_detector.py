import argparse,json,math,re,subprocess,tempfile,wave,array,sys
from pathlib import Path

LEXICONS={
"laughter":("jajaja","jajaj","jejeje","jiji","risas","se ríe","se rie","risa"),
"sadness":("triste","tristísimo","tristisimo","llorar","llorando","lloró","lloro","lágrimas","lagrimas","pena","dolor","perdí","perdi","murió","murio","muerte","te quiero","te echo de menos","echo de menos","lo siento","me duele"),
"fear":("miedo","asusta","susto","terror","temor","qué miedo","que miedo","no mires","cuidado"),
"surprise":("increíble","increible","no puede ser","wow","wtf","dios mío","dios mio","madre mía","madre mia","resulta que","nadie esperaba"),
"anger_conflict":("enfadado","enojado","cabreado","cabreé","cabree","rabia","hijo de","imbécil","imbecil","gilipollas","qué coño","que coño","cállate","callate"),
"joy_triumph":("brutal","épico","epico","victoria","ganamos","gané","gane","felicidades","feliz","grande","lo conseguimos")
}
BASE_SCORES={"laughter":55,"sadness":70,"fear":65,"surprise":60,"anger_conflict":65,"joy_triumph":50}

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

def hits(text,terms):
    t=(text or "").lower()
    return sum(1 for term in terms if term in t)

def local_text(segs,st,en):
    return " ".join(x.get("text","") for x in segs if float(x.get("end",0))>=st-4 and float(x.get("start",0))<=en+5).strip()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True);p.add_argument("--transcript",required=True);p.add_argument("--output",required=True)
    a=p.parse_args()
    transcript=json.loads(Path(a.transcript).read_text(encoding="utf-8"));segs=transcript.get("segments",[])
    src=Path(a.input)
    with tempfile.TemporaryDirectory() as td:
        wav=Path(td)/"a.wav"
        if subprocess.run(["ffmpeg","-v","error","-y","-i",str(src),"-vn","-ac","1","-ar","16000","-sample_fmt","s16",str(wav)],check=False).returncode:
            raise SystemExit("ffmpeg audio decode failed")
        with wave.open(str(wav),"rb") as w:
            rate=w.getframerate();raw=w.readframes(w.getnframes())
    samples=array.array("h");samples.frombytes(raw)
    if sys.byteorder!="little":samples.byteswap()
    frame=max(1,int(rate*.25));hop=max(1,int(rate*.10));rows=[]
    for i in range(0,max(0,len(samples)-frame+1),hop):
        chunk=samples[i:i+frame]
        rows.append((i/rate,(i+len(chunk))/rate,db(chunk),db(chunk,True),zcr(chunk)))
    rms_values=[r[2] for r in rows];base=pct(rms_values,.50);loud=max(-20,pct(rms_values,.85),base+8)
    raw_events=[];previous_rms=base
    for st,en,rms,peak,zc in rows:
        rel=rms-base;delta=rms-previous_rms
        audio_score=(45 if rms>=loud else 25 if rel>=6 else 0)+(20 if rel>=12 else 0)+(15 if peak>=-2 else 0)+(10 if zc>=.035 else 0)+(10 if delta>=8 else 0)
        if audio_score>=55:
            raw_events.append((st,en,min(100,audio_score),"scream_or_volume_spike"))
        previous_rms=rms
    audio_events=[]
    for st,en,score,signal in raw_events:
        if audio_events and st<=audio_events[-1]["end"]+.4:
            audio_events[-1]["end"]=en;audio_events[-1]["score"]=max(audio_events[-1]["score"],score)
        else:
            audio_events.append({"start":st,"end":en,"score":score,"signals":[signal]})
    events=[]
    for e in audio_events:
        text=local_text(segs,e["start"],e["end"]);signals=list(e["signals"]);scores=[e["score"]]
        for name,terms in LEXICONS.items():
            if hits(text,terms):signals.append(name);scores.append(BASE_SCORES[name])
        words=re.findall(r"\b[\wáéíóúüñ']+\b",text,re.I)
        if len(words)>=12:
            wpm=len(words)/max(.5,e["end"]-e["start"])*60
            if wpm>=210:signals.append("rapid_speech");scores.append(55)
        score=min(100,max(scores)+min(20,max(0,(len(set(signals))-1)*7)))
        events.append({"event_id":f"emotion:{int(e['start']*1000)}","start":round(max(0,e["start"]-1.5),3),"end":round(e["end"]+7,3),"score":round(score,1),"signals":sorted(set(signals)),"audio_score":round(e["score"],1),"text":text,"detector":"audio+transcript"})
    for seg in segs:
        st=float(seg.get("start",0));en=float(seg.get("end",st));text=local_text(segs,st,en)
        signals=[];scores=[]
        for name,terms in LEXICONS.items():
            if hits(text,terms):signals.append(name);scores.append(BASE_SCORES[name])
        if not signals:continue
        if any(float(x.get("end",0))<=st and st-float(x.get("end",0))>=1.2 for x in segs):
            signals.append("silence_to_emotion");scores.append(60)
        score=min(100,max(scores)+min(20,max(0,(len(set(signals))-1)*7)))
        if score>=55:
            events.append({"event_id":f"emotion:text:{int(st*1000)}","start":round(max(0,st-2),3),"end":round(en+7,3),"score":round(score,1),"signals":sorted(set(signals)),"audio_score":0,"text":text,"detector":"transcript"})
    merged=[]
    for e in sorted(events,key=lambda x:x["start"]):
        if merged and e["start"]<=merged[-1]["end"]+.75:
            m=merged[-1];m["end"]=max(m["end"],e["end"]);m["score"]=max(m["score"],e["score"]);m["signals"]=sorted(set(m["signals"]+e["signals"]));m["audio_score"]=max(m["audio_score"],e["audio_score"]);m["text"]=(m["text"]+" "+e["text"]).strip()
        else:merged.append(e)
    Path(a.output).write_text(json.dumps({"schema_version":1,"source":str(src),"events":merged},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Emotion detector: {len(merged)} emotional events")

if __name__=="__main__":main()
