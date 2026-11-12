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

def seo_pack(title: str, script: str, keyword: str = "", science: bool = False) -> str:
    """Produce an editable French publishing pack without inventing facts or trends."""
    title = re.sub(r"\s+", " ", title).strip()
    keyword = re.sub(r"\s+", " ", keyword).strip() or title
    if not title or not script.strip():
        raise ValueError("Titre et script requis pour le pack SEO.")
    # Use only script text for the description; no invented scientific claim.
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", script) if s.strip()]
    summary = " ".join(sentences[:2])
    if len(summary) > 190:
        summary = summary[:187].rsplit(" ", 1)[0] + "..."
    safe_title = title[:85].rstrip()
    terms = [t.lower() for t in re.findall(r"[\wÀ-ÿ]+", keyword, flags=re.UNICODE)
             if len(t) >= 4 and not t.isdigit()]
    hashtags = ["#ScienceWTF", "#Science", "#LeSaviezVous"] if science else ["#CultureG", "#LeSaviezVous", "#Decouverte"]
    for term in terms[:2]:
        tag = "#" + term[:24].capitalize()
        if tag.casefold() not in {t.casefold() for t in hashtags}:
            hashtags.append(tag)
    hashtags = hashtags[:5]
    audit = audit_script(script, keyword)
    notes = []
    if not audit["keyword_in_script"]:
        notes.append("- Ajouter naturellement le mot-clé à la narration si pertinent.")
    if not audit["duration_ok"]:
        notes.append("- Ajuster la durée du script avant publication.")
    notes.extend([
        "- Vérifier chaque affirmation scientifique et les droits des images.",
        "- Vérifier manuellement les tendances et hashtags : aucune donnée TikTok temps réel utilisée.",
        "- Adapter le titre et la description après visionnage du MP4 final.",
    ])
    return (
        "PACK DE PUBLICATION — BROUILLON À RELIRE\n\n"
        f"TITRE\n{safe_title}\n\n"
        f"MOT-CLÉ CIBLE\n{keyword}\n\n"
        f"DESCRIPTION\n{summary}\n"
        f"Une découverte étonnante expliquée simplement.\n\n"
        f"HASHTAGS\n{' '.join(hashtags)}\n\n"
        f"COMMENTAIRE ÉPINGLÉ (SUGGESTION)\n"
        "Quel sujet scientifique voudrais-tu voir dans le prochain épisode ?\n\n"
        "VÉRIFICATIONS AVANT PUBLICATION\n" + "\n".join(notes) + "\n"
    )
