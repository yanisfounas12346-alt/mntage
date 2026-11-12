"""Render the original MNTAGE mirror studio's eight-second silent preview.

Temporary demo only; no change to the production video engine.
"""
from pathlib import Path
import subprocess
import tempfile

from motion_studio import MotionScene, render_motion_scene

SECONDS = 8.0
SHOTS = (
    MotionScene("distort", 0.0, SECONDS * .15, 4, .75, .96),
    MotionScene("approach", SECONDS * .15, SECONDS * .30, 0),
    MotionScene("stare", SECONDS * .30, SECONDS * .50, 3),
    MotionScene("distort", SECONDS * .50, SECONDS * .70, 5, .20, .80),
    MotionScene("brain", SECONDS * .70, SECONDS, 4),
)

def render():
    destination = Path("outputs") / "demo"
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / "MNTAGE_demo_miroir_8s.mp4"
    with tempfile.TemporaryDirectory() as tmp:
        working = Path(tmp)
        paths = []
        for index, shot in enumerate(SHOTS):
            clip = working / f"scene_{index:02}.mp4"
            render_motion_scene(clip, shot, width=540, height=960, fps=25)
            paths.append(clip)
        manifest = working / "concat.txt"
        manifest.write_text(
            "".join(f"file '{clip.name}'\n" for clip in paths), encoding="utf-8"
        )
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
             "-safe", "0", "-i", str(manifest),
             "-c", "copy", "-movflags", "+faststart", str(target)],
            check=True, timeout=120, capture_output=True
        )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", "1.9",
         "-i", str(target), "-frames:v", "1",
         str(destination / "MNTAGE_demo_affiche.png")],
        check=True, timeout=60, capture_output=True
    )
    if not target.is_file() or target.stat().st_size < 10000:
        raise RuntimeError("Le rendu MNTAGE est absent ou anormalement petit.")
    print(f"Rendered real MNTAGE preview: {target} ({target.stat().st_size} bytes)")

if __name__ == "__main__":
    render()
