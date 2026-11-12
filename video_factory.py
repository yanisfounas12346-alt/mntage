from __future__ import annotations
import asyncio
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from io import BytesIO
import edge_tts
from PIL import Image, ImageOps
from subtitles import write_srt, write_ass, write_timed_srt, write_timed_ass

OUT = Path("outputs").resolve()
OUT.mkdir(exist_ok=True)

def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", value.lower().strip())[:60].strip("-") or "video"

def require_ffmpeg():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg et ffprobe doivent être installés et présents dans le PATH.")

def duration_seconds(audio: Path) -> float:
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","default=noprint_wrappers=1:nokey=1",str(audio)],
                       capture_output=True,text=True,check=True)
    return float(r.stdout.strip())

async def synthesize(script: str, destination: Path, voice: str, rate: str = "-5%"):
    boundaries=[]
    with destination.open("wb") as audio:
        async for chunk in edge_tts.Communicate(script, voice=voice, rate=rate).stream():
            if chunk["type"]=="audio":
                audio.write(chunk["data"])
            elif chunk["type"]=="WordBoundary":
                boundaries.append({"offset":chunk["offset"],"duration":chunk["duration"],"text":chunk["text"]})
    if not destination.stat().st_size:
        raise RuntimeError("La synthèse vocale n'a produit aucun audio.")
    return boundaries

def _run(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("FFmpeg : " + result.stderr[-1400:])

def make_video(title: str, script: str, image_bytes: list[bytes],
               voice: str = "fr-FR-DeniseNeural",
               captions: bool = True, music: bytes | None = None,
               music_volume: float = 0.12, voice_rate: str = "-5%", video_bytes: list[bytes] | None = None) -> Path:
    require_ffmpeg()
    if not script.strip() or not (image_bytes or video_bytes):
        raise ValueError("Un script et au moins un visuel sont nécessaires.")
    if len(image_bytes) > 24 or len(video_bytes or []) > 24:
        raise ValueError("Maximum 24 images pour protéger les ressources du PC.")
    OUT.mkdir(exist_ok=True)
    output = OUT / f"{slugify(title)}.mp4"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        audio = work / "voice.mp3"
        boundaries = asyncio.run(synthesize(script.strip(), audio, voice, voice_rate))
        duration = duration_seconds(audio)
        count = len(video_bytes) if video_bytes else len(image_bytes)
        per_image = duration / count
        scene_count = max(count, round(duration / 4.0)) if video_bytes else count
        clips = []
        for idx in range(scene_count):
            data = (video_bytes if video_bytes else image_bytes)[idx % count]
            scene_duration = duration / scene_count
            if video_bytes:
                source = work / f"source_{idx:03d}.mp4"
                if len(data)>100*1024*1024:raise ValueError("Chaque clip MP4 doit faire moins de 100 Mo.")
                source.write_bytes(data)
                clip = work / f"clip_{idx:03d}.mp4"
                # Repeat short source clips if needed, discard their original audio.
                _run(["ffmpeg","-y","-loglevel","error","-stream_loop","-1","-i",str(source),
                      "-t",str(scene_duration+0.08),"-an","-vf",
                      "fps=25,scale=540:960:force_original_aspect_ratio=increase,crop=540:960,setsar=1,format=yuv420p",
                      "-c:v","libx264","-preset","ultrafast","-crf","27",str(clip)])
                clips.append(clip)
                continue
            with Image.open(BytesIO(data)) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                im = ImageOps.fit(im, (540, 960), method=Image.Resampling.LANCZOS)
                img = work / f"image_{idx:03d}.jpg"
                im.save(img, quality=85)
            clip = work / f"clip_{idx:03d}.mp4"
            frames = max(1, round(scene_duration * 25) + 1)
            # Alternate camera movement between scenes, staying lightweight on CPU.
            zoom = "min(zoom+0.00055,1.12)" if idx % 2 == 0 else "if(eq(on,0),1.12,max(zoom-0.00055,1.0))"
            x = "iw/2-(iw/zoom/2)" if idx % 3 else "min(iw-iw/zoom,on*0.12)"
            _run(["ffmpeg","-y","-loglevel","error","-loop","1","-i",str(img),
                  "-vf",f"zoompan=z='{zoom}':x='{x}':y='ih/2-(ih/zoom/2)':d={frames}:s=540x960:fps=25,format=yuv420p",
                  "-frames:v",str(frames),"-c:v","libx264","-preset","ultrafast","-crf","27",str(clip)])
            clips.append(clip)
        concat = work / "clips.txt"
        # Relative paths avoid Windows drive-letter escaping in FFmpeg concat lists.
        concat.write_text("".join(f"file '{p.name}'\n" for p in clips),encoding="utf-8")
        base = work / "base.mp4"
        _run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0",
              "-i",str(concat),"-i",str(audio),"-map","0:v:0","-map","1:a:0",
              "-t",str(duration),"-c:v","copy","-c:a","aac","-b:a","160k",
              "-movflags","+faststart",str(base)])
        filters = []
        if captions:
            if boundaries:
                srt = write_timed_srt(boundaries, work / "captions.srt")
                write_timed_ass(boundaries, work / "captions.ass")
            else:
                srt = write_srt(script, duration, work / "captions.srt")
                write_ass(script, duration, work / "captions.ass")
            # Use forward-slash relative filename from cwd to avoid Windows drive colon.
            filters.append("ass=captions.ass")
        if music:
            music_path = work / "music.mp3"
            music_path.write_bytes(music)
        if not filters and not music:
            shutil.copy2(base, output)
        else:
            cmd = ["ffmpeg","-y","-loglevel","error","-i",str(base)]
            if music:
                cmd += ["-stream_loop","-1","-i",str(music_path)]
            if filters:
                cmd += ["-vf",",".join(filters)]
            if music:
                cmd += ["-filter_complex",f"[0:a]volume=1.0[a0];[1:a]volume={max(0,min(music_volume,0.4))}[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[a]",
                        "-map","0:v:0","-map","[a]"]
            else:
                cmd += ["-map","0:v:0","-map","0:a:0"]
            cmd += ["-t",str(duration),"-c:v","libx264","-preset","veryfast",
                    "-crf","25","-c:a","aac","-b:a","160k","-movflags","+faststart",str(output)]
            # The subtitle filter resolves its path from the process cwd.
            result = subprocess.run(cmd,cwd=str(work),capture_output=True,text=True)
            if result.returncode:
                raise RuntimeError("FFmpeg (sous-titres/musique) : "+result.stderr[-1400:])
        if captions:
            shutil.copy2(work / "captions.srt", OUT / f"{slugify(title)}.srt")
    return output
