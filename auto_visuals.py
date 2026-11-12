"""Create original graphic cards automatically from a narration script."""
from __future__ import annotations
import re
import textwrap
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def _font(size: int):
    paths = [
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def script_to_images(script: str, title: str, max_cards: int = 12) -> list[bytes]:
    parts = [p.strip() for p in re.split(r"\n\s*\n|(?<=[.!?])\s+(?=[A-ZÀ-Ý])", script) if p.strip()]
    if not parts:
        raise ValueError("Le script est vide.")
    # Group into a bounded number of cards, avoiding extremely short scenes.
    size = max(1, (len(parts) + max_cards - 1) // max_cards)
    cards = [" ".join(parts[i:i + size]) for i in range(0, len(parts), size)]
    results = []
    for idx, body in enumerate(cards):
        image = Image.new("RGB", (1080, 1920))
        draw = ImageDraw.Draw(image)
        for y in range(1920):
            t = y / 1920
            draw.line((0, y, 1080, y), fill=(int(9+12*t), int(17+9*t), int(38+25*t)))
        draw.rounded_rectangle((70, 130, 1010, 240), radius=25, fill=(25, 85, 146))
        draw.text((100, 165), "IA LAB FR  /  VIDEO", font=_font(35), fill="white")
        draw.text((85, 330), title[:42], font=_font(46), fill=(105, 210, 255))
        lines = textwrap.wrap(body, width=27)
        if len(lines) > 12:
            lines = lines[:11] + ["…"]
        font = _font(58 if len(lines) < 7 else 45)
        line_h = 95 if len(lines) < 7 else 74
        start_y = max(540, 950 - (len(lines) * line_h)//2)
        for j, line in enumerate(lines):
            draw.text((90, start_y + j * line_h), line, font=font, fill="white")
        draw.text((90, 1780), f"SCENE {idx+1:02d} / {len(cards):02d}", font=_font(30), fill=(160, 180, 210))
        stream = BytesIO()
        image.save(stream, format="JPEG", quality=88)
        results.append(stream.getvalue())
    return results
