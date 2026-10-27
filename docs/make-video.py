#!/usr/bin/env python3
# Builds docs/images/every-turn-resends-history.mp4 (1080x1080, 13.5 s) and a 540 px GIF of it.
# One idea: every turn re-sends the whole conversation. The only numbers are the totals of one answer from an
# earlier round on private repositories: 7 turns and 267k billed input tokens without a 12,000-character cap on
# tool output, 18 turns and 708k with it. Per-turn counts were not recorded, so each block is the average turn.
# Usage: python3 docs/make-video.py [--out-dir DIR] [--frames-only 3]   (needs Pillow, matplotlib and ffmpeg)
import argparse, math, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from matplotlib import font_manager

W=H=1080; FPS=30; DURATION=13.5
BG=(2,3,10); PRIMARY=(237,238,243); SECONDARY=(163,167,183); TRACK=(17,19,28)
ORANGE=(242,113,60); GRAY=(123,129,148)
def font(size,bold=False):
    props=font_manager.FontProperties(family=["Helvetica Neue","Helvetica","Arial","DejaVu Sans"], weight="bold" if bold else "normal")
    path=font_manager.findfont(props, fallback_to_default=True)
    if not path.lower().endswith(".ttc"): return ImageFont.truetype(path,size)
    # A .ttc holds several faces; take the one whose style matches.
    want="Bold" if bold else "Regular"
    for i in range(16):
        try: f=ImageFont.truetype(path,size,index=i)
        except OSError: break
        if f.getname()[1]==want: return f
    return ImageFont.truetype(path,size)
F64=font(64,True); F56B=font(52,True); F42=font(42); F42B=font(42,True); F36=font(36); F26=font(26)
def ease(x): return 1-(1-max(0,min(1,x)))**3
def fade(t,start,length=.4): return ease((t-start)/length)
def blend(c,amount): return tuple(round(v+(255-v)*amount) for v in c)
def text(draw, xy, s, f, color, anchor="la", alpha=1):
    color=tuple(round(BG[i]+(color[i]-BG[i])*alpha) for i in range(3)); draw.text(xy,s,font=f,fill=color,anchor=anchor)
def wrapped(draw, x, y, words, f, width, color, alpha=1, gap=8):
    lines=[]; line=""
    for word in words.split():
        trial=(line+" "+word).strip()
        if draw.textbbox((0,0),trial,font=f)[2] > width and line: lines.append(line); line=word
        else: line=trial
    lines.append(line)
    for i,line in enumerate(lines): text(draw,(x,y+i*(f.size+gap)),line,f,color,alpha=alpha)
def frame(t):
    im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im); top=fade(t,0)
    wrapped(d,80,60,"Every turn re-sends the whole conversation",F64,920,PRIMARY,top,6)
    wrapped(d,80,212,"system prompt, tool definitions, question and every tool result so far",F36,920,SECONDARY,top,5)
    track_x,track_w=80,920; tick_start=.0+1.5
    for row,(label,total,turns,color,y) in enumerate((("No cap",267000,7,GRAY,410),("12,000-character cap",708000,18,ORANGE,650))):
        text(d,(80,y-56),label,F42B,PRIMARY,alpha=top)
        d.rounded_rectangle((track_x,y,track_x+track_w,y+74),radius=8,fill=TRACK)
        # blocks appear at the shared ticks; row 1 stops after seven.
        count=min(turns, max(0, int(math.floor((t-tick_start)/.45))+1)) if t>=tick_start else 0
        if count == 0: state=""
        elif count < turns: state=f"turn {count}"
        else: state=f"{turns} turns · {fmt_tokens(total)} tokens"
        text(d,(1000,y-56),state,F42,PRIMARY,anchor="ra",alpha=top)
        unit=(track_w*(total/708000))/turns; gap=4
        # At every new turn the blocks already there light up: the history goes out again with the new request.
        last=tick_start+(count-1)*.45
        resend=max(0,1-(t-last)/.3) if count>1 and t<tick_start+turns*.45 else 0
        for i in range(count):
            begun=tick_start+i*.45; grow=ease((t-begun)/.25)
            c=blend(color,.38*resend) if i<count-1 else color
            x=track_x+i*unit; d.rounded_rectangle((x,y,x+(unit-gap)*grow,y+74),radius=5,fill=c)
    bottom=fade(t,10.2)
    text(d,(540,888),"2.65× the tokens for the same answer",F56B,PRIMARY,"ma",bottom)
    wrapped(d,80,958,"Each block is the average turn (267k ÷ 7, 708k ÷ 18). Billed input tokens, one answer, earlier round on private repositories.",F26,920,SECONDARY,bottom,5)
    return im
def fmt_tokens(n): return "708k" if n==708000 else "267k"
def main():
    p=argparse.ArgumentParser(); p.add_argument("--out-dir",default="docs/images"); p.add_argument("--frames-only",nargs="?",type=int,const=3)
    a=p.parse_args(); out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
    if a.frames_only is not None:
        for i,t in enumerate((1,6,12.5)[:min(3,a.frames_only)],1):
            path=out/f"every-turn-resends-history-frame-{i}.png"; frame(t).save(path); print(path)
        return
    ff=shutil.which("ffmpeg")
    if not ff: raise SystemExit("ffmpeg must be on PATH")
    mp4=out/"every-turn-resends-history.mp4"; gif=out/"every-turn-resends-history.gif"
    cmd=[ff,"-y","-f","rawvideo","-pix_fmt","rgb24","-s","1080x1080","-r","30","-i","-","-c:v","libx264","-pix_fmt","yuv420p","-crf","18","-threads","4","-movflags","+faststart",str(mp4)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    for i in range(405): proc.stdin.write(frame(i/FPS).tobytes())
    proc.stdin.close()
    if proc.wait(): raise SystemExit("ffmpeg video encode failed")
    filt="fps=15,scale=540:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=48:stats_mode=full[p];[b][p]paletteuse=dither=none"
    subprocess.run([ff,"-y","-threads","4","-i",str(mp4),"-vf",filt,str(gif)],check=True)
    print(mp4); print(gif)
if __name__ == "__main__": main()
