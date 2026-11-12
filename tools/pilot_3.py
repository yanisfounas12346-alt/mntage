"""MNTAGE three-request supervised ChatGPT optimization pilot.

This UI prepares prompts, opens ChatGPT on user request, and requires explicit
human confirmation of the output. It does NOT scrape ChatGPT, click its send
button, infer that generation has finished or bypass usage limits.

Start with: python -m tools.pilot_3
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import webbrowser

from tools import session_handoff as handoff


PILOT_FILE = handoff.DIRECTORY / "pilot_3.json"
MAX_REQUESTS = 3
CHAT_URL = "https://chatgpt.com/"
SHA_PATTERN = re.compile(r"^[a-fA-F0-9]{7,40}$")


def _save_metadata(metadata: dict) -> None:
    PILOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Atomic save with no external dependency.
    target = PILOT_FILE.with_suffix(".tmp")
    target.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    target.replace(PILOT_FILE)


def _verify_remote_commit(commit: str) -> None:
    """A 'validated' change must exist on the fetched GitHub main branch."""
    if not SHA_PATTERN.fullmatch(commit.strip()):
        raise ValueError("SHA Git invalide (7 à 40 chiffres hexadécimaux).")
    commands = [
        ["git", "fetch", "--quiet", "origin", "main"],
        ["git", "rev-parse", "--verify", f"{commit.strip()}^{{commit}}"],
        ["git", "merge-base", "--is-ancestor", commit.strip(), "origin/main"],
    ]
    for cmd in commands:
        try:
            result = subprocess.run(
                cmd, cwd=handoff.ROOT, capture_output=True, text=True, timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("Impossible de vérifier le commit GitHub.") from exc
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()[-350:]
            raise ValueError(
                "Commit absent ou non présent dans origin/main. "
                "Vérifie le SHA et le dépôt. " + detail
            )


class PilotSession:
    """A restart-safe limit of three confirmed optimization requests."""

    def __init__(self):
        state = handoff.load()
        if PILOT_FILE.is_file():
            try:
                metadata = json.loads(PILOT_FILE.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ValueError("Fichier du pilote corrompu : ne pas réinitialiser.") from exc
            if (metadata.get("version") != 1 or
                not isinstance(metadata.get("baseline"), int) or
                metadata["baseline"] > state["completed"] or
                metadata["baseline"] < 0 or metadata.get("limit") != MAX_REQUESTS):
                raise ValueError("État incohérent du pilote : vérification manuelle.")
        else:
            if state.get("pending"):
                raise ValueError(
                    "Une demande est déjà en cours avant l'essai : "
                    "termine-la dans session_handoff avant de démarrer le pilote."
                )
            metadata = {"version": 1, "baseline": state["completed"],
                        "limit": MAX_REQUESTS, "created": handoff.now()}
            _save_metadata(metadata)
        self.metadata = metadata

    def progress(self) -> tuple[int, int]:
        count = handoff.load()["completed"] - self.metadata["baseline"]
        return count, MAX_REQUESTS

    def prepare(self) -> dict:
        completed, limit = self.progress()
        if completed >= limit:
            return {"status": "DONE", "allow_send": False,
                    "prompt": "Essai de 3 requêtes terminé. Évaluer les résultats avant toute extension."}
        return handoff.begin(handoff.load())

    def confirm(self, request_id: str, summary: str, commit: str, *,
                result: str = "validated", verifier=None) -> dict:
        completed, limit = self.progress()
        if completed >= limit:
            raise ValueError("La limite de 3 optimisations est atteinte.")
        if result == "validated":
            # Reusing one old commit for several prompts is not evidence
            # of several improvements.
            prior = {
                str(entry.get("commit", "")).lower()
                for entry in handoff.load().get("history", [])
                if entry.get("commit")
            }
            if commit.strip().lower() in prior:
                raise ValueError("Ce commit a déjà été comptabilisé. Il faut une nouvelle correction.")
            (verifier or _verify_remote_commit)(commit)
        elif result not in ("partial", "failed"):
            raise ValueError("Statut inconnu.")
        return handoff.complete(
            handoff.load(), request_id, summary, commit=commit, result=result
        )

    def checkpoint(self) -> dict:
        return handoff.checkpoint(handoff.load())


def run_gui() -> None:
    # Import only here so the state machine can be unit-tested headlessly.
    import tkinter as tk
    from tkinter import messagebox, scrolledtext, ttk

    pilot = PilotSession()
    root = tk.Tk()
    root.title("MNTAGE — Pilote supervisé de 3 optimisations")
    root.geometry("820x690")
    root.minsize(650, 580)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(3, weight=1)

    headline = tk.StringVar()
    hint = tk.StringVar(value="Prépare une demande, colle-la dans ChatGPT, puis vérifie le résultat.")
    title = ttk.Label(root, textvariable=headline, font=("Segoe UI", 15, "bold"))
    title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 5))
    ttk.Label(root, textvariable=hint, wraplength=770).grid(
        row=1, column=0, sticky="w", padx=16, pady=4)
    buttons = ttk.Frame(root)
    buttons.grid(row=2, column=0, sticky="w", padx=16, pady=10)

    prompt_box = scrolledtext.ScrolledText(root, wrap="word", height=13)
    prompt_box.grid(row=3, column=0, sticky="nsew", padx=16, pady=8)

    fields = ttk.Frame(root)
    fields.grid(row=4, column=0, sticky="ew", padx=16, pady=8)
    fields.columnconfigure(1, weight=1)
    ttk.Label(fields, text="Résumé vérifié :").grid(row=0, column=0, sticky="nw", pady=4)
    summary_widget = tk.Text(fields, height=3, wrap="word")
    summary_widget.grid(row=0, column=1, sticky="ew", padx=8, pady=4)
    ttk.Label(fields, text="Commit GitHub :").grid(row=1, column=0, sticky="w")
    commit_var = tk.StringVar()
    ttk.Entry(fields, textvariable=commit_var).grid(
        row=1, column=1, sticky="ew", padx=8, pady=4)
    ttk.Label(fields, text="Résultat :").grid(row=2, column=0, sticky="w")
    result_var = tk.StringVar(value="validated")
    ttk.Combobox(fields, values=("validated", "partial", "failed"),
                 state="readonly", textvariable=result_var).grid(
        row=2, column=1, sticky="w", padx=8)

    active_id: str | None = None

    def copy_text(text: str) -> None:
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()  # ensure clipboard is available after interaction

    def show_prompt(text: str) -> None:
        prompt_box.configure(state="normal")
        prompt_box.delete("1.0", "end")
        prompt_box.insert("1.0", text)
        prompt_box.configure(state="disabled")

    def refresh() -> None:
        nonlocal active_id
        count, limit = pilot.progress()
        state = handoff.load()
        active = state.get("pending")
        active_id = active["request_id"] if active else None
        headline.set(f"Optimisations confirmées : {count}/{limit}")
        if active:
            hint.set(f"Requête #{active['iteration']} en cours ou à vérifier. "
                     "Ne la renvoie pas une deuxième fois.")
            show_prompt(active["prompt"])
        elif count >= limit:
            hint.set("Essai terminé. Vérifie la qualité des modifications.")
        elif state.get("failure"):
            hint.set("STOP : correction obligatoire avant une nouvelle optimisation.")
        elif count and state["completed"] % 10 == 0 and handoff.gate_status(
                state["completed"]) != "PASS":
            hint.set("STOP : checkpoint requis. Exécute les tests et répare.")
        else:
            hint.set("Prêt. Clique sur Préparer, puis colle le texte dans ChatGPT.")

    def prepare() -> None:
        try:
            data = pilot.prepare()
            if data["status"] == "SEND":
                copy_text(data["prompt"])
                hint.set("Prompt copié ! Colle-le dans ChatGPT et envoie-le toi-même.")
            else:
                messagebox.showwarning(data["status"], data["prompt"])
            refresh()
        except Exception as exc:
            messagebox.showerror("Préparation impossible", str(exc))

    def finish() -> None:
        if not active_id:
            messagebox.showinfo("Aucune demande", "Prépare d'abord une requête.")
            return
        summary = summary_widget.get("1.0", "end").strip()
        if not summary:
            messagebox.showerror("Résumé manquant", "Vérifie et décris le résultat.")
            return
        if not messagebox.askyesno(
            "Confirmer le travail effectué",
            "As-tu réellement vu la réponse terminée et vérifié le résultat ?\n"
            "Un résultat 'validated' exige un commit présent sur GitHub."
        ):
            return
        try:
            result = pilot.confirm(active_id, summary, commit_var.get().strip(),
                                   result=result_var.get())
            summary_widget.delete("1.0", "end")
            commit_var.set("")
            refresh()
            if result["status"] == "CHECKPOINT_REQUIRED":
                messagebox.showinfo(
                    "Checkpoint requis",
                    "Arrêt obligatoire à la 10e demande : lance les tests."
                )
        except Exception as exc:
            messagebox.showerror("Confirmation refusée", str(exc))

    def resume() -> None:
        text = handoff.make_handoff(handoff.load())
        handoff.HANDOFF_FILE.parent.mkdir(parents=True, exist_ok=True)
        handoff.HANDOFF_FILE.write_text(text, encoding="utf-8")
        copy_text(text)
        hint.set("Message de reprise copié. Ouvre un nouveau fil et colle-le.")

    def checkpoint() -> None:
        try:
            result = pilot.checkpoint()
            if result["status"] == "PASS":
                messagebox.showinfo("Checkpoint", "Tous les tests passent.")
            else:
                messagebox.showerror("Checkpoint", "Échec : vérifie le rapport et corrige.")
            refresh()
        except Exception as exc:
            messagebox.showerror("Checkpoint impossible", str(exc))

    ttk.Button(buttons, text="1. Préparer et copier", command=prepare).pack(side="left", padx=3)
    ttk.Button(buttons, text="Ouvrir ChatGPT", command=lambda: webbrowser.open(CHAT_URL)).pack(
        side="left", padx=3)
    ttk.Button(buttons, text="2. Valider le résultat", command=finish).pack(
        side="left", padx=3)
    ttk.Button(buttons, text="Tests", command=checkpoint).pack(side="left", padx=3)
    ttk.Button(buttons, text="Copier reprise", command=resume).pack(side="left", padx=3)
    ttk.Label(root, text="Sécurité : aucun clic automatique, aucune lecture cachée du chat, "
              "3 demandes maximum.", wraplength=770).grid(
        row=5, column=0, sticky="w", padx=16, pady=(3, 14))
    refresh()
    root.mainloop()


if __name__ == "__main__":
    try:
        run_gui()
    except Exception as exc:
        print(f"Pilote MNTAGE indisponible : {exc}", file=sys.stderr)
        raise SystemExit(1)
