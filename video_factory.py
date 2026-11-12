from __future__ import annotations
import asyncio
import re
import math
import shutil
import subprocess
import tempfile
from uuid import uuid4
from pathlib import Path
from io import BytesIO
import edge_tts
from PIL import Image, ImageOps
from subtitles import write_srt, write_ass, write_timed_srt, write_timed_ass
from motion_studio import plan_mirror_scenes, render_motion_scene, is_mirror_subject

WIDTH, HEIGHT = 1080, 1920
OUT = Path("outputs").resolve()
OUT.mkdir(exist_ok=True)

def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", value.lower().strip())[:60].strip("-") or "video"

def validate_image_dimensions(width: int, height: int) -> None:
    """Avoid excessive memory allocation from compressed source images."""
    if width <= 0 or height <= 0 or width * height > 40_000_000:
        raise ValueError("Image trop grande ou invalide : maximum 40 mégapixels.")

def require_ffmpeg():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg et ffprobe doivent être installés et présents dans le PATH.")

def duration_seconds(audio: Path) -> float:
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","default=noprint_wrappers=1:nokey=1",str(audio)],
                       capture_output=True,text=True,check=True,timeout=30)
    try:
        duration=float(r.stdout.strip())
    except ValueError as exc:
        raise RuntimeError("Durée audio illisible : ffprobe n'a pas retourné de nombre.") from exc
    if not math.isfinite(duration) or duration<=0:
        raise RuntimeError("Durée audio invalide : la voix est vide ou corrompue.")
    return duration

def validate_music_audio(path: Path) -> None:
    """Reject video-only or renamed files masquerading as an MP3."""
    import json
    try:
        result = subprocess.run(
            ["ffprobe","-v","error","-select_streams","a:0",
             "-show_entries","stream=codec_type,codec_name",
             "-of","json",str(path)],
            capture_output=True,text=True,timeout=30)
        data = json.loads(result.stdout) if result.returncode == 0 else {}
    except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
        raise ValueError("Musique MP3 illisible ou sans piste audio.") from exc
    streams = data.get("streams", [])
    if not streams or streams[0].get("codec_type") != "audio":
        raise ValueError("Musique MP3 illisible ou sans piste audio.")
    if streams[0].get("codec_name") != "mp3":
        raise ValueError("La musique doit être un véritable fichier MP3.")

def prepare_narration(script: str) -> str:
    """Normalize whitespace and pauses while preserving the spoken words."""
    text = re.sub(r"[ \t]+", " ", script.strip())
    text = re.sub(r"\s*\n+\s*", ". ", text)
    text = re.sub(r"([.!?])\s*\.\s+", r"\1 ", text)
    text = re.sub(r"\s+([,;:.!?])", r"\1", text)
    text = re.sub(r"([.!?])(?=[^\s.!?])", r"\1 ", text)
    text = re.sub(r"([,;:])(?=[^\s])", r"\1 ", text)
    return text.strip()

async def synthesize(script: str, destination: Path, voice: str, rate: str = "-5%"):
    boundaries=[]
    with destination.open("wb") as audio:
        async for chunk in edge_tts.Communicate(prepare_narration(script), voice=voice, rate=rate).stream():
            if chunk["type"]=="audio":
                audio.write(chunk["data"])
            elif chunk["type"]=="WordBoundary":
                boundaries.append({"offset":chunk["offset"],"duration":chunk["duration"],"text":chunk["text"]})
    if not destination.stat().st_size:
        raise RuntimeError("La synthèse vocale n'a produit aucun audio.")
    return boundaries

def _run(args, timeout=1800):
    """Bound stalled FFmpeg processes and provide actionable errors."""
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"FFmpeg bloqué : délai de {timeout} secondes dépassé.") from exc
    if result.returncode:
        raise RuntimeError("FFmpeg : " + result.stderr[-1400:])

def scene_durations(duration: float, boundaries: list[dict], clip_count: int) -> list[float]:
    """Keep cuts near speech boundaries, with no very short or giant final scene."""
    if not math.isfinite(duration) or duration <= 0 or clip_count < 1:
        raise ValueError("Durée ou nombre de clips invalide.")
    target_count=min(24,max(clip_count,round(duration/4.0)))
    target_count=min(target_count,max(1,int(duration/1.5)))
    if target_count==1:
        return [duration]
    ends=sorted({min(duration,max(0.0,(w["offset"]+w["duration"])/10000000))
                 for w in boundaries if w.get("duration",0)>=0})
    cuts=[0.0]
    for i in range(1,target_count):
        ideal=duration*i/target_count
        # A narrow window preserves rhythm even if the speech has long pauses.
        window=min(0.8,duration/target_count*0.25)
        choices=[t for t in ends if abs(t-ideal)<=window
                 and t-cuts[-1]>=1.0 and duration-t>=1.0]
        cut=min(choices,key=lambda t:abs(t-ideal)) if choices else ideal
        if cut-cuts[-1]<1.0:
            cut=ideal
        cuts.append(cut)
    cuts.append(duration)
    return [b-a for a,b in zip(cuts,cuts[1:])]

def scene_source_index(scene_index: int, scene_count: int, source_count: int) -> int:
    """Keep storyboard images in narrative order when creating extra fast cuts.

    Reusing an image in adjacent shots is less confusing than cycling back
    to the opening image halfway through the story.
    """
    if scene_count < 1 or source_count < 1 or not 0 <= scene_index < scene_count:
        raise ValueError("Index de scène invalide.")
    return min(source_count - 1, scene_index * source_count // scene_count)


def validate_output(path: Path, expected_duration: float) -> None:
    """Reject missing, truncated, or incorrectly sized exports."""
    import json
    if not path.is_file() or path.stat().st_size < 1024:
        raise RuntimeError("Le MP4 exporté est absent ou vide.")
    try:
        result=subprocess.run(
            ["ffprobe","-v","error","-show_entries",
             "format=duration:stream=codec_type,width,height",
             "-of","json",str(path)],
            capture_output=True,text=True,timeout=30)
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise RuntimeError("Impossible de vérifier le MP4 : FFprobe indisponible ou trop lent.") from exc
    if result.returncode:
        raise RuntimeError("Impossible de vérifier le MP4 : "+result.stderr[-500:])
    try:
        data=json.loads(result.stdout)
        streams=data["streams"]
        if not isinstance(streams,list):
            raise ValueError("Liste des pistes invalide")
    except (ValueError, TypeError, KeyError) as exc:
        raise RuntimeError("Métadonnées du MP4 exporté illisibles.") from exc
    videos=[s for s in streams if s.get("codec_type")=="video"]
    audios=[s for s in streams if s.get("codec_type")=="audio"]
    if not videos or not audios:
        raise RuntimeError("Export incomplet : vidéo ou voix absente.")
    if (videos[0].get("width"),videos[0].get("height")) != (WIDTH,HEIGHT):
        raise RuntimeError("Export incorrect : résolution verticale 1080x1920 attendue.")
    try:
        actual=float(data.get("format",{}).get("duration",0))
    except (TypeError,ValueError) as exc:
        raise RuntimeError("Durée MP4 illisible.") from exc
    if not math.isfinite(actual) or actual<=0 or abs(actual-expected_duration)>1.0:
        raise RuntimeError(f"Durée incorrecte : {actual:.1f}s au lieu de {expected_duration:.1f}s.")

def inspect_source_video(path: Path) -> dict:
    """Probe a source before expensive encoding; reject broken or tiny videos."""
    import json
    result=subprocess.run(
        ["ffprobe","-v","error","-select_streams","v:0",
         "-show_entries","stream=width,height,duration:format=duration",
         "-of","json",str(path)],capture_output=True,text=True,timeout=30)
    if result.returncode:
        raise RuntimeError("Clip source illisible : "+result.stderr[-300:])
    try:
        data=json.loads(result.stdout)
        video=data.get("streams",[])[0]
        width,height=int(video["width"]),int(video["height"])
        raw_duration=video.get("duration")
        if raw_duration in (None,"","N/A"):
            raw_duration=data.get("format",{}).get("duration",0)
        duration=float(raw_duration)
    except (ValueError,TypeError,KeyError,IndexError) as exc:
        raise RuntimeError("Métadonnées vidéo source invalides.") from exc
    if width<480 or height<480:
        raise RuntimeError(f"Clip trop petit ({width}x{height}) : minimum 480 px par dimension.")
    if width * height > 3840 * 2160:
        raise RuntimeError(f"Clip trop grand ({width}x{height}) : maximum 8,3 mégapixels (4K).")
    if not math.isfinite(duration) or duration<0.5:
        raise RuntimeError("Clip source trop court ou sans durée détectable.")
    return {"width":width,"height":height,"duration":duration}


def make_video(title: str, script: str, image_bytes: list[bytes],
               voice: str = "fr-FR-DeniseNeural",
               captions: bool = True, music: bytes | None = None,
               music_volume: float = 0.12, voice_rate: str = "-5%", video_bytes: list[bytes] | None = None, dynamic: bool = False,
               motion_mode: bool = False, motion_subject: str = "") -> Path:
    require_ffmpeg()
    if motion_mode and (video_bytes or image_bytes):
        raise ValueError("Studio animé : ne fournis pas de visuels externes.")
    if motion_mode and not is_mirror_subject(motion_subject, script):
        raise ValueError("Le studio animé pilote prend en charge uniquement le sujet du miroir.")
    if any(not data for data in image_bytes) or any(not data for data in (video_bytes or [])):
        raise ValueError("Un visuel importé est vide : retire le fichier et réessaie.")
    if not script.strip() or not (image_bytes or video_bytes or motion_mode):
        raise ValueError("Un script et au moins un visuel sont nécessaires.")
    if len(image_bytes) > 24 or len(video_bytes or []) > 24:
        raise ValueError("Maximum 24 visuels pour protéger les ressources du PC.")
    if any(len(data)>100*1024*1024 for data in (video_bytes or [])):
        raise ValueError("Chaque clip MP4 doit faire au maximum 100 Mo.")
    if sum(map(len,video_bytes or [])) > 300*1024*1024:
        raise ValueError("Les vidéos dépassent la limite totale de 300 Mo.")
    if any(len(data)>20*1024*1024 for data in image_bytes):
        raise ValueError("Chaque image doit faire au maximum 20 Mo.")
    if sum(map(len,image_bytes)) > 100*1024*1024:
        raise ValueError("Les images dépassent la limite totale de 100 Mo.")
    if music is not None and (not music or len(music)>30*1024*1024):
        raise ValueError("La musique MP3 doit être non vide et faire au maximum 30 Mo.")
    # Check image headers and pixel budgets before contacting the TTS service.
    if not video_bytes:
        import warnings
        for idx, data in enumerate(image_bytes, start=1):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(BytesIO(data)) as source_image:
                        validate_image_dimensions(*source_image.size)
                        # Detect malformed/truncated image payloads before paid-in-time TTS.
                        source_image.verify()
            except (OSError, SyntaxError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
                raise ValueError(f"Image {idx} invalide ou trop grande.") from exc
    OUT.mkdir(exist_ok=True)
    output = OUT / f"{slugify(title)}-{uuid4().hex[:8]}.mp4"
    try:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            # Probe all imported clips before starting online speech synthesis.
            source_paths = {}
            if video_bytes:
                for idx, data in enumerate(video_bytes):
                    source = work / f"source_{idx:03d}.mp4"
                    source.write_bytes(data)
                    try:
                        inspect_source_video(source)
                    except (RuntimeError, OSError, ValueError) as exc:
                        raise ValueError(f"Clip MP4 {idx + 1} invalide : {exc}") from exc
                    source_paths[idx] = source
            if music is not None:
                music_path = work / "music.mp3"
                music_path.write_bytes(music)
                try:
                    validate_music_audio(music_path)
                    duration_seconds(music_path)
                except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                    raise ValueError("Musique MP3 invalide ou illisible.") from exc
            audio = work / "voice.mp3"
            boundaries = asyncio.run(synthesize(script.strip(), audio, voice, voice_rate))
            duration = duration_seconds(audio)
            if motion_mode:
                motion_scenes = plan_mirror_scenes(script, duration, boundaries)
                durations = [scene.end-scene.start for scene in motion_scenes]
                count = 0
            else:
                motion_scenes = []
                count = len(video_bytes) if video_bytes else len(image_bytes)
                durations = scene_durations(duration,boundaries,count) if (video_bytes or dynamic) else [duration/count]*count
            scene_count = len(durations)
            clips = []
            for idx in range(scene_count):
                if motion_mode:
                    clip = work / f"clip_{idx:03d}.mp4"
                    render_motion_scene(clip, motion_scenes[idx], boundaries=boundaries)
                    clips.append(clip)
                    continue
                source_index = scene_source_index(idx, scene_count, count) if dynamic else idx % count
                data = (video_bytes if video_bytes else image_bytes)[source_index]
                scene_duration = durations[idx]
                if video_bytes:
                    source = source_paths[source_index]
                    clip = work / f"clip_{idx:03d}.mp4"
                    # Repeat short source clips if needed, discard their original audio.
                    _run(["ffmpeg","-y","-loglevel","error","-stream_loop","-1","-i",str(source),
                          "-t",str(scene_duration),"-an","-vf",
                          "fps=25,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,format=yuv420p",
                          "-c:v","libx264","-preset","veryfast","-crf","19",str(clip)])
                    clips.append(clip)
                    continue
                # Compressed images can be tiny on disk but huge once decoded.
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(BytesIO(data)) as im:
                        validate_image_dimensions(im.width, im.height)
                        im = ImageOps.exif_transpose(im).convert("RGB")
                    im = ImageOps.fit(im, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
                    img = work / f"image_{idx:03d}.jpg"
                    im.save(img, quality=95, subsampling=0)
                clip = work / f"clip_{idx:03d}.mp4"
                frames = max(1, round(scene_duration * 25))
                # Science WTF: faster cuts, stable framing. No continuous panning or zooming.
                # Older non-dynamic exports retain their subtle Ken Burns movement.
                zoom = "1" if dynamic else ("min(zoom+0.00055,1.12)" if idx % 2 == 0 else "if(eq(on,0),1.12,max(zoom-0.00055,1.0))")
                x = "0" if dynamic else ("iw/2-(iw/zoom/2)" if idx % 3 else "min(iw-iw/zoom,on*0.12)")
                if dynamic:
                    # Existing artwork may already contain a character. Avoid stickers
                    # and duplicates; only the authored 2D studio animates objects.
                    _run(["ffmpeg","-y","-loglevel","error","-loop","1","-framerate","25",
                          "-i",str(img),"-vf",
                          "fps=25,scale=1080:1920,setsar=1,format=yuv420p",
                          "-frames:v",str(frames),"-c:v","libx264","-preset","veryfast",
                          "-crf","19",str(clip)])
                else:
                    _run(["ffmpeg","-y","-loglevel","error","-loop","1","-i",str(img),
                          "-vf",f"zoompan=z='{zoom}':x='{x}':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=25,format=yuv420p",
                          "-frames:v",str(frames),"-c:v","libx264","-preset","veryfast","-crf","19",str(clip)])
                clips.append(clip)
            concat = work / "clips.txt"
            # Relative paths avoid Windows drive-letter escaping in FFmpeg concat lists.
            concat.write_text("".join(f"file '{p.name}'\n" for p in clips),encoding="utf-8")
            base = work / "base.mp4"
            _run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0",
                  "-i",str(concat),"-i",str(audio),"-map","0:v:0","-map","1:a:0",
                  "-t",str(duration),"-c:v","libx264","-preset","veryfast","-crf","23",
                  "-pix_fmt","yuv420p","-c:a","aac","-b:a","160k",
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
                        "-crf","19","-c:a","aac","-b:a","160k","-movflags","+faststart",str(output)]
                # The subtitle filter resolves its path from the process cwd.
                try:
                    result = subprocess.run(cmd,cwd=str(work),capture_output=True,text=True,timeout=1800)
                except subprocess.TimeoutExpired as exc:
                    raise RuntimeError("FFmpeg (sous-titres/musique) bloqué plus de 30 minutes.") from exc
                if result.returncode:
                    raise RuntimeError("FFmpeg (sous-titres/musique) : "+result.stderr[-1400:])
            if captions:
                shutil.copy2(work / "captions.srt", output.with_suffix(".srt"))
        validate_output(output, duration)
        return output
    except Exception:
        output.unlink(missing_ok=True)
        output.with_suffix(".srt").unlink(missing_ok=True)
        raise
