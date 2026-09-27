import argparse, json, math, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
CFG=ROOT/"config/character_appearances.json"

def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def font(size,bold=False):
    candidates=["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in candidates:
        if Path(p).exists(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def draw_character(d, cx, cy, scale, spec, emotion):
    lw=max(3,int(7*scale)); head_w=int(250*scale); head_h=int(290*scale)
    # body
    shoulder_y=cy+head_h//2+70
    hip_y=shoulder_y+250*scale
    d.line((cx,shoulder_y,cx,hip_y),fill=(35,32,28),width=lw)
    sway=math.sin(cy*0.001)*18*scale
    arm=180*scale
    leg=220*scale
    d.line((cx,shoulder_y,cx-arm,shoulder_y+110*scale),fill=(35,32,28),width=lw)
    d.line((cx,shoulder_y,cx+arm,shoulder_y+110*scale),fill=(35,32,28),width=lw)
    d.line((cx,hip_y,cx-110*scale,hip_y+leg),fill=(35,32,28),width=lw)
    d.line((cx,hip_y,cx+110*scale,hip_y+leg),fill=(35,32,28),width=lw)
    # head
    box=(cx-head_w//2,cy-head_h//2,cx+head_w//2,cy+head_h//2)
    d.ellipse(box,fill=(247,239,220),outline=(35,32,28),width=lw)
    hair=spec.get("hair","dark_short")
    if "long" in hair:
        d.arc((box[0]-10,box[1]-25,box[2]+10,box[3]+30),180,360,fill=(35,32,28),width=int(35*scale))
        d.line((box[0]+25,box[1]+40,box[0]+5,box[3]-20),fill=(35,32,28),width=int(22*scale))
        d.line((box[2]-25,box[1]+40,box[2]-5,box[3]-20),fill=(35,32,28),width=int(22*scale))
    else:
        d.arc((box[0]-5,box[1]-45,box[2]+5,box[3]+5),180,360,fill=(35,32,28),width=int(38*scale))
    if spec.get("beard") in ("short","full"):
        d.arc((box[0]+45,box[1]+70,box[2]-45,box[3]+120),0,180,fill=(45,40,34),width=int(20*scale))
    # eyes and expression
    ex=52*scale; ey=-15*scale
    eye_r=11*scale
    mouth_y=cy+65*scale
    if emotion in ("sadness","pain_loss","emotional","sentimental","low_mood"):
        d.arc((cx-48*scale,mouth_y-5*scale,cx+48*scale,mouth_y+35*scale),180,350,fill=(35,32,28),width=lw)
        brow=20*scale
        d.line((cx-75*scale,cy-25*scale,cx-25*scale,cy-35*scale),fill=(35,32,28),width=lw)
        d.line((cx+25*scale,cy-35*scale,cx+75*scale,cy-25*scale),fill=(35,32,28),width=lw)
        d.ellipse((cx+ex,cy+ey+35*scale,cx+ex+4*scale,cy+ey+55*scale),outline=(50,70,110),width=max(2,lw//2))
    elif emotion in ("anger","anger_conflict"):
        d.arc((cx-45*scale,mouth_y-15*scale,cx+45*scale,mouth_y+45*scale),20,160,fill=(35,32,28),width=lw)
        d.line((cx-75*scale,cy-35*scale,cx-25*scale,cy-15*scale),fill=(35,32,28),width=lw)
        d.line((cx+25*scale,cy-15*scale,cx+75*scale,cy-35*scale),fill=(35,32,28),width=lw)
    elif emotion in ("fear","surprise","scream"):
        d.ellipse((cx-75*scale,cy-35*scale,cx-35*scale,cy+15*scale),outline=(35,32,28),width=lw)
        d.ellipse((cx+35*scale,cy-35*scale,cx+75*scale,cy+15*scale),outline=(35,32,28),width=lw)
        d.ellipse((cx-28*scale,mouth_y-5*scale,cx+28*scale,mouth_y+75*scale),outline=(35,32,28),width=lw)
    else:
        d.ellipse((cx-70*scale,cy-30*scale,cx-35*scale,cy+5*scale),fill=(35,32,28))
        d.ellipse((cx+35*scale,cy-30*scale,cx+70*scale,cy+5*scale),fill=(35,32,28))
        d.arc((cx-45*scale,mouth_y-20*scale,cx+45*scale,mouth_y+45*scale),10,170,fill=(35,32,28),width=lw)
    acc=spec.get("accessory")
    if acc=="glasses":
        d.ellipse((cx-105*scale,cy-55*scale,cx-5*scale,cy+25*scale),outline=(35,32,28),width=lw)
        d.ellipse((cx+5*scale,cy-55*scale,cx+105*scale,cy+25*scale),outline=(35,32,28),width=lw)
        d.line((cx-5*scale,cy-15*scale,cx+5*scale,cy-15*scale),fill=(35,32,28),width=lw)
    elif acc=="cap":
        d.arc((cx-145*scale,cy-head_h//2-25*scale,cx+145*scale,cy-head_h//2+95*scale),180,360,fill=(35,32,28),width=int(20*scale))
        d.line((cx-150*scale,cy-head_h//2+35*scale,cx+30*scale,cy-head_h//2+20*scale),fill=(35,32,28),width=int(15*scale))

def transcript_lines(plan):
    p=plan.get("transcript_path")
    if not p or not Path(p).exists(): return []
    try: data=load(p)
    except Exception: return []
    start=float(plan.get("start",0)); end=start+float(plan.get("duration",0)); out=[]
    for seg in data.get("segments",[]):
        a=float(seg.get("start",0)); b=float(seg.get("end",a)); text=str(seg.get("text","")).strip()
        if text and b>start and a<end: out.append((max(0,a-start),min(float(plan.get("duration",0)),b-start),text))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--plan",required=True); ap.add_argument("--audio",required=True); ap.add_argument("--output",required=True)
    args=ap.parse_args()
    plan=load(args.plan); cfg=load(CFG)
    w,h=cfg["style"]["canvas"]; fps=cfg["style"]["fps"]; duration=float(plan["duration"])
    creator=str(plan.get("source_creator","")).strip()
    cid=str(plan.get("character_id") or creator.lower().replace(" ","_"))
    spec=cfg["characters"].get(cid,{})
    signals=plan.get("emotion_signals",[])
    captions=transcript_lines(plan)
    emotion=signals[0] if signals else "neutral"
    ff=subprocess.Popen(["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{w}x{h}","-r",str(fps),"-i","-","-ss",str(float(plan.get("start",0))),"-i",args.audio,"-t",str(duration),"-map","0:v:0","-map","1:a:0?","-c:v","libx264","-preset","veryfast","-crf","23","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",args.output],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        total=int(duration*fps)
        for i in range(total):
            t=i/fps
            im=Image.new("RGB",(w,h),(244,238,222)); d=ImageDraw.Draw(im)
            # paper-like sketch lines
            for y in range(0,h,140): d.line((0,y,w,y),fill=(226,216,195),width=1)
            bob=math.sin(t*5.0)*10
            cx=w//2; cy=650+int(bob)
            draw_character(d,cx,cy,1.0,spec,emotion)
            label=creator.upper()
            f=font(54,True); tw=d.textbbox((0,0),label,font=f)[2]
            d.text(((w-tw)//2,170),label,fill=(35,32,28),font=f)
            if plan.get("original_context"):
                cf=font(38); txt=str(plan["original_context"])[:70]
                d.text((70,1540),txt,fill=(45,40,34),font=cf)
            current=""
            for ca,cb,ct in captions:
                if ca <= t <= cb:
                    current=ct[:82]
                    break
            if current:
                cf=font(44,True); bbox=d.textbbox((0,0),current,font=cf); tw=bbox[2]-bbox[0]; x=(w-tw)//2
                d.rounded_rectangle((x-28,1660,x+tw+28,1745),radius=18,fill=(250,245,231),outline=(55,48,40),width=3)
                d.text((x,1675),current,fill=(35,32,28),font=cf)
            # dynamic motion / impact marks
            if emotion in ("fear","surprise","scream"):
                for k in range(8):
                    ang=k*math.pi/4; x=cx+int(math.cos(ang)*(260+40*math.sin(t*8))); y=cy+int(math.sin(ang)*(260+40*math.sin(t*8)))
                    d.line((cx+int(math.cos(ang)*180),cy+int(math.sin(ang)*180),x,y),fill=(65,55,45),width=6)
            im.tobytes()
            ff.stdin.write(im.tobytes())
    finally:
        ff.stdin.close()
    err=ff.stderr.read().decode("utf-8","ignore"); code=ff.wait()
    if code: print(err[-3000:],file=sys.stderr); raise SystemExit(code)
if __name__=="__main__": main()
