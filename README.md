# mntage — AI Video Factory (MVP)

Studio léger pour générer une voix française, assembler des images en vidéo verticale 1080×1920 avec FFmpeg, puis téléverser manuellement ou via OAuth sur YouTube.

## Installation

1. Installer Python 3.11+ et [FFmpeg](https://ffmpeg.org/download.html) et rendre `ffmpeg` accessible dans le PATH.
2. Cloner le dépôt, puis :

```bash
python -m venv .venv
# Windows PowerShell :
.venv\Scripts\Activate.ps1
# Linux/macOS : source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Utilisation

1. Saisir un titre et un script, ajouter des images personnelles ou sous licence compatible.
2. Générer une voix française (Edge TTS, service en ligne) et un MP4 vertical.
3. Vérifier le résultat puis utiliser l'export manuel ou `python youtube_upload.py outputs/<nom>.mp4 --title "Titre"`.

Pour l'upload API : créer un projet Google Cloud, activer **YouTube Data API v3**, configurer l'écran de consentement OAuth, créer un identifiant OAuth **application de bureau**, puis enregistrer son JSON en `client_secret.json` à la racine. Le script utilise `youtube.upload`, envoie en **privé** par défaut et mémorise le jeton localement. Certains projets API non audités peuvent être limités à la publication privée. Ne jamais committer les secrets.

## Limites

Ce MVP n'invente pas de scènes vidéo : il anime des images fournies avec un léger zoom, génère la narration et assemble les scènes. La génération d'images/vidéos par IA (ComfyUI/cloud), les sous-titres synchronisés, la planification et les métriques de monétisation restent à intégrer. Edge TTS nécessite Internet ; FFmpeg doit être installé séparément. Vérifier les droits des images, de l'audio et des vidéos avant publication. Aucun revenu n'est garanti.
