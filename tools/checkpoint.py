"""Local no-regression checkpoint for every tenth MNTAGE optimization.

Stdlib-only. Never overwrites files, resets branches, or automatically applies fixes.
Results and the next repair prompt are written to outputs/checkpoints/.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "checkpoints"
SOURCE_FILES = (
    "app.py",
    "video_factory.py",
    "motion_studio.py",
    "motion_director.py",
    "speech_motion.py",
    "tiktok_pro.py",
    "tools/checkpoint.py",
    "tools/next_request.py",
    "tools/session_handoff.py",
    "tools/pilot_3.py",
)


def _run(label: str, command: list[str], timeout: int) -> dict:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
        return {
            "step": label,
            "command": command,
            "ok": result.returncode == 0,
            "exit_code": result.returncode,
            "duration_seconds": round(time.monotonic() - started, 2),
            "output": (result.stdout + "\n" + result.stderr)[-18000:],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "step": label,
            "command": command,
            "ok": False,
            "exit_code": None,
            "duration_seconds": round(time.monotonic() - started, 2),
            "output": f"{type(exc).__name__}: {exc}",
        }


def _write_results(iteration: int, steps: list[dict], ok: bool) -> tuple[Path, Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    prefix = f"cycle_{iteration:04d}"
    report = OUT / f"{prefix}.json"
    prompt = OUT / f"{prefix}_next_prompt.txt"
    payload = {
        "iteration": iteration,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if ok else "FAIL",
        "python": sys.version,
        "repository": str(ROOT),
        "steps": steps,
    }
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if ok:
        text = (
            f"POINT DE CONTROLE {iteration}/100 : TOUS LES TESTS ONT REUSSI.\n"
            "Continue l'optimisation de MNTAGE avec une seule amélioration "
            "concrète et vérifiable par demande. Maintiens le budget IA "
            "sous contrôle. Ne change pas les voix et ne lance pas de validation "
            "TikTok. Respecte les tests et les fonctionnalités existantes.\n"
            "Au prochain multiple de 10, relance le checkpoint avant de continuer.\n"
        )
    else:
        failures = "\n\n".join(
            f"ÉTAPE : {item['step']}\n"
            f"Commande : {' '.join(item['command'])}\n"
            f"Sortie :\n{item['output'][-12000:]}"
            for item in steps if not item["ok"]
        )
        text = (
            f"STOP — POINT DE CONTROLE {iteration}/100 EN ECHEC.\n"
            "Ne commence PAS une nouvelle fonctionnalité. Lis les erreurs, "
            "corrige précisément le code sur le dépôt yanisfounas12346-alt/mntage, "
            "ajoute un test de non-régression adapté, puis fais relancer "
            f"'python tools/checkpoint.py --iteration {iteration}'.\n"
            "Ne passe pas à la demande suivante avant PASS. "
            "Les tests du PC Windows doivent être exécutés sur ce PC.\n\n"
            "IMPORTANT : relire et retirer toute donnée personnelle ou clé "
            "secrète avant de partager ce journal.\n\n" + failures
        )
    prompt.write_text(text, encoding="utf-8")
    return report, prompt


def checkpoint(iteration: int, *, pull: bool = True) -> bool:
    steps = []
    if pull:
        if not shutil.which("git"):
            steps.append({"step": "git disponible", "command": ["git"], "ok": False,
                          "exit_code": None, "duration_seconds": 0,
                          "output": "Git introuvable dans PATH."})
            _write_results(iteration, steps, False)
            return False
        # Do not risk a pull on locally modified tracked files.
        status = _run("git status", ["git", "status", "--porcelain", "--untracked-files=no"], 20)
        steps.append(status)
        if not status["ok"] or status["output"].strip():
            if status["ok"]:
                steps.append({"step": "répertoire propre", "command": ["git", "status"],
                              "ok": False, "exit_code": None, "duration_seconds": 0,
                              "output": "Fichiers suivis modifiés localement : sauvegarde-les avant git pull."})
            _write_results(iteration, steps, False)
            return False
        updated = _run("git pull --ff-only", ["git", "pull", "--ff-only"], 120)
        steps.append(updated)
        if not updated["ok"]:
            _write_results(iteration, steps, False)
            return False

    missing = [name for name in SOURCE_FILES if not (ROOT / name).is_file()]
    if missing:
        steps.append({"step": "sources attendues", "command": [],
                      "ok": False, "exit_code": None, "duration_seconds": 0,
                      "output": "Fichiers absents : " + ", ".join(missing)})
        _write_results(iteration, steps, False)
        return False

    compiled = _run(
        "syntaxe Python",
        [sys.executable, "-m", "py_compile", *SOURCE_FILES], 90,
    )
    steps.append(compiled)
    if not compiled["ok"]:
        _write_results(iteration, steps, False)
        return False

    for binary in ("ffmpeg", "ffprobe"):
        found = shutil.which(binary)
        steps.append({
            "step": f"{binary} disponible",
            "command": [binary, "-version"], "ok": found is not None,
            "exit_code": 0 if found else 1, "duration_seconds": 0,
            "output": found or f"{binary} absent du PATH. Tests vidéo non fiables.",
        })

    tests = _run(
        "tests unitaires et de non-régression",
        [sys.executable, "-m", "unittest", "discover", "-s", "tests",
         "-p", "test_*.py", "-v"], 1200,
    )
    steps.append(tests)
    ok = all(item["ok"] for item in steps)
    report, prompt = _write_results(iteration, steps, ok)
    print(f"\nCHECKPOINT {iteration} : {'PASS' if ok else 'FAIL'}")
    for item in steps:
        print(f"  {'OK' if item['ok'] else 'ECHEC'}  {item['step']}")
    print(f"Rapport : {report}")
    print(f"Instruction suivante : {prompt}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Checkpoint de non-régression MNTAGE")
    parser.add_argument("--iteration", type=int, required=True,
                        help="Numéro de la demande d'optimisation (10, 20, etc.)")
    parser.add_argument("--no-pull", action="store_true",
                        help="Ne pas télécharger les commits (tests potentiellement obsolètes)")
    parser.add_argument("--force", action="store_true",
                        help="Lancer le checkpoint même hors d'un multiple de 10")
    args = parser.parse_args()
    if args.iteration < 1:
        parser.error("--iteration doit être positif")
    if args.iteration % 10 and not args.force:
        print(f"Requête {args.iteration}: checkpoint au prochain multiple de 10.")
        return 0
    return 0 if checkpoint(args.iteration, pull=not args.no_pull) else 1


if __name__ == "__main__":
    raise SystemExit(main())
