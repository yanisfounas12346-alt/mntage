# mntage — script vers vidéo, sans abonnement GPU

Interface Streamlit : écris un titre et un script, puis génère un MP4 vertical avec voix française. **Mode Éco** : images typographiques créées par Pillow, narration Edge TTS (service en ligne sans clé API) et montage FFmpeg. Aucune carte graphique dédiée requise.

## Installation Windows PowerShell

Installer Python 3.11+ et Git, puis FFmpeg :

```powershell
winget install --id Gyan.FFmpeg -e
```

Ferme puis rouvre PowerShell, et vérifie `ffmpeg -version` et `ffprobe -version`.

```powershell
cd $HOME
git clone https://github.com/yanisfounas12346-alt/mntage.git
cd mntage
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Ouvre http://localhost:8501.

### Mise à jour

```powershell
cd $HOME\mntage
git pull
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Option : images IA locales sans GPU cloud

Le moteur [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) est **facultatif**. Le mode Éco fonctionne sans lui. Pour activer le mode IA :

1. Télécharge un binaire Windows compatible **CPU** depuis les [releases officielles](https://github.com/leejet/stable-diffusion.cpp/releases), puis extrais-le. Trouve le fichier `sd-cli.exe`.
2. Télécharge légalement un modèle compatible, par exemple SD 1.5 au format `.safetensors`, depuis une source officielle et vérifie sa licence commerciale.
3. Configure les chemins vers les fichiers téléchargés :

```powershell
$env:MNTAGE_SD_CLI = "C:\chemin\vers\sd-cli.exe"
$env:MNTAGE_SD_MODEL = "C:\chemin\vers\modele.safetensors"
cd $HOME\mntage
.\.venv\Scripts\python.exe -m streamlit run app.py
```

L'interface affichera « IA locale ». Ce mode lance **au maximum six scènes**, en 512×512, avec 12 étapes, et peut être **très lent sur CPU**. Aucun téléchargement de modèle n'est lancé automatiquement. Si le moteur échoue, sélectionne le mode Éco.

Le support Vulkan AMD dépend du binaire, du pilote et du modèle ; le mode intégré utilise volontairement le CPU pour la compatibilité. Il ne génère **pas** de clips vidéo IA : il crée des images que FFmpeg anime.

## Projets de référence

- [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) : architecture de production, sous-titres, médias, génération en lots (fonctionnalités à intégrer progressivement, non incluses ici).
- [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) : moteur d'images IA local.
- [FFmpeg](https://github.com/FFmpeg/FFmpeg) : encodage et montage.
- [edge-tts](https://github.com/rany2/edge-tts) : synthèse vocale en ligne sans clé API.

**Limites :** pas encore de sous-titres, musique, publication automatique, génération vidéo cinématique, ou tests de bout en bout validés. La publication YouTube privée reste disponible séparément via `youtube_upload.py` avec OAuth. Vérifie les droits des voix, images et modèles avant monétisation.

## Sous-titres et musique (nouveau)

Dans Streamlit, coche **Ajouter des sous-titres automatiques** pour incruster des sous-titres et exporter aussi un fichier SRT. Le minutage est estimé, et non aligné mot par mot. FFmpeg doit être compilé avec le filtre `subtitles` (libass) ; vérifie avec `ffmpeg -filters | findstr subtitles`. Tu peux importer une musique MP3 dont tu possèdes les droits ; elle est mixée à volume réduit avec la narration. Aucun catalogue musical ni téléchargement automatique n'est inclus.

## Publication

`youtube_upload.py` reste une commande distincte, avec configuration OAuth Google Cloud. Il n'y a pas de publication automatique sans validation dans l'interface.

## Studio v0.3 : file, médias et statistiques

- Onglet **Créer** : script seul, visuels automatiques, narration, sous-titres estimés et musique MP3 personnelle facultative.
- Onglet **File & historique** : ajouter des scripts, puis cliquer sur **Traiter la prochaine vidéo**. Les tâches sont stockées dans `outputs/mntage.sqlite3` et exécutées **manuellement**, une par une. Les fichiers musicaux et images importées ne sont pas stockés dans la file. Une tâche interrompue peut rester au statut `running` ; aucun mécanisme de reprise automatique n'est encore inclus.
- Onglet **Résultats** : saisie manuelle des vues, revenus et coûts. Il ne s'agit pas de statistiques YouTube synchronisées.
- **YouTube** : après une génération via la file, configure `client_secret.json` OAuth Desktop dans le dossier du projet, confirme l'envoi et clique sur **Envoyer sur YouTube en privé**. L'API YouTube Data et l'écran de consentement doivent être configurés dans Google Cloud. Aucune publication publique automatique.
- **Pexels** : option facultative avec clé API gratuite (quotas et conditions applicables). Dans PowerShell : `$env:PEXELS_API_KEY = "TA_CLE"` avant de lancer Streamlit. La recherche utilise le titre, non une compréhension sémantique détaillée de chaque scène. Vérifie les droits et conserve les crédits des photographes.

Les visuels générés par le mode Éco sont des cartes graphiques. Les images IA nécessitent stable-diffusion.cpp et un modèle compatibles, téléchargés séparément. La synchronisation des sous-titres est approximative, les effets restent des zooms simples et la voix Edge TTS nécessite Internet. **Ces fonctionnalités n'ont pas été validées par un test de bout en bout sur Windows.**

Pour vérifier rapidement les imports :

```powershell
cd $HOME\mntage
.\.venv\Scripts\python.exe -m compileall -q .
.\.venv\Scripts\python.exe -m streamlit run app.py
```
