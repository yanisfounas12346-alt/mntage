"""Original offline 2D motion studio for the Science WTF mirror pilot.

Every frame is drawn from vector-like primitives with independent scene,
character, reflection, and science-diagram layers. No stock or AI artwork,
no camera panning, no external assets or paid APIs.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

NAVY = (13, 23, 38)
PANEL = (22, 42, 61)
PANEL2 = (30, 67, 81)
CYAN = (0, 217, 192)
YELLOW = (255, 212, 71)
PINK = (255, 84, 120)
WHITE = (248, 250, 252)
MUTED = (110, 166, 182)
DARK = (8, 16, 28)
BASE_W, BASE_H = 540, 960


@dataclass(frozen=True)
class MotionScene:
    kind: str
    start: float
    end: float
    shot: int = 0
    beat_from: float = 0.0
    beat_to: float = 1.0


# Stage boundaries are located in the actual script, rather than fixed time slots.
MIRROR_BEATS = (
    ("stare", r"puis tu fixes|tu fixes ton|sans bouger"),
    ("distort", r"ton nez|tes yeux semblent|visage devient|visage se déforme"),
    ("brain", r"c.est ton cerveau|cerveau qui bug|cerveau commence"),
    ("experiment", r"des chercheurs|une expérience|participants regard"),
    ("distort", r"et certains|déformations étranges"),
    ("brain", r"mais pourquoi|parce que ton cerveau"),
    ("neural", r"il reconstruit|reconstruit constamment"),
    ("vision", r"quand tu fixes|informations visuelles"),
    ("distort", r"résultat\s*:|propre reflet"),
    ("reveal", r"le plus fou|besoin d.un miroir|miroir hanté"),
    ("outro", r"abonne.toi|prochain épisode|science wtf"),
)


def is_mirror_subject(subject: str, script: str = "") -> bool:
    """Never promise a mirror-specific animation for unrelated topics."""
    return bool(re.search(r"miroir|reflet|réflexion|reflection", subject, re.I)
                or ("miroir" in script.lower() and "visage" in script.lower()))


def _timestamp_for_match(script: str, position: int, duration: float, boundaries: list[dict] | None) -> float:
    words = re.findall(r"\w+", script, re.UNICODE)
    fraction = len(re.findall(r"\w+", script[:position], re.UNICODE)) / max(1, len(words))
    if boundaries:
        index = min(len(boundaries) - 1, round(fraction * len(boundaries)))
        try:
            value = float(boundaries[index]["offset"]) / 10_000_000.0
            return max(0.0, min(duration, value))
        except (TypeError, ValueError, KeyError):
            pass
    return fraction * duration


def plan_mirror_scenes(script: str, duration: float, boundaries: list[dict] | None = None) -> list[MotionScene]:
    """Timed narrative beats aligned approximately to Edge-TTS word boundaries."""
    if not script.strip() or not math.isfinite(duration) or duration <= 0:
        raise ValueError("Script ou durée invalide pour le studio animé.")
    matched = [("approach", 0.0)]
    from_pos = 0
    for kind, pattern in MIRROR_BEATS:
        match = re.search(pattern, script[from_pos:], re.I)
        if match is None:
            continue
        start_pos = from_pos + match.start()
        time = _timestamp_for_match(script, start_pos, duration, boundaries)
        if time - matched[-1][1] >= 1.4 and duration - time >= 1.0:
            matched.append((kind, time))
        from_pos = from_pos + match.end()
    result = []
    for i, (kind, start) in enumerate(matched):
        end = matched[i + 1][1] if i + 1 < len(matched) else duration
        if end > start:
            result.append(MotionScene(kind, start, end))
    if len(result) < 4:
        raise ValueError("Storyboard miroir incomplet : colle le script du miroir pour animer correctement l'histoire.")
    # Cut the narration into short compositions without moving the camera.
    # Open with the strange reflection for a short visual hook, then explain it.
    # No camera movement; the story still follows the narration after the hook.
    shots = []
    if duration >= 16 and result[0].end >= 2.1:
        hook_duration = min(1.1, result[0].end * .42)
        shots.append(MotionScene("distort", 0.0, hook_duration, 2, .75, .94))
        result[0] = MotionScene(result[0].kind, hook_duration, result[0].end)
    for beat in result:
        shot_count = max(1, math.ceil((beat.end - beat.start) / 3.25))
        for part in range(shot_count):
            a = beat.start + (beat.end - beat.start) * part / shot_count
            b = beat.start + (beat.end - beat.start) * (part + 1) / shot_count
            shots.append(MotionScene(beat.kind, a, b, len(shots) % 4, part/shot_count, (part+1)/shot_count))
    return shots


def mouth_open_at(seconds: float, boundaries: list[dict] | None) -> float:
    """Word-aligned mouth motion from TTS timestamps; not phoneme-perfect lip sync."""
    if boundaries is None:
        return 0.25 + 0.7 * abs(math.sin(seconds * 15.0))
    for word in boundaries:
        try:
            start = float(word["offset"]) / 10_000_000.0
            end = start + float(word["duration"]) / 10_000_000.0
        except (TypeError, KeyError, ValueError):
            continue
        if start <= seconds < end:
            return 0.18 + 0.78 * abs(math.sin((seconds - start) * 23.0))
    return 0.0


def _ease(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


class _Painter:
    """Scale one original 540x960 design consistently to any export resolution."""
    def __init__(self, image: Image.Image):
        self.d = ImageDraw.Draw(image)
        self.s = image.width / BASE_W

    def p(self, x: float, y: float) -> tuple[int, int]:
        return (round(x * self.s), round(y * self.s))

    def rect(self, box, fill, radius=0, outline=None, width=1):
        self.d.rounded_rectangle((*self.p(box[0], box[1]), *self.p(box[2], box[3])),
                                 radius=round(radius * self.s), fill=fill, outline=outline,
                                 width=max(1, round(width * self.s)))

    def ellipse(self, box, fill=None, outline=None, width=1):
        self.d.ellipse((*self.p(box[0], box[1]), *self.p(box[2], box[3])),
                       fill=fill, outline=outline, width=max(1, round(width * self.s)))

    def line(self, points, fill, width=2):
        self.d.line([self.p(x, y) for x, y in points], fill=fill,
                    width=max(1, round(width * self.s)), joint="curve")

    def text(self, xy, value, color=WHITE, size=23, anchor="mm"):
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", round(size * self.s))
        except OSError:
            font = ImageFont.load_default()
        self.d.text(self.p(*xy), value, font=font, fill=color, anchor=anchor)


def _background(size, scene_kind):
    image = Image.new("RGB", size, NAVY)
    p = _Painter(image)
    for x in range(0, 541, 54):
        p.line([(x, 65), (x, 875)], (21, 37, 55), 1)
    for y in range(70, 880, 54):
        p.line([(0, y), (540, y)], (21, 37, 55), 1)
    p.ellipse((-175, -200, 240, 210), outline=(23, 82, 87), width=3)
    p.ellipse((375, 90, 710, 425), outline=(23, 71, 80), width=2)
    p.rect((34, 45, 506, 53), CYAN, radius=4)
    p.rect((34, 87, 119, 94), YELLOW, radius=3)
    p.text((37, 124), "SCIENCE WTF", WHITE, 20, anchor="lm")
    p.text((37, 155), "LAB / 01", MUTED, 11, anchor="lm")
    return image


def _limb(p, pts, width=13):
    p.line(pts, DARK, width + 6)
    p.line(pts, WHITE, width)
    for x, y in (pts[0], pts[-1]):
        p.ellipse((x-width/2, y-width/2, x+width/2, y+width/2), WHITE)


def _scientist(p, cx, cy, size=1.0, wave=0.0, startled=0.0, blink=False, side=1, mouth=0.0):
    """One consistent original character. Limbs, backpack and face are separate motions."""
    def xy(x, y):
        return (cx + x * size * side, cy + y * size)
    def box(x1,y1,x2,y2):
        a, b = xy(x1,y1), xy(x2,y2)
        return min(a[0],b[0]), min(a[1],b[1]), max(a[0],b[0]), max(a[1],b[1])
    yshift = 2.6 * math.sin(wave)
    cx0, cy0 = cx, cy + yshift
    def at(x,y):return cx0 + x*size*side, cy0+y*size
    p.ellipse((cx-68*size, cy+173*size, cx+68*size, cy+187*size), (7, 16, 27))
    p.rect(box(22,-22,77,85), YELLOW, radius=13*size, outline=DARK, width=5*size)
    _limb(p, [at(0,66),at(-44,154)], 11*size)
    _limb(p, [at(0,66),at(45,154)], 11*size)
    _limb(p, [at(0,-34),at(0,70)], 17*size)
    _limb(p, [at(0,-8),at(-47,28-startled*25)], 11*size)
    _limb(p, [at(0,-8),at(50,-13-34*startled)], 11*size)
    p.ellipse(box(-52,-147,52,-43), WHITE, outline=DARK, width=5*size)
    if blink:
        p.line([at(-19,-103), at(-10,-103)], DARK, 3*size)
        p.line([at(11,-103), at(20,-103)], DARK, 3*size)
    else:
        p.ellipse(box(-23,-110,-12,-97), DARK)
        p.ellipse(box(12,-110,23,-97), DARK)
    if mouth > 0.12:
        lip_width = 7 + 9 * mouth
        lip_height = 3 + 15 * mouth
        center = at(0, -76)
        p.ellipse((center[0]-lip_width*size, center[1]-lip_height*size,
                   center[0]+lip_width*size, center[1]+lip_height*size), DARK)
        if mouth > 0.75:
            p.line([(center[0]-lip_width*size*.65,center[1]+lip_height*size*.54),
                    (center[0]+lip_width*size*.65,center[1]+lip_height*size*.54)],
                   PINK, 2*size)
    elif startled > 0.35:
        p.ellipse(box(-8,-87,8,-66), DARK)
    else:
        p.line([at(-12,-77), at(0,-70), at(13,-78)], DARK, 3*size)


def _mirror(p, cx=388, top=245, width=174, height=430, distort=0.0, t=0.0):
    left = cx-width/2
    right = cx+width/2
    p.rect((left-13,top-15,right+13,top+height+15), (9,19,32), radius=32,
           outline=CYAN, width=7)
    p.rect((left,top,right,top+height), (34,79,92), radius=23,
           outline=(74,143,151), width=2)
    p.rect((left+14,top+17,left+24,top+height-17), (48,107,119), radius=5)
    facex, facey = cx, top+137
    jitter = distort * math.sin(t*4.6)
    shift = jitter * 20
    # The reflection itself morphs; the original character and camera stay stable.
    face_width = 59 + distort * 25 * math.sin(t * 2.1)
    face_height = 70 + distort * 18 * math.cos(t * 2.6)
    p.ellipse((facex-face_width+shift,facey-face_height,
               facex+face_width+shift,facey+face_height), WHITE,
              outline=DARK, width=5)
    p.ellipse((facex-27-10*distort,facey-10,facex-16-10*distort,facey+5), DARK)
    p.ellipse((facex+18+13*distort,facey-8-16*distort,facex+29+13*distort,facey+8+10*distort), DARK)
    if distort > 0.3:
        p.ellipse((facex-5,facey+23,facex+12+20*distort,facey+43+24*distort), DARK)
    else:
        p.line([(facex-17,facey+34),(facex,facey+41),(facex+18,facey+34)], DARK, 4)
    p.line([(cx,facey+69),(cx,top+height-32)], WHITE, 19)
    p.rect((cx+17,facey+102,cx+49,facey+160), YELLOW, radius=11,
           outline=DARK, width=4)
    if distort > .1:
        for z in range(3):
            y = top + 30 + z*110 + 12*math.sin(t*3+z)
            p.line([(left+15, y),(cx-20,y+distort*12),(right-15,y-distort*9)],
                   PINK if z==1 else CYAN, 2+2*distort)


def _brain(p, cx=270, cy=370, t=0.0, scale=1.0):
    r = 115*scale
    p.ellipse((cx-r-20,cy-r-20,cx+r+20,cy+r+20), outline=PANEL2, width=4)
    blobs=[(-68,-32,58),(-27,-78,65),(47,-79,58),(85,-25,52),
           (72,49,58),(11,78,59),(-59,57,61)]
    for j,(dx,dy,rad) in enumerate(blobs):
        pulse=(1+0.035*math.sin(t*3+j))*scale
        x,y=cx+dx*scale,cy+dy*scale
        p.ellipse((x-rad*pulse,y-rad*pulse,x+rad*pulse,y+rad*pulse),
                  PANEL2, outline=CYAN if j%2==0 else (63,144,150), width=4)
    for j,(dx,dy,_) in enumerate(blobs):
        a=t*2.2+j*.75
        x,y=cx+dx*scale,cy+dy*scale
        p.ellipse((x-6*scale+7*math.sin(a),y-6*scale,x+6*scale+7*math.sin(a),y+6*scale),
                  YELLOW if j%2 else PINK)
    p.line([(cx,cy-110*scale),(cx,cy+114*scale)], (7,24,38), 8*scale)


def _draw_frame(size, kind, progress, seconds, base, shot=0, mouth=0.0, beat_progress=None):
    """Draw an original scene composed of background, actions and optical effect."""
    from motion_director import draw_professional_frame
    return draw_professional_frame(base, kind, shot, progress, seconds, mouth, beat_progress=beat_progress)


def render_motion_scene(destination: Path, scene: MotionScene, *, fps: int = 25,
                        width: int = 1080, height: int = 1920,
                        boundaries: list[dict] | None = None) -> None:
    """Stream native HD frames to FFmpeg without storing thousands of PNGs."""
    if width * BASE_H != height * BASE_W or fps < 1 or scene.end <= scene.start:
        raise ValueError("Format ou durée du plan animé invalide.")
    frames=max(1,round((scene.end-scene.start)*fps))
    base=_background((width,height),scene.kind)
    args=["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pixel_format","rgb24",
          "-video_size",f"{width}x{height}","-framerate",str(fps),"-i","pipe:0",
          "-an","-c:v","libx264","-preset","veryfast","-crf","19",
          "-pix_fmt","yuv420p","-movflags","+faststart",str(destination)]
    proc=subprocess.Popen(args,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        assert proc.stdin is not None
        for i in range(frames):
            progress=i/max(frames-1,1)
            absolute_seconds=scene.start + i/fps
            mouth=mouth_open_at(absolute_seconds,boundaries)
            arc=scene.beat_from+(scene.beat_to-scene.beat_from)*progress
            image=_draw_frame((width,height),scene.kind,progress,
                              scene.end-scene.start,base,shot=scene.shot,mouth=mouth,beat_progress=arc)
            proc.stdin.write(image.tobytes())
        proc.stdin.close()
        assert proc.stderr is not None
        stderr=proc.stderr.read().decode("utf-8",errors="replace")
        result=proc.wait(timeout=240)
        if result:
            raise RuntimeError("Échec du rendu animé FFmpeg : "+stderr[-900:])
    except Exception:
        proc.kill()
        proc.wait()
        destination.unlink(missing_ok=True)
        raise
    finally:
        if proc.stderr:
            proc.stderr.close()


def render_mirror_preview(destination: Path, seconds: float = 8.0) -> Path:
    """Three compositions in eight seconds, with an animated speaking mouth."""
    import tempfile
    if seconds <= 0 or seconds > 15:
        raise ValueError("L'aperçu doit durer entre 0 et 15 secondes.")
    # Five purposeful edits: visual hook, entry, stare, surprise, brain reveal.
    shots = [MotionScene("distort",0.0,seconds*.15,2,.75,.96),
             MotionScene("approach",seconds*.15,seconds*.30,0),
             MotionScene("stare",seconds*.30,seconds*.50,3),
             MotionScene("distort",seconds*.50,seconds*.70,1),
             MotionScene("brain",seconds*.70,seconds,2)]
    with tempfile.TemporaryDirectory() as folder:
        files=[]
        for i,shot in enumerate(shots):
            path=Path(folder) / f"shot_{i}.mp4"
            render_motion_scene(path,shot)
            files.append(path)
        manifest=Path(folder) / "clips.txt"
        manifest.write_text("".join(f"file '{path.name}'\n" for path in files),encoding="utf-8")
        subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0",
                        "-i",str(manifest),"-c","copy",str(destination)],
                       check=True,capture_output=True,timeout=120)
    return destination
