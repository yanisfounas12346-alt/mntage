"""Create timed SRT captions from script; timing is approximate, not word-aligned."""
import re
from pathlib import Path

def _stamp(seconds):
    ms = max(0, round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def write_srt(script: str, duration: float, path: Path) -> Path:
    words = script.split()
    if not words or duration <= 0:
        raise ValueError("Script ou durée invalide")
    chunks = [" ".join(words[i:i+7]) for i in range(0, len(words), 7)]
    total = sum(len(c) for c in chunks)
    start = 0.0
    blocks = []
    for index, chunk in enumerate(chunks):
        end = duration if index == len(chunks)-1 else start + duration * len(chunk)/total
        blocks.append(f"{index+1}\n{_stamp(start)} --> {_stamp(end)}\n{chunk}\n")
        start = end
    path.write_text("\n".join(blocks), encoding="utf-8")
    return path
