"""Create clean, original motion-ready backgrounds without duplicating narration text."""
from __future__ import annotations
import hashlib
import math
import re
from io import BytesIO
from PIL import Image, ImageDraw, ImageFilter

def script_to_images(script: str, title: str, max_cards: int = 12) -> list[bytes]:
    parts=[p.strip() for p in re.split(r"\n\s*\n|(?<=[.!?])\s+(?=[A-ZÀ-Ý])",script) if p.strip()]
    if not parts: raise ValueError("Le script est vide.")
    count=min(max_cards,max(1,len(parts)))
    images=[]
    for i in range(count):
        phrase=parts[min(len(parts)-1,i*len(parts)//count)]
        seed=int.from_bytes(hashlib.sha256((title+phrase+str(i)).encode()).digest()[:8],"big")
        im=Image.new("RGB",(540,960))
        px=im.load()
        for y in range(960):
            for x in range(540):
                glow=max(0,1-math.hypot(x-(120+(seed%300)),y-(290+(seed%220)))/620)
                px[x,y]=(int(12+24*glow),int(12+8*glow),int(25+22*glow))
        layer=Image.new("RGBA",im.size,(0,0,0,0))
        d=ImageDraw.Draw(layer)
        for j in range(5):
            cx=(seed//(j+3)+j*151)%700-80
            cy=(seed//(j+5)+j*211)%900+30
            radius=90+(seed//(j+7))%170
            col=(235,39+(j*15),79+(j*10),65 if j%2 else 38)
            d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill=col)
        layer=layer.filter(ImageFilter.GaussianBlur(62))
        im=Image.alpha_composite(im.convert("RGBA"),layer)
        d=ImageDraw.Draw(im)
        for j in range(3):
            cx=100+(seed//(j+8))%340
            cy=260+(seed//(j+13))%440
            r=75+j*42
            d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=(240,100,122,95),width=2)
        # Bottom area intentionally clear for captions; no script text on backgrounds.
        output=BytesIO()
        im.convert("RGB").save(output,format="JPEG",quality=88)
        images.append(output.getvalue())
    return images
