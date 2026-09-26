import argparse, array, json, math, subprocess, sys, tempfile, wave
from pathlib import Path

def pct(v,p):
    if not v:return 0.0
    v=sorted(v); x=(len(v)-1)*p; a=int(x); b=min(a+1,len(v)-1); return v[a]*(1-x+a)+v[b]*(x-a)

def db(samples,peak=False):
    if not samples:return -100.0
    value=(max(abs(x) for x in samples) if peak else math.sqrt(sum(x*x for x in samples)/len(samples)))/32768.0
    return 20*math.log10(max(value,1e-8))

def zcr(s):
    return sum(1 for a,b in zip(s,s[1:]) if (a<0<=b) or (a>=0>b))/max(1,len(s))

def main():
    p=argparse.ArgumentParser();p.add_argument("--input",required=True);p.add_argument("--output",required=True);p.add_argument("--window",type=float,default=.25);p.add_argument("--hop",type=float,default=.10);a=p.parse_args()
    src=Path(a.input)
    with tempfile.TemporaryDirectory() as td:
        wav=Path(td)/"a.wav"
        r=subprocess.run(["ffmpeg","-v","error","-y","-i",str(src),"-vn","-ac","1","-ar","16000","-sample_fmt","s16",str(wav)],check=False)
        if r.returncode: raise SystemExit("ffmpeg audio decode failed")
        with wave.open(str(wav),"rb") as w:
            rate=w.getframerate(); raw=w.readframes(w.getnframes())
    s=array.array("h");s.frombytes(raw)
    if sys.byteorder!="little":s.byteswap()
    frame=max(1,int(rate*a.window));hop=max(1,int(rate*a.hop)); rows=[]
    for i in range(0,max(0,len(s)-frame+1),hop):
        c=s[i:i+frame];rows.append((i/rate,(i+len(c))/rate,db(c),db(c,True),zcr(c)))
    vals=[x[2] for x in rows];base=pct(vals,.50); loud=max(-20,pct(vals,.85),base+9); events=[];cur=None
    def close(cur):
        if not cur or cur["end"]-cur["start"]<.20:return None
        return {"event_id":f'scream:{int(cur["start"]*1000)}',"start":round(max(0,cur["start"]-.35),3),"end":round(cur["end"]+.85,3),"duration_seconds":round(cur["end"]-cur["start"],3),"score":round(min(100,sum(cur["scores"])/len(cur["scores"])),1),"peak_db":round(max(cur["peaks"]),1),"avg_rms_db":round(sum(cur["rms"])/len(cur["rms"]),1),"detector":"energy+peak+zcr"}
    for st,en,rms,peak,zc in rows:
        rel=rms-base;score=(55 if rms>=loud else 35 if rel>=7 else 0)+(20 if rel>=14 else 0)+(15 if peak>=-2 else 0)+(10 if zc>=.035 else 0)+(5 if zc>=.08 else 0)
        if score>=55:
            if cur is None:cur={"start":st,"end":en,"scores":[],"rms":[],"peaks":[]}
            cur["end"]=en;cur["scores"].append(score);cur["rms"].append(rms);cur["peaks"].append(peak)
        else:
            e=close(cur)
            if e:events.append(e)
            cur=None
    e=close(cur)
    if e:events.append(e)
    merged=[]
    for e in events:
        if merged and e["start"]<=merged[-1]["end"]+.5:
            m=merged[-1];m["end"]=max(m["end"],e["end"]);m["score"]=max(m["score"],e["score"]);m["peak_db"]=max(m["peak_db"],e["peak_db"]);m["duration_seconds"]=round(m["end"]-m["start"],3)
        else:merged.append(e)
    Path(a.output).write_text(json.dumps({"schema_version":1,"source":str(src),"baseline_rms_db":round(base,1),"loud_threshold_db":round(loud,1),"events":merged},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Scream detector: {len(merged)} scream-like events")

if __name__=="__main__":main()
