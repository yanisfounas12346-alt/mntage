"""Caption exports: short readable SRT and precisely styled ASS (estimated timings)."""
from pathlib import Path

def _stamp(seconds, ass=False):
    ms=max(0,round(seconds*1000))
    h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f"{h}:{m:02}:{s:02}.{ms//10:02}" if ass else f"{h:02}:{m:02}:{s:02},{ms:03}"

def _chunks(script, duration):
    words=script.split()
    if not words or duration<=0:raise ValueError("Script ou durée invalide")
    chunks=[" ".join(words[i:i+4]) for i in range(0,len(words),4)]
    weight=sum(len(c) for c in chunks)
    t=0.0
    for i,chunk in enumerate(chunks):
        end=duration if i==len(chunks)-1 else t+duration*len(chunk)/weight
        yield i+1,t,end,chunk
        t=end

def write_srt(script: str, duration: float, path: Path) -> Path:
    blocks=[f"{i}\n{_stamp(a)} --> {_stamp(b)}\n{txt}\n" for i,a,b,txt in _chunks(script,duration)]
    path.write_text("\n".join(blocks),encoding="utf-8")
    return path

def write_ass(script: str, duration: float, path: Path) -> Path:
    header="""[Script Info]
ScriptType: v4.00+
PlayResX: 540
PlayResY: 960
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial,31,&H00FFFFFF,&H000000FF,&H00130A0D,&H88000000,-1,0,0,0,100,100,0,0,1,3,1,2,40,40,155,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines=[]
    for _,a,b,txt in _chunks(script,duration):
        safe=txt.replace("{","(").replace("}",")").replace("\\","/")
        lines.append(f"Dialogue: 0,{_stamp(a,True)},{_stamp(b,True)},Caption,,0,0,0,,{safe}")
    path.write_text(header+"\n".join(lines)+"\n",encoding="utf-8-sig")
    return path
