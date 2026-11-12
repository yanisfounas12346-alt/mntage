from __future__ import annotations
import asyncio
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import edge_tts
from PIL import Image, ImageOps

OUT = Path("outputs")
OUT.mkdir(exist_ok=True)


def slugify(value: str) -> str:
    return (re.sub(r"[^a-z0-9_-]+", "-", value.lower().strip())[:60].strip("-") or "video")


def require_ffmpeg() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("Installe FFmpeg et ajoute ffmpeg/ffprobe au PATH.")


def duration_seconds(audio: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


async def synthesize(script: str, destination: Path, voice: str) -> None:
    await edge_tts.Communicate(script, voice=voice).save(str(destination))


def make_video(title: str, script: str, image_bytes: list[bytes],
               voice: str = "fr-FR-DeniseNeural") -> Path:
    require_ffmpeg()
    if not script.strip():
        raise ValueError("Le script ne peut pas être vide.")
    if not image_bytes:
        raise ValueError("Ajoute au moins une image.")
    name = slugify(title)
    output = OUT / f"{name}.mp4"
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        audio = work / "voice.mp3"
        asyncio.run(synthesize(script.strip(), audio, voice))
        duration = duration_seconds(audio)
        per_image = max(1.0, duration / len(image_bytes))
        clips = []
        for idx, data in enumerate(image_bytes):
            from io import BytesIO
            with Image.open(BytesIO(data)) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                im = ImageOps.fit(im, (1080, 1920), method=Image.Resampling.LANCZOS)
                img = work / f"image_{idx:03d}.jpg"
                im.save(img, quality=90)
            clip = work / f"clip_{idx:03d}.mp4"
            frames = int(per_image * 25) + 2
            # Modest animated zoom, generated on CPU by FFmpeg.
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(img),
                "-vf", f"scale=540:960,zoompan=z='min(zoom+0.0004,1.06)':d={frames}:s=540x960:fps=25,scale=1080:1920,format=yuv420p",
                "-frames:v", str(frames), "-c:v", "libx264", "-preset", "ultrafast",
                "-crf", "26", str(clip)
            ], check=True)
            clips.append(clip)
        concat = work / "clips.txt"
        concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips), encoding="utf-8")
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
            "-i", str(concat), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
            "-t", str(duration), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", str(output)
        ], check=True)
    return output
