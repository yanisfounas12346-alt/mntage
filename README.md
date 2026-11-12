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

**Limites :** sous-titres et musique personnelle disponibles, mais pas de publication publique automatique, pas de génération vidéo cinématique par IA et pas encore de test de bout en bout validé sur Windows. La publication YouTube privée reste disponible séparément via `youtube_upload.py` avec OAuth. Vérifie les droits des voix, images et modèles avant monétisation.

## Sous-titres et musique (nouveau)

Dans Streamlit, coche **Ajouter des sous-titres automatiques** pour incruster des sous-titres et exporter aussi un fichier SRT. Le minutage utilise les événements WordBoundary d'Edge TTS lorsqu'ils sont disponibles ; sinon il est estimé. FFmpeg doit disposer du filtre `ass` (libass) ; vérifie avec `ffmpeg -filters | findstr ass`. Tu peux importer une musique MP3 dont tu possèdes les droits ; elle est mixée à volume réduit avec la narration. Aucun catalogue musical ni téléchargement automatique n'est inclus.

## Publication

`youtube_upload.py` reste une commande distincte, avec configuration OAuth Google Cloud. Il n'y a pas de publication automatique sans validation dans l'interface.

## Studio v0.3 : file, médias et statistiques

- Onglet **Créer** : script seul, visuels automatiques, narration, sous-titres estimés et musique MP3 personnelle facultative.
- Onglet **File & historique** : ajouter des scripts, puis cliquer sur **Traiter la prochaine vidéo**. Les tâches sont stockées dans `outputs/mntage.sqlite3` et exécutées **manuellement**, une par une. Les fichiers musicaux et images importées ne sont pas stockés dans la file. Une tâche interrompue peut rester au statut `running` : depuis l'historique, confirme que le rendu est bien arrêté puis utilise « Remettre en attente ». Les tâches en échec peuvent être relancées et les tâches en attente annulées. La file limite les montages à un seul travail actif à la fois, y compris entre plusieurs onglets ; les générations immédiates de l'onglet Créer ne sont pas couvertes par cette limite.
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

### Vérification sur GitHub Actions

À chaque push ou pull request, le workflow `.github/workflows/python-checks.yml` prévoit deux environnements : Linux et Windows. Sur Windows, il installe les dépendances, puis lance `verify_windows.ps1`, y compris les tests FFmpeg. Consulte l'onglet **Actions** du dépôt pour voir si les vérifications ont réellement réussi ; la présence du workflow ne garantit pas leur succès.

### Vérification automatique sous Windows

Après installation et mise à jour du dépôt, lance dans PowerShell :

```powershell
.\verify_windows.ps1
```

Le script vérifie Python, FFmpeg, le filtre ASS, compile les modules et lance les tests hors ligne. Si l'exécution des scripts PowerShell est bloquée, utilise `powershell -ExecutionPolicy Bypass -File .\verify_windows.ps1`. Un résultat vert confirme uniquement les tests exécutés ; il ne remplace pas une génération réelle avec Edge TTS et une recherche Wikimedia Commons connectée à Internet.

**Visuels personnels :** les clips MP4 importés sont prioritaires, puis les images importées. La recherche automatique n'est utilisée qu'en l'absence de ces fichiers. Retire les fichiers importés pour revenir au mode Wikimedia Commons.
