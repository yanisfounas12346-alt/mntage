"""Optional local Stable Diffusion CLI backend; no paid API."""
from __future__ import annotations
import os
import subprocess
import tempfile
from pathlib import Path
from io import BytesIO
from PIL import Image
import re

def configured() -> bool:
    return bool(os.environ.get("MNTAGE_SD_CLI") and os.environ.get("MNTAGE_SD_MODEL"))

STYLE_PROMPTS = {
    "documentaire cinématique": "cinematic documentary photography, natural colors, realistic lighting",
    "réaliste": "photorealistic editorial photography, realistic textures, natural light",
    "animation 3D": "high quality 3D animation, coherent art direction, detailed render",
    "illustration scientifique": "accurate scientific illustration, detailed educational visual",
    "fantastique": "cinematic fantasy concept art, atmospheric lighting, rich detail",
}

def scene_prompts(script: str, style: str = "documentaire cinématique", limit: int = 12) -> list[str]:
    """Produce consistent vertical scene prompts without using external footage."""
    if style not in STYLE_PROMPTS:
        raise ValueError("Style IA inconnu.")
    if not 1 <= limit <= 12:
        raise ValueError("Nombre de scènes IA invalide.")
    sentences=[s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+",script) if s.strip()]
    if not sentences:
        raise ValueError("Le script est vide.")
    # Each scene uses the same visual art direction to reduce style changes.
    return [
        f"{STYLE_PROMPTS[style]}, vertical 9:16 composition, cohesive visual series, "
        f"single clear subject, no text, no logo, no watermark. Scene: {sentence[:280]}"
        for sentence in sentences[:limit]
    ]

def generate_images(prompts: list[str], *, backend: str = "cpu", steps: int = 12) -> list[bytes]:
    exe = Path(os.environ.get("MNTAGE_SD_CLI", ""))
    model = Path(os.environ.get("MNTAGE_SD_MODEL", ""))
    if not exe.is_file() or not model.is_file():
        raise RuntimeError("Configure MNTAGE_SD_CLI et MNTAGE_SD_MODEL vers des fichiers existants.")
    if backend not in {"cpu", "auto", "vulkan0"}:
        raise ValueError("Backend non pris en charge.")
    if not 1 <= len(prompts) <= 12:
        raise ValueError("Entre 1 et 12 scènes IA sont nécessaires.")
    images = []
    with tempfile.TemporaryDirectory() as tmp:
        for index, prompt in enumerate(prompts):
            out = Path(tmp) / f"scene_{index}.png"
            args = [str(exe), "-m", str(model), "-p", prompt[:600],
                    "--width", "512", "--height", "896", "--steps", str(steps),
                    "-o", str(out)]
            if backend != "auto":
                args += ["--backend", backend]
            try:
                result = subprocess.run(args, capture_output=True, text=True, timeout=1800)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(f"Scène {index+1} : délai de 30 minutes dépassé.") from exc
            if result.returncode or not out.is_file():
                raise RuntimeError(f"Scène {index+1} : erreur Stable Diffusion : {result.stderr[-1200:]}")
            with Image.open(out) as im:
                buf = BytesIO()
                im.convert("RGB").save(buf, "JPEG", quality=88)
                images.append(buf.getvalue())
    return images
