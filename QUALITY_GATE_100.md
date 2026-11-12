# MNTAGE — Bilan critique à 100 demandes d'optimisation

Démarrage du suivi : **12 novembre 2026**.

**Cycle de développement visé : 600 optimisations.** Le présent document est
la **première réévaluation critique à 100**. Optimisations #1 et #2/600 présentes
sur la branche principale, #3/600 en revue (CI Linux et Windows réussie),
et #4/600 proposée sur une branche dépendant de #3 ;
#5/600 non documentée, #6/600 en revue (CI Linux et Windows réussie),
#7/600 proposée sur une branche dépendant de #6 ;
**contrôle visuel Windows des vidéos à effectuer** : statuts partiels.
Le compteur persistant du PC reste indépendant et ne s'incrémente qu'après
confirmation via `tools/session_handoff.py`. Les anciens échanges ne sont pas
reconstitués artificiellement.

## Règles de comptage

- **Une demande utilisateur d'optimisation = une entrée**, qu'elle aboutisse à un
  changement de code, une décision de ne rien changer ou un diagnostic.
- Une entrée comporte une date, une description, le défaut visé, un test ou une
  preuve visuelle, les commits éventuels et un statut : validée, partielle, échouée.
- Ne compter **ni les réponses d'encouragement ni les modifications cosmétiques
  multiples** comme plusieurs demandes.
- Une demande livrée sans preuve de test reste *partielle*. Les erreurs découvertes
  comptent dans le bilan, elles ne sont pas effacées.
- Les optimisations liées à l'audio ne modifient pas le choix des voix. Validation
  TikTok en temps réel : hors périmètre tant que suspendue.

## Journal à compléter à chaque nouvelle demande

| N° | Date | Demande et défaut | Modification / commit | Preuve ou test | Statut |
|---:|---|---|---|---|---|
| 1 | 2026-11-12 | Libellés du dessin animé lisibles sur Windows ; objectif de reprise étendu sans perte à 600 | `b635c18`, `e33018a` | `tests/test_typography.py` et migration du suivi ajoutés ; **à exécuter sur Windows** | Partielle |
| 2 | 2026-11-12 | Marche moins rigide : pas alternés, levée de pied, flexion de genou, balancement opposé des bras, rebond du corps avec appui au sol | `f817296`, `b2406c4`, `e648ef4` | `tests/test_walk_gait.py` (5 tests) ajoutés ; **à exécuter et inspecter en MP4 sur Windows** | Partielle |
| 3 | 2026-11-12 | Glissement horizontal du pied d'appui lié au cycle de marche | `f9a8464`, `01a94a1`, `86afb9a` (branche `optimization-003-lock-stance-foot`) | CI Linux/Windows réussie après installation explicite de FFmpeg sur Ubuntu ; **contrôle visuel local à confirmer** | Partielle |
| 4 | 2026-11-12 | Le pied posé se déplace avec la translation du personnage dans le décor | `f45002c`, `e432ea4`, `083e764` (branche `optimization-004-world-foot-plant`, dépend de #3) | CI Linux/Windows : 142 tests réussis ; **validation visuelle locale en attente** | Partielle |
| 6 | 2026-11-12 | Flexions des genoux géométriquement incohérentes pendant la marche | `d528cad`, `97d506e` (branche `optimization-006-two-bone-knees`, dépend de #4) | CI Linux/Windows : 147 tests réussis ; **contrôle visuel local à confirmer** | Partielle |
| 7 | 2026-11-12 | Chaussures trop rigides et horizontales pendant la phase aérienne du pas | `2a7b67b`, `a651a2c` (branche `optimization-007-ankle-foot-roll`, dépend de #6) | Relevé progressif de l'avant-pied sans déplacer l'appui au sol ; 5 tests sur le pivot, la continuité, la hauteur et le rendu ; **CI et contrôle visuel à confirmer** | Partielle |

## État de référence au démarrage (à vérifier, pas un score de performance)

- Pilote d'animation d'un sujet spécialisé : miroir et perception visuelle.
- Six compositions de plans, sous 3,25 s dans les tests du storyboard ; lip-sync
  approximatif fondé sur le niveau de l'audio ; 1080 × 1920 à 25 i/s.
- Tests ciblés et aperçus courts réalisés ; **pas de preuve documentée d'un
  parcours complet et fiable sur le Windows cible**.
- Qualité esthétique de niveau prototype ; pas de validation de 3 sujets distincts,
  pas de mesure de temps/coût par vidéo, pas de test de vente.
- Les évaluations antérieures de « 65 % » ne mesurent ni la satisfaction client,
  ni la qualité professionnelle, ni la rentabilité.

## Protocole de réévaluation après la 100e demande

### A. Qualité artistique et narration (0–10)

Évaluer **à l'aveugle** au moins 3 vidéos complètes de 60–90 secondes sur
**3 sujets scientifiques différents**, pas uniquement des extraits de miroir :
compréhension sans explication externe, synchronisation de l'image avec les
phrases, expressivité, variété et cohérence du style, lisibilité mobile, impact
des 3 premières secondes. Recueillir aussi des avis externes, y compris négatifs.

### B. Fiabilité technique

Exécuter de bout en bout sur le PC Windows cible : tests unitaires complets,
génération + export + sous-titres + audio, durée audio/vidéo, mémoire et temps de
rendu, retour après erreur. Vérifier 1080 × 1920, 25 i/s, aucun plan > 4 s,
pas de personnages en double, pas d'objets hors récit, pas de décalage voix/visuel
gênant. Une démonstration de 8 s **ne suffit pas**.

### C. Généralisation

Vérifier qu'un nouveau sujet fonctionne **sans réécrire les animations à la
main** et sans inventer d'illustrations hors sujet. Rapporter explicitement le
pourcentage de demandes prises en charge et la part nécessitant une intervention
manuelle.

### D. Rentabilité

Mesurer le coût total **par vidéo** : logiciels et services, électricité
si pertinente, temps humain complet (préparation, corrections, rendu, livraison),
commissions, retours client. Distinguer **chiffre d'affaires, marge brute,
bénéfice et rémunération du travail**. Ne pas conclure à la rentabilité
commerciale avant des ventes réelles et répétables. Les revenus TikTok supposés
ne comptent pas comme revenus prouvés.

### E. Verdict contradictoire obligatoire

Après 100 demandes documentées, produire :
1. Ce qui fonctionne, avec preuves ;
2. Ce qui échoue encore et fréquence des bugs ;
3. Une note artistique /10 avec méthode et taille d'échantillon ;
4. Les coûts et délais mesurés ;
5. Les limites du moteur pour de nouveaux sujets ;
6. **GO / PIVOT / STOP** motivé, sans utiliser le nombre de commits ou
   de demandes comme preuve de qualité.

**Important :** atteindre 100 demandes n'est pas en soi un succès et ne garantit
pas 100 % de qualité. Une faiblesse majeure doit être signalée immédiatement,
sans attendre la centième demande.
