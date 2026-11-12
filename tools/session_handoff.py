"""Persist optimizer progress and create a ChatGPT new-thread handoff prompt.

This module neither controls the browser nor assumes a ChatGPT response is complete.
The local UI controller must explicitly mark completion after verifying the result.
"""
from __future__ import annotations
import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import uuid
from tools import checkpoint as gate

ROOT=Path(__file__).resolve().parents[1]
DIRECTORY=ROOT/"outputs"/"automation"
STATE_FILE=DIRECTORY/"session_state.json"
HANDOFF_FILE=DIRECTORY/"resume_prompt.txt"
REPO_URL="https://github.com/yanisfounas12346-alt/mntage"

CONTEXT=(
    "Projet MNTAGE, application Streamlit sur Windows : vidéos 2D Science WTF "
    "France 1080x1920 originales, dynamiques et professionnelles.\n"
    "Dépôt : "+REPO_URL+"\n"
    "Machine : Ryzen 5 7520U, Radeon 610M, 16 Go, Python 3.11 et FFmpeg.\n"
    "Moteur actuel : pilote miroir, six cadrages, gestuelle et bouche synchronisée "
    "approximativement sur l'audio, SEO local. Les nouveaux sujets ne sont pas "
    "encore généralisés. Produit professionnel et rentabilité non démontrés.\n"
    "Contraintes : maximum 30 EUR/mois, aucun appel payant sans accord, "
    "ne pas modifier les voix ni faire de validation TikTok.\n"
    "Une amélioration à la fois ; tests de non-régression obligatoires toutes "
    "les 10 demandes, avec réparation avant de reprendre.\n"
)

def now():
    return datetime.now(timezone.utc).isoformat()

def initial():
    return {"version":1,"completed":0,"goal":100,"pending":None,
            "last_summary":"Pilote miroir, qualité pro non démontrée.",
            "last_commit":"","next_focus":"Animation et généralisation des sujets.",
            "failure":"","history":[],"updated":now()}

def load(path=None):
    path=path or STATE_FILE
    if not path.exists():
        return initial()
    s=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(s,dict) or s.get("version")!=1 or not isinstance(s.get("completed"),int) or s["completed"]<0:
        raise ValueError("État corrompu. Ne pas réinitialiser le compteur.")
    return s

def save(s,path=None):
    path=path or STATE_FILE
    path.parent.mkdir(parents=True,exist_ok=True)
    s["updated"]=now()
    tmp=path.with_name(path.name+"."+uuid.uuid4().hex+".tmp")
    try:
        tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        os.replace(tmp,path)
    finally:
        tmp.unlink(missing_ok=True)
    # Keep the handoff prompt continuously up to date, even if the UI
    # conversation reaches its limit without an explicit "resume" command.
    if path == STATE_FILE:
        HANDOFF_FILE.parent.mkdir(parents=True, exist_ok=True)
        prompt_tmp = HANDOFF_FILE.with_name(
            HANDOFF_FILE.name + "." + uuid.uuid4().hex + ".tmp")
        try:
            prompt_tmp.write_text(make_handoff(s), encoding="utf-8")
            os.replace(prompt_tmp, HANDOFF_FILE)
        finally:
            prompt_tmp.unlink(missing_ok=True)

def gate_status(n):
    path=gate.OUT/f"cycle_{n:04d}.json"
    if not path.exists():
        return "MISSING"
    try:
        report=json.loads(path.read_text(encoding="utf-8"))
        if report.get("iteration")==n and report.get("status")=="PASS":
            return "PASS"
    except (ValueError,OSError):
        pass
    return "FAIL"

def begin(s):
    """Create a pending request; never send an unconfirmed duplicate."""
    if s.get("pending"):
        p=s["pending"]
        return {"status":"PENDING_REVIEW","allow_send":False,
                "iteration":p["iteration"],"request_id":p["request_id"],
                "prompt":"Une demande est encore en cours ou non enregistrée. "
                         "Vérifier le dernier message et les commits avant toute relance."}
    n=s["completed"]
    if s.get("failure"):
        return {"status":"REPAIR","allow_send":False,"iteration":n,
                "prompt":"STOP : "+s["failure"]+" ; réparer puis relancer le contrôle."}
    if n>0 and n%10==0:
        status=gate_status(n)
        if status!="PASS":
            prompt=gate.OUT/f"cycle_{n:04d}_next_prompt.txt"
            detail=prompt.read_text(encoding="utf-8") if prompt.exists() else (
                f"Checkpoint {n} absent/échoué. Exécuter le contrôle et réparer.")
            return {"status":"CHECKPOINT_REQUIRED" if status=="MISSING" else "REPAIR",
                    "allow_send":False,"iteration":n,"prompt":detail}
    ident=uuid.uuid4().hex
    prompt=(
        f"OPTIMISATION MNTAGE {n+1}/{s['goal']} — dépôt https://github.com/yanisfounas12346-alt/mntage : améliorer un défaut prioritaire "
        "dans le dépôt GitHub, avec preuve et test ciblé. Donner le commit, "
        "les résultats et les limites. Ne pas modifier les voix ni valider TikTok. "
        "Aucun appel IA payant sans accord.\n"
        f"Dernier résultat : {s.get('last_summary','')}\n"
        f"Prochain objectif : {s.get('next_focus','')}"
    )
    s["pending"]={"request_id":ident,"iteration":n+1,"prompt":prompt,"at":now()}
    save(s)
    return {"status":"SEND","allow_send":True,"iteration":n+1,
            "request_id":ident,"prompt":prompt}

def complete(s,request_id,summary,commit="",focus="",result="partial"):
    p=s.get("pending")
    if not p or p["request_id"]!=request_id:
        raise ValueError("ID non reconnu : compteur inchangé.")
    if not summary.strip() or result not in ("validated","partial","failed"):
        raise ValueError("Résumé et statut requis.")
    if p["iteration"]!=s["completed"]+1:
        raise ValueError("Compteur incohérent.")
    entry={"number":p["iteration"],"when":now(),"summary":summary[:1000],
           "commit":commit[:80],"result":result}
    s["completed"]+=1
    s["history"]=(s["history"]+[entry])[-100:]
    s["last_summary"]=entry["summary"]
    if commit:
        s["last_commit"]=commit[:80]
    if focus:
        s["next_focus"]=focus[:400]
    if result=="failed":
        s["failure"]=summary[:400]
    s["pending"]=None
    save(s)
    n=s["completed"]
    return {"status":"CHECKPOINT_REQUIRED" if n%10==0 else
            ("REPAIR" if result=="failed" else "RECORDED"),
            "completed":n}

def checkpoint(s,pull=True,force=False):
    n=s["completed"]
    if n<1 or (n%10 and not force):
        raise ValueError("Checkpoint uniquement aux multiples de 10, sauf --force.")
    # Keep stdout machine-readable JSON for a graphical UI controller.
    with redirect_stdout(sys.stderr):
        ok=gate.checkpoint(n,pull=pull)
    if ok:
        s["failure"]=""
    elif not s.get("failure"):
        s["failure"]=f"Checkpoint {n} en échec"
    save(s)
    return {"status":"PASS" if ok else "FAIL","iteration":n,
            "report":str(gate.OUT/f"cycle_{n:04d}.json")}

def make_handoff(s):
    n=s["completed"]
    p=s.get("pending")
    if p:
        phase=(f"REQUÊTE {p['iteration']} EN COURS, ID {p['request_id']}. "
               "Ne PAS réenvoyer ni incrémenter sans vérification.")
    elif s.get("failure"):
        phase="BLOCAGE : "+s["failure"]+". Corriger avant toute nouvelle optimisation."
    elif n>0 and n%10==0:
        phase=f"Checkpoint {n} : {gate_status(n)}. Doit être PASS avant la suite."
    else:
        phase=f"Prêt pour la requête {n+1}."
    recent="\n".join(
        f"- #{e['number']}: {e['summary'][:220]} "
        f"({e['result']}, commit {e.get('commit') or 'non indiqué'})"
        for e in s.get("history",[])[-5:]
    ) or "Aucune optimisation enregistrée par ce contrôleur."
    return (
        "REPRISE MNTAGE DANS UN NOUVEAU FIL CHATGPT\n\n"
        "Ce message est créé par un programme local. L'ancien fil n'est "
        "pas automatiquement accessible dans celui-ci. Ne rien inventer.\n\n"
        +CONTEXT+"\n"
        f"DEMANDES CONFIRMÉES : {n}/{s['goal']}.\n"
        f"ÉTAT : {phase}\n"
        f"DERNIER RÉSULTAT : {s.get('last_summary','')}\n"
        f"DERNIER COMMIT : {s.get('last_commit') or 'non indiqué'}\n"
        f"PRIORITÉ SUIVANTE : {s.get('next_focus','')}\n"
        "HISTORIQUE RÉCENT :\n"+recent+"\n\n"
        "Avant toute modification : vérifier les vrais fichiers sur GitHub, "
        "README.md, QUALITY_GATE_100.md et les tests. Conserver les restrictions "
        "de dépenses, les voix et la pause de validation TikTok. Ne pas compter "
        "une demande tant que le résultat n'est pas explicitement confirmé. "
        "Respecter tout checkpoint non validé.\n"
    )

def main():
    p=argparse.ArgumentParser(description="Sauvegarde/reprise entre fils ChatGPT")
    sub=p.add_subparsers(dest="action",required=True)
    for a in ("init","status","begin","resume"):
        sub.add_parser(a)
    done=sub.add_parser("complete")
    done.add_argument("--request-id",required=True)
    done.add_argument("--summary",required=True)
    done.add_argument("--commit",default="")
    done.add_argument("--focus",default="")
    done.add_argument("--result",choices=("validated","partial","failed"),
                      default="partial")
    check=sub.add_parser("checkpoint")
    check.add_argument("--no-pull",action="store_true")
    check.add_argument("--force",action="store_true")
    args=p.parse_args()
    s=load()
    if args.action=="init":
        if not STATE_FILE.exists():
            save(s)
        output={"status":"READY","completed":s["completed"],
                "state_file":str(STATE_FILE)}
    elif args.action=="status":
        output=s
    elif args.action=="begin":
        output=begin(s)
    elif args.action=="complete":
        output=complete(s,args.request_id,args.summary,args.commit,
                        args.focus,args.result)
    elif args.action=="checkpoint":
        output=checkpoint(s,pull=not args.no_pull,force=args.force)
    else:
        HANDOFF_FILE.parent.mkdir(parents=True,exist_ok=True)
        text=make_handoff(s)
        HANDOFF_FILE.write_text(text,encoding="utf-8")
        print(text)
        print("Sauvegardé : "+str(HANDOFF_FILE),file=sys.stderr)
        return 0
    print(json.dumps(output,ensure_ascii=False,indent=2))
    return 1 if output.get("status")=="FAIL" else 0

if __name__=="__main__":
    raise SystemExit(main())
