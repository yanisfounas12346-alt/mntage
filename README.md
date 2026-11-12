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

## Studio Science WTF — pilote animé 2D (miroir)

Dans **Créer**, active **Science WTF**, puis choisis **Studio animé 2D — miroir (gratuit)**.
Ce mode crée des scènes originales sans images cloud, en conservant le personnage au
sac jaune et une caméra fixe. Les six compositions alternent : plans avec personnage,
gros plans du reflet, comparaison **normal / perçu**, observation chronométrée et
explications visuelles du cerveau. Les plans durent **3,25 secondes maximum**.

- Le bouton **Tester 5 plans animés en 8 secondes** produit un aperçu **silencieux** :
  la bouche y est simulée pour montrer son animation.
- Pour le MP4 complet, la bouche suit approximativement le signal sonore de la voix
  générée et se ferme dans les silences. Il ne s'agit **pas** d'un lip-sync phonétique.
- Le pilote n'est disponible **que pour le script de l'expérience du miroir** :
  les autres sujets nécessitent encore leur propre storyboard et leurs animations.
- Les exports sont en 1080 × 1920 à 25 i/s. Le rendu peut être long sur CPU ;
  aucune requête IA payante n'est lancée par ce mode.

**Contrôle local Windows** :

```powershell
cd C:\Users\taver\mntage
git pull
.\.venv\Scripts\python.exe -m py_compile app.py video_factory.py motion_studio.py motion_director.py speech_motion.py tiktok_pro.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Le **pack SEO** propose un titre de recherche, une accroche et des hashtags à
relire. Il est aussi enregistré à côté du MP4 (fichier `.seo.txt`).
Ces propositions ne sont ni des tendances TikTok vérifiées ni une garantie de vues.

**Statut :** moteur expérimental en cours d'amélioration, pas encore production
professionnelle validée sur tout un épisode et sur toutes les machines Windows.

## Optimisation par lots : test obligatoire toutes les 10 demandes

Les fichiers `tools/checkpoint.py` et `tools/next_request.py` mettent en place le
**point de contrôle de non-régression**, sans modifier de voix, sans appeler
d'IA payante et sans supprimer de modifications du dépôt.

Après la réponse à la **10e demande**, lance sur ton PC :

```powershell
cd C:Users	avermntage
..venvScriptspython.exe tools/checkpoint.py --iteration 10
```

La commande effectue un `git pull --ff-only` prudent, vérifie les
fichiers Python, FFmpeg/ffprobe et exécute
`python -m unittest discover -s tests -p 'test_*.py' -v`.

- **PASS** : les améliorations peuvent reprendre avec la 11e demande.
- **FAIL** : stop aux nouvelles fonctionnalités. Le fichier
  `outputs/checkpoints/cycle_0010_next_prompt.txt` contient le diagnostic
  à transmettre pour réparer le code ; relancer **le même** checkpoint
  après correction, jusqu'au succès. Relire les logs pour ne pas partager
  de clés secrètes.
- Aux demandes 20, 30, 40, etc., remplacer `--iteration 10` par le
  nouveau numéro. Pour vérifier sans récupérer GitHub, ajouter
  `--no-pull` (test potentiellement obsolète).

Pour un **contrôleur de clics ChatGPT** externe, une fois la réponse terminée,
appeler :

```powershell
..venvScriptspython.exe -m tools.next_request --completed 10
```

Cette commande retourne un objet JSON avec :
`status` = `CONTINUE` ou `REPAIR`,
`allow_new_optimization` et `prompt`.
Le contrôleur ne doit **pas incrémenter le compteur des optimisations**
lorsqu'il soumet une réparation. Le même palier de 10 est retesté.

**Important :** les tests et le choix du prochain message sont programmés.
Le logiciel ne pilote **pas encore la souris/le navigateur**, ne sait pas
garantir la fin d'une réponse ChatGPT et **ne répare pas automatiquement
sans que son prompt d'erreur soit renvoyé à l'assistant**. La qualité
artistique doit encore être validée humainement sur de vrais MP4.

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
