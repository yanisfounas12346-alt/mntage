"""Cheap audio-envelope driven facial animation; never modifies the voice track."""
from __future__ import annotations
from array import array
from dataclasses import dataclass
import math
from pathlib import Path
import struct
import subprocess
import sys


@dataclass(frozen=True)
class SpeechMotion:
    """A 20ms speech intensity track indexed by absolute narration time."""
    values: tuple[float, ...]
    step_seconds: float = 0.02

    def at(self, seconds: float) -> float:
        if not self.values or not math.isfinite(seconds) or seconds < 0:
            return 0.0
        index = seconds / self.step_seconds
        i = int(index)
        if i >= len(self.values):
            return 0.0
        if i + 1 == len(self.values):
            return self.values[i]
        blend = index - i
        return self.values[i] * (1 - blend) + self.values[i + 1] * blend


def speech_motion_from_pcm(pcm: bytes, sample_rate: int = 8000,
                           step_seconds: float = 0.02) -> SpeechMotion:
    """Derive mouth opening from actual audio loudness with silence detection.

    The track does not infer phonemes or alter the original MP3.
    """
    if sample_rate < 1000 or not 0.005 <= step_seconds <= 0.1:
        raise ValueError("Paramètres audio non pris en charge.")
    if len(pcm) % 2:
        raise ValueError("PCM 16 bits invalide.")
    samples = array("h")
    samples.frombytes(pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    window = max(1, round(sample_rate * step_seconds))
    rms = []
    for i in range(0, len(samples), window):
        block = samples[i:i+window]
        if len(block) < window // 2:
            break
        power = sum(value * value for value in block) / len(block)
        rms.append(math.sqrt(power))
    if not rms:
        return SpeechMotion((), step_seconds)
    levels = sorted(rms)
    high = levels[int((len(levels) - 1) * 0.90)]
    low = levels[int((len(levels) - 1) * 0.12)]
    if high < 45:
        return SpeechMotion(tuple(0.0 for _ in rms), step_seconds)
    noise = max(40.0, min(high * 0.18, low * 1.5))
    scale = max(100.0, high * 0.72 - noise)
    smoothed = 0.0
    envelope = []
    for volume in rms:
        instant = max(0.0, min(1.0, (volume-noise) / scale))
        # Fast mouth opening, modest damping between syllables and clean silence.
        alpha = 0.70 if instant > smoothed else 0.60
        smoothed = alpha * instant + (1-alpha) * smoothed
        envelope.append(0.0 if smoothed < 0.06 else round(smoothed, 4))
    return SpeechMotion(tuple(envelope), step_seconds)


def analyze_speech_audio(audio: Path) -> SpeechMotion:
    """Decode existing TTS audio to 8kHz mono PCM using the installed FFmpeg."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-i", str(audio),
             "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "pipe:1"],
            capture_output=True, check=False, timeout=90,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Impossible de lire la voix pour animer la bouche.") from exc
    if result.returncode or not result.stdout:
        raise RuntimeError("Analyse audio impossible : " +
                           result.stderr.decode("utf-8", errors="replace")[-300:])
    return speech_motion_from_pcm(result.stdout)
