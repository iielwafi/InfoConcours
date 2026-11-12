# Rapport de qualité pédagogique — InfoConcours

Revue de phase 7 — 12 novembre 2026. Les nombres ci-dessous proviennent d’une base temporaire migrée et semée à neuf. Ce contrôle ne certifie ni l’alignement à un référentiel officiel ni une validation par des enseignants.

## Inventaire vérifié

- Curriculum source : 8 matières, 16 modules, 32 chapitres, 32 leçons.
- Banque initialisée par `seed-content` : 200 questions distinctes, 25 par matière, chacune avec quatre choix distincts, une réponse indexée, une explication française, un chapitre et un objectif pédagogique.
- Progression par difficulté après regroupement éditorial des libellés historiques : 64 Débutant, 10 Élémentaire, 80 Intermédiaire, 19 Avancé et 27 Expert. Les anciens libellés Facile/Moyen/Difficile restent enregistrés pour préserver la compatibilité et sont respectivement regroupés comme Débutant/Intermédiaire/Expert dans ce tableau.
- Pratique : 224 exercices publiés, 7 par leçon. Soixante-quatre activités historiques sont conservées et cinq nouveaux exercices ouverts progressifs sont ajoutés pour chacune des 32 leçons. Ces nouveaux exercices portent leur objectif et une grille de correction; ils restent non notés automatiquement.
- Banque de questions : 200 actives et 200 associées à une leçon ainsi qu’à un objectif lorsque le curriculum contient une leçon dans le chapitre.
- Vidéos : 0 vérifiée, 0 en attente, 0 rejetée. Aucune des 32 leçons n’a une vidéo dédiée vérifiée.
- Base historique `instance/infoconcours.db` : inspectée en lecture seule; elle contient 24 questions et un compte utilisateur dans son ancien schéma. Elle n’a pas été migrée, ressemée ou modifiée pendant cette phase.

| Matière | Questions | Débutant* | Élémentaire | Intermédiaire* | Avancé | Expert* |
|---|---:|---:|---:|---:|---:|---:|
| Algorithmique | 25 | 7 | 2 | 9 | 3 | 4 |
| Programmation | 25 | 7 | 2 | 10 | 3 | 3 |
| Bases de données | 25 | 8 | 1 | 10 | 2 | 4 |
| Systèmes | 25 | 8 | 1 | 11 | 2 | 3 |
| Réseaux | 25 | 9 | 1 | 10 | 2 | 3 |
| Architecture | 25 | 8 | 1 | 9 | 2 | 5 |
| Bureautique | 25 | 8 | 1 | 11 | 3 | 2 |
| Multimédia | 25 | 9 | 1 | 10 | 2 | 3 |
| **Total** | **200** | **64** | **10** | **80** | **19** | **27** |

\*Inclut les questions dont le libellé historique Facile/Moyen/Difficile est regroupé respectivement sous Débutant/Intermédiaire/Expert. Cette normalisation sert au rapport seulement; les lignes existantes ne sont pas réécrites.

## Qualité des leçons et limites

- Le nouvel audit de contenu trouve **0 leçon complète, 32 incomplètes et 32 à relire par un expert**. Les conditions sont observables (théorie d’au moins 2 600 caractères, trois exemples numérotés, sections d’application et d’erreurs, cinq niveaux d’exercices, vidéo dédiée vérifiée, objectifs, résumé et fiche). Les seuils n’évaluent pas la justesse des notions.
- Les théories semées sont enrichies avec introduction, définitions, démarche pas à pas, applications, erreurs fréquentes et conseil de résolution, mais leur longueur actuelle reste sous le seuil de profondeur de la revue Phase 7; elles ne sont pas présentées comme des cours complets.
- Les nouveaux exercices sont des réponses ouvertes avec niveaux Débutant, Élémentaire, Intermédiaire, Avancé et Défi concours. Les 64 activités historiques sont conservées en plus. Les QCM de chapitre et le moteur adaptatif continuent d’utiliser les 200 questions; l’association question-leçon est ajoutée sans compter les réponses ouvertes comme maîtrise.
- Les exercices libres nécessitent un retour humain et n’attribuent aucun score avant correction.
- Les niveaux proposés sont éditoriaux; ils ne sont pas calibrés sur des résultats représentatifs d’apprenants. Les clés ont des contrôles structurels automatisés, mais n’ont pas reçu de validation pédagogique externe.
- Les 176 questions ajoutées dans les phases précédentes et cette phase n’ont pas toutes d’énoncé, de choix et de correction Darija. La localisation d’une partie de la banque reste incomplète.
- Les candidats vidéo retournés par la recherche n’ont pas pu être confirmés par une ouverture directe de page dans l’outil de navigation. Aucun lien n’a été ajouté ou présenté comme vérifié.

## Contrôles automatisés exécutés

- Suite complète `python -W ignore -m unittest discover -s tests -v` : **44 tests passés** en 190,095 s.
- Vérifications incluent unicité, 25 questions par matière, champs/questions structurés, association chapitre, cinq bandes de difficulté dans les huit matières, sélection adaptative à 30/80/95 % dans chaque matière, flux admin, progression et validation YouTube HTTPS/host/ID.
- Tests de migration : base vierge et conservation des lignes historiques dans une base temporaire.
- `py_compile` des modules et tests modifiés : réussi.
- Migration additive `b71c92a4e613` : objectif pédagogique des exercices, statut et date de vérification vidéo, et associations leçon-vidéo / leçon-question. L’upgrade a été appliqué à une base temporaire vierge; les tests confirment la conservation d’anciennes lignes d’exercice.
- Après migration et `seed-content` sur la base d’audit temporaire : 8 matières, 16 modules, 32 chapitres, 32 leçons, 224 exercices, 200 questions, 0 vidéo vérifiée/en attente/rejetée et 0 résultat d’évaluation préexistant dans cette base neuve. La base historique n’a été ni migrée, ni ressemée, ni modifiée.

## Pas d’affirmation officielle

Le corpus est un support de révision original et général. Il ne prétend pas représenter les exigences officielles du concours marocain. Une personne enseignante doit relire les corrections, les choix de difficulté, la terminologie locale et la progression avant diffusion comme cours certifié.


## Phase 8 — audit de production pédagogique (12 novembre 2026)

Cette section remplace les seuils de longueur et les comptes de complétude antérieurs. Audit exécuté après `seed-content` dans une base SQLite temporaire neuve, avec le validateur existant renforcé. Aucun lien vidéo n’a été ajouté ni marqué vérifié sans preuve d’accès.

- **32/32 sujets de leçon enrichis** avec contenu propre au chapitre : vocabulaire, explications thématiques, démonstration, trois exemples, cinq points de révision; les objectifs atteignent cinq par leçon. Les exemples SQL/Python ont des contrôles d’exécution dédiés.
- **Théorie :** entre 476 et 636 mots par leçon. Le seuil Phase 8 est 1 500 mots pour la théorie seule; **0/32 l’atteignent**, donc 0 leçon complète. Le total de cours (théorie, champs d’apprentissage et exercices) varie de 1119 à 1503 mots, mais ne remplace pas le seuil de théorie.
- **Exercices :** 224 publiés (7 par leçon), dont cinq nouvelles activités ouvertes à réponse libre par leçon; **5 corrections structurées** par leçon. Chaque réponse libre reste en attente d’un retour humain et ne crée pas de score automatique.
- **Exemples distincts :** 3 par leçon. **Vidéos dédiées vérifiées : 0**; les vidéos n’ont pas été fabriquées ou ajoutées.
- **Relecture experte :** requise pour les 32 leçons. Les contrôles automatisés vérifient la présence et la structure, pas l’exactitude pédagogique, l’adéquation aux élèves ou l’alignement sur un programme officiel.
- **Données historiques :** `instance/infoconcours.db` conservée sans migration ni écriture par ce travail. Aucun changement de schéma/migration Phase 8.

| Leçon | Mots de théorie | Mots cours total | Exemples | Exercices | Corrections détaillées | Vidéos vérifiées |
|---|---:|---:|---:|---:|---:|---:|
| Écrire et tracer un algorithme | 617 | 1467 | 3 | 7 | 5 | 0 |
| Raisonner sur les répétitions | 605 | 1393 | 3 | 7 | 5 | 0 |
| Parcourir et rechercher dans une séquence | 636 | 1503 | 3 | 7 | 5 | 0 |
| Décomposer un problème et analyser son coût | 612 | 1387 | 3 | 7 | 5 | 0 |
| Écrire des fonctions fiables | 523 | 1333 | 3 | 7 | 5 | 0 |
| Organiser les données en collections | 561 | 1302 | 3 | 7 | 5 | 0 |
| Modéliser avec la programmation orientée objet | 537 | 1255 | 3 | 7 | 5 | 0 |
| Vérifier un programme par des tests | 538 | 1346 | 3 | 7 | 5 | 0 |
| Passer d’un besoin à un modèle relationnel | 528 | 1340 | 3 | 7 | 5 | 0 |
| Réduire les anomalies de données | 502 | 1356 | 3 | 7 | 5 | 0 |
| Construire une requête SQL lisible | 510 | 1352 | 3 | 7 | 5 | 0 |
| Garantir cohérence et accès efficaces | 495 | 1206 | 3 | 7 | 5 | 0 |
| Partager le processeur | 521 | 1312 | 3 | 7 | 5 | 0 |
| Comprendre mémoire et pagination | 526 | 1220 | 3 | 7 | 5 | 0 |
| Manipuler un système de fichiers avec prudence | 519 | 1170 | 3 | 7 | 5 | 0 |
| Protéger disponibilité et accès | 496 | 1201 | 3 | 7 | 5 | 0 |
| Situer les protocoles dans les couches réseau | 540 | 1224 | 3 | 7 | 5 | 0 |
| Lire un préfixe CIDR | 533 | 1236 | 3 | 7 | 5 | 0 |
| Choisir un transport selon le besoin | 510 | 1248 | 3 | 7 | 5 | 0 |
| Suivre la résolution d’un nom et une requête Web | 555 | 1244 | 3 | 7 | 5 | 0 |
| Suivre une instruction dans le processeur | 495 | 1119 | 3 | 7 | 5 | 0 |
| Comparer cache, RAM et stockage | 500 | 1208 | 3 | 7 | 5 | 0 |
| Coder nombres et caractères | 498 | 1178 | 3 | 7 | 5 | 0 |
| Comparer sans se fier à un seul chiffre | 484 | 1228 | 3 | 7 | 5 | 0 |
| Produire un document accessible et cohérent | 483 | 1260 | 3 | 7 | 5 | 0 |
| Construire des formules recopiables | 511 | 1217 | 3 | 7 | 5 | 0 |
| Résumer des données sans les déformer | 482 | 1254 | 3 | 7 | 5 | 0 |
| Préparer un support pédagogique clair | 476 | 1183 | 3 | 7 | 5 | 0 |
| Choisir un format d’image | 488 | 1169 | 3 | 7 | 5 | 0 |
| Comprendre couleur et taille d’image | 508 | 1206 | 3 | 7 | 5 | 0 |
| Numériser un signal audio | 492 | 1147 | 3 | 7 | 5 | 0 |
| Distinguer codec et conteneur | 496 | 1158 | 3 | 7 | 5 | 0 |

