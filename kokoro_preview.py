"""Optional offline Kokoro French voice comparison (not used in video exports yet).

Install separately: python -m pip install kokoro soundfile
Kokoro French phonemization also requires eSpeak NG installed on Windows.
First run may download model weights from Hugging Face.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def generate_preview(text: str, output: Path, *, speed: float = 0.9) -> Path:
    if not text.strip():
        raise ValueError("Le texte de test ne peut pas être vide.")
    if not 0.7 <= speed <= 1.2:
        raise ValueError("Vitesse Kokoro attendue entre 0.7 et 1.2.")
    try:
        import numpy as np
        import soundfile as sf
        from kokoro import KPipeline
    except ImportError as exc:
        raise RuntimeError(
            "Kokoro non installé. Lance : python -m pip install kokoro soundfile. "
            "Installe aussi eSpeak NG pour le français."
        ) from exc

    try:
        pipeline = KPipeline(lang_code="f", device="cpu")
        chunks = [audio for _, _, audio in pipeline(
            text.strip(), voice="ff_siwis", speed=speed, split_pattern=r"\n+"
        )]
    except Exception as exc:
        raise RuntimeError(
            "Échec Kokoro français : vérifie eSpeak NG, les modèles téléchargés "
            "et la compatibilité de PyTorch avec ton PC."
        ) from exc
    if not chunks:
        raise RuntimeError("Kokoro n'a produit aucun audio.")
    output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output), np.concatenate(chunks), 24000)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tester une voix Kokoro française hors ligne")
    parser.add_argument("--text", default="Sous la surface de l'océan, un monde mystérieux nous attend. Certaines créatures brillent dans le noir.")
    parser.add_argument("--output", default="outputs/kokoro_test_fr.wav")
    parser.add_argument("--speed", type=float, default=0.9)
    args = parser.parse_args()
    print("Aperçu créé :", generate_preview(args.text, Path(args.output), speed=args.speed))
