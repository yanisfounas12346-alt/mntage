"""Decision bridge for a ChatGPT UI controller after each finished optimization.

This script does not click the browser. It returns a machine-readable JSON
action. A separate GUI controller must wait for a genuinely completed response.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from contextlib import redirect_stdout
import sys

from tools import checkpoint as gate


CONTINUE_PROMPT = (
    "CONTINUE MNTAGE : choisis UN défaut prioritaire, améliore le code sur GitHub, "
    "ajoute ou adapte les tests, et donne le commit. Ne modifie pas les voix ni "
    "la validation TikTok. Pas de dépenses IA payantes sans autorisation."
)


def decide(completed: int, *, pull: bool = True) -> dict:
    """After optimization N, return CONTINUE or REPAIR; REPAIR blocks progress.

    A repair message must not increment the optimization counter.
    """
    if completed < 0:
        raise ValueError("Le nombre de demandes terminées doit être positif.")
    if completed == 0 or completed % 10:
        previous_gate = (completed // 10) * 10
        if previous_gate:
            report = gate.OUT / f"cycle_{previous_gate:04d}.json"
            if report.is_file():
                try:
                    status = json.loads(report.read_text(encoding="utf-8"))["status"]
                except (OSError, ValueError, KeyError):
                    status = "FAIL"
                if status != "PASS":
                    prompt_path = gate.OUT / f"cycle_{previous_gate:04d}_next_prompt.txt"
                    text = (prompt_path.read_text(encoding="utf-8")
                            if prompt_path.is_file() else
                            "STOP : checkpoint précédent non validé. Corriger et relancer.")
                    return {"status": "REPAIR", "iteration": previous_gate,
                            "prompt": text, "allow_new_optimization": False}
        return {"status": "CONTINUE", "iteration": completed,
                "prompt": CONTINUE_PROMPT, "allow_new_optimization": True}

    # Keep stdout strictly JSON so the browser controller can parse it.
    with redirect_stdout(sys.stderr):
        ok = gate.checkpoint(completed, pull=pull)
    prompt_path = gate.OUT / f"cycle_{completed:04d}_next_prompt.txt"
    prompt = prompt_path.read_text(encoding="utf-8")
    return {
        "status": "CONTINUE" if ok else "REPAIR",
        "iteration": completed,
        "prompt": prompt,
        "allow_new_optimization": ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Décide de la prochaine requête")
    parser.add_argument("--completed", required=True, type=int,
                        help="Demandes d'optimisation terminées depuis le dernier cycle")
    parser.add_argument("--no-pull", action="store_true")
    args = parser.parse_args()
    decision = decide(args.completed, pull=not args.no_pull)
    print(json.dumps(decision, ensure_ascii=False))
    # A controller uses status/allow_new_optimization, not the process exit code.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
