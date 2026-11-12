"""Optional paid fal FLUX image generation with a local conservative spend guard."""
from __future__ import annotations
import io
import json
import math
import os
import sqlite3
import threading
from contextlib import contextmanager
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

MODEL = "fal-ai/flux/schnell"
ENDPOINT = "https://fal.run/" + MODEL
MONTHLY_CAP_EUR = 30.0
# Provider quotes USD; conservative EUR planning estimate, NOT a currency conversion.
USD_PER_MEGAPIXEL = 0.003
EUR_BUFFER_PER_USD = 1.25
WIDTH, HEIGHT = 576, 1024
_LOCK = threading.Lock()

def configured() -> bool:
    return bool(os.environ.get("FAL_KEY", "").strip())

def estimate_eur(count: int) -> float:
    if not 1 <= count <= 12:
        raise ValueError("Choisis entre 1 et 12 images.")
    mp = math.ceil(WIDTH * HEIGHT / 1_000_000)
    return round(count * mp * USD_PER_MEGAPIXEL * EUR_BUFFER_PER_USD, 4)

def _db_path() -> Path:
    return Path(os.environ.get("MNTAGE_CLOUD_LEDGER", "mntage_cloud_spend.sqlite3"))

@contextmanager
def _connect():
    conn = sqlite3.connect(_db_path(), timeout=30)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS spend (id INTEGER PRIMARY KEY, month TEXT NOT NULL, eur REAL NOT NULL, status TEXT NOT NULL)")
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
    finally:
        conn.close()

def spent_eur() -> float:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    with _connect() as conn:
        return round(conn.execute("SELECT COALESCE(SUM(eur),0) FROM spend WHERE month=? AND status IN ('reserved','submitted')", (month,)).fetchone()[0], 4)

def _reserve(count: int, cap_eur: float) -> tuple[int, float]:
    if not 0 < cap_eur <= MONTHLY_CAP_EUR:
        raise ValueError("Plafond mensuel invalide.")
    estimate = estimate_eur(count)
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    with _LOCK:
        with _connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            total = conn.execute("SELECT COALESCE(SUM(eur),0) FROM spend WHERE month=? AND status IN ('reserved','submitted')", (month,)).fetchone()[0]
            if total + estimate > cap_eur:
                raise RuntimeError("Plafond mensuel local atteint : génération bloquée.")
            cur = conn.execute("INSERT INTO spend(month,eur,status) VALUES(?,?,'reserved')", (month,estimate))
            return cur.lastrowid, estimate

def generate_cloud_images(prompts: list[str], *, confirmed: bool, cap_eur: float = 15.0) -> list[bytes]:
    if not confirmed:
        raise PermissionError("Confirmation explicite nécessaire avant tout appel payant.")
    if not configured():
        raise RuntimeError("Configure la variable FAL_KEY sur ton PC.")
    if not 1 <= len(prompts) <= 12:
        raise ValueError("Entre 1 et 12 scènes sont nécessaires.")
    reservation, _ = _reserve(len(prompts), cap_eur)
    submitted = False
    try:
        images = []
        for prompt in prompts:
            payload = json.dumps({"prompt": prompt[:1200], "image_size": {"width": WIDTH,"height": HEIGHT}, "num_images": 1, "num_inference_steps": 4, "output_format": "jpeg"}).encode()
            req = urllib.request.Request(ENDPOINT, data=payload, headers={"Authorization": "Key " + os.environ["FAL_KEY"], "Content-Type": "application/json"}, method="POST")
            # Mark submitted before the first network request: failures may still be billed.
            if not submitted:
                with _connect() as conn:
                    conn.execute("UPDATE spend SET status='submitted' WHERE id=?", (reservation,))
                submitted = True
            with urllib.request.urlopen(req, timeout=180) as response:
                result = json.load(response)
            url = result["images"][0]["url"]
            if not url.startswith("https://") or not (url.split("/")[2].endswith(".fal.media") or url.split("/")[2] == "fal.media"):
                raise RuntimeError("URL d'image inattendue reçue du fournisseur.")
            with urllib.request.urlopen(url, timeout=90) as response:
                raw = response.read(15_000_001)
            if len(raw) > 15_000_000:
                raise RuntimeError("Image cloud trop volumineuse.")
            with Image.open(io.BytesIO(raw)) as image:
                image.verify()
            images.append(raw)
        return images
    except Exception:
        if not submitted:
            with _connect() as conn:
                conn.execute("UPDATE spend SET status='cancelled' WHERE id=?", (reservation,))
        raise
