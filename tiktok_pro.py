"""Offline TikTok production planning. No API calls or paid services."""
from __future__ import annotations
import re

MONTHLY_BUDGET_EUR = 30.0
TARGET_MIN_SECONDS = 65
TARGET_MAX_SECONDS = 90
WORDS_PER_SECOND = 2.5

def audit_script(script: str, keyword: str = "") -> dict:
    words = re.findall(r"\b[\wÀ-ÿ]+\b", script, flags=re.UNICODE)
    duration = len(words) / WORDS_PER_SECOND
    keyword = keyword.strip().casefold()
    return {
        "words": len(words),
        "estimated_seconds": round(duration, 1),
        "target_words": (round(TARGET_MIN_SECONDS * WORDS_PER_SECOND),
                         round(TARGET_MAX_SECONDS * WORDS_PER_SECOND)),
        "duration_ok": TARGET_MIN_SECONDS <= duration <= TARGET_MAX_SECONDS,
        "keyword_in_script": bool(keyword and keyword in script.casefold()),
        "hook": " ".join(words[:15]),
    }

def production_brief(topic: str, keyword: str, style: str = "documentaire cinématique") -> str:
    topic = topic.strip()
    keyword = keyword.strip()
    if not topic:
        raise ValueError("Indique un sujet avant de préparer le brief.")
    return (
        f"SUJET : {topic}\n"
        f"MOT-CLÉ PRINCIPAL : {keyword or topic}\n"
        f"STYLE VISUEL : {style}\n"
        "FORMAT : 9:16, 1080x1920, 65 à 90 secondes.\n"
        "STRUCTURE : 0-4s accroche factuelle ; 4-16s contexte ; "
        "16-62s explication progressive ; 62-75s conclusion.\n"
        "RÉDACTION : 163 à 225 mots environ ; faits vérifiés ; "
        "pas de promesse sensationnaliste trompeuse.\n"
        "VISUELS : illustrations originales cohérentes, cadrage vertical, "
        "aucun texte ni logo incrusté dans les images.\n"
        "SEO : mot-clé naturel dans la narration et la description ; "
        "3 à 5 hashtags pertinents ; vérifier la demande sur TikTok.\n"
        "DROITS : vérifier la licence commerciale des modèles et médias ; "
        "vérifier les règles TikTok avant publication.\n"
        "BUDGET : 30 EUR/mois maximum ; aucune dépense automatique.\n"
    )
