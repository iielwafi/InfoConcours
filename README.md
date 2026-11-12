# InfoConcours Online

Application Flask de préparation au concours marocain de l’enseignement en informatique. Le projet conserve son architecture Flask/SQLAlchemy, les comptes et l’authentification existants. Aucun déploiement ni changement de la base de production n’a été effectué pendant cette phase.

## Académie et progression

- 8 matières pondérées, 16 modules, 32 chapitres et 32 leçons originales. La vérification automatisée Phase 7 classe actuellement **0 leçon complète et 32 incomplètes**, car les leçons n’ont pas trois exemples nommés distincts, leur cours ne satisfait pas encore le seuil de profondeur, et aucune vidéo dédiée vérifiée n’existe. Les 32 leçons nécessitent aussi une revue experte; le contrôle de structure n’atteste pas l’exactitude pédagogique.
- Le contenu fourni par la semence compte 200 questions distinctes (25 par matière), associées à un chapitre, à une leçon lorsqu’elle existe et à un objectif d’apprentissage. Les apprenants conservent deux activités historiques par leçon, plus cinq exercices ouverts progressifs; soit 224 exercices de curriculum au départ. Les réponses ouvertes utilisent le correcteur sémantique configuré ou, sans service fiable, la correction humaine.
- Les diagnostics, QCM et examens continuent d’utiliser la banque existante et d’enregistrer les résultats par compte. La base locale historique n’a pas été modifiée ni automatiquement ressemée.
- Les apprenants peuvent reprendre une leçon non terminée, voir les leçons découvertes/en cours/terminées, naviguer entre les leçons, et marquer une leçon comme terminée.
- Les résultats de QCM, vrai/faux et réponses courtes acceptées sont corrigés immédiatement. Les réponses libres utilisent l’évaluateur sémantique configuré; sans clé IA ou si la réponse est incertaine, elles restent en correction manuelle. La maîtrise ne compte que des résultats évalués et reste masquée quand les données sont insuffisantes.

## Exercices et administration

Chaque exercice peut être un QCM, un vrai/faux, une réponse courte avec variantes acceptées ou une réponse ouverte. Les réponses ouvertes sont évaluées selon le sens, les concepts, le raisonnement et le barème par l’API OpenAI Responses si le serveur est configuré; une confiance inférieure à 0,70, une erreur fournisseur ou un résultat invalide envoie l’essai en correction manuelle. Sans configuration, aucune note sémantique n’est simulée. Les tentatives, réponses et retours persistent sous leur exercice; la correction manuelle est accessible sous Administration → Réponses à corriger.

Pour activer l’évaluation IA, configurez `OPENAI_API_KEY` et `EXERCISE_GRADING_MODEL` dans l’environnement serveur (voir `.env.example`). La clé n’est jamais envoyée au navigateur. Le fournisseur reçoit le titre, l’énoncé, le corrigé, le barème, l’objectif et la réponse de l’apprenant; la page le signale avant la soumission. Sans clé, le parcours manuel reste disponible.

Les administrateurs peuvent créer, éditer, publier, dépublier ou retirer les contenus. Les exercices qui ont déjà des tentatives ne peuvent pas être supprimés ni réécrits : créer une nouvelle version préserve l’historique des apprenants.

## Français / Darija

Le français est la langue par défaut. La préférence de langue du compte est enregistrée et revient après déconnexion/reconnexion. La Darija est écrite en caractères arabes et les exemples de code sont protégés de la traduction.

La localisation n’est pas encore complète. Les 176 questions ajoutées depuis la banque historique ont encore leurs champs arabes vides ou en français; plusieurs objectifs, exercices, corrections, messages et blocs administratifs restent français. Le détail de cette couverture est dans [CONTENT_QUALITY_REPORT.md](/C:/Users/Lamiaa/Downloads/InfoConcours_Online/CONTENT_QUALITY_REPORT.md).

## Vidéothèque

Les ressources sont ajoutées par un administrateur en attente par défaut. Le flux permet l’approbation, le rejet, le marquage indisponible et le retour en attente. Une modification des métadonnées réinitialise la vérification. Les ressources validées peuvent être associées à une leçon et intégrées à son cours avec lecteur `youtube-nocookie.com`. Aucune vidéo n’est préchargée : le compteur actuel est 0 vérifiée, 0 en attente et 0 rejetée. Le suivi « visionnée » est une déclaration manuelle par compte, pas une mesure de lecture complète.

## Base de données et migrations

Flask-Migrate/Alembic est initialisé sous le dossier migrations. La migration additive `b71c92a4e613` ajoute l’objectif pédagogique aux exercices, le statut/date de vérification aux vidéos, et les associations leçon-vidéo / leçon-question. Son downgrade est volontairement bloqué pour protéger les données. La migration a été éprouvée sur une base SQLite temporaire; `instance/infoconcours.db` n’a pas été modifiée.

En production, APP_ENV=production désactive la création automatique des tables et l’insertion automatique du curriculum au démarrage. Les migrations et la semence de contenu sont deux opérations explicites après sauvegarde.

### Appliquer une migration en préservant les données

1. Arrêter l’application et faire une sauvegarde vérifiable.
2. Essayer d’abord flask db upgrade sur une copie restaurée de la base.
3. Sur la base cible, appliquer la migration.
4. Lancer flask seed-content pour ajouter le contenu pédagogique manquant. Cette commande est idempotente et n’écrase pas les leçons modifiées par un administrateur.
5. Redémarrer et vérifier la connexion, les comptes, les résultats historiques, les leçons et les tentatives d’exercice.

Exemple SQLite PowerShell, avant toute migration :

```powershell
New-Item -ItemType Directory -Force .\backups | Out-Null
$backup = ".\backups\infoconcours-$(Get-Date -Format yyyyMMdd-HHmmss).db"
Copy-Item -LiteralPath .\instance\infoconcours.db -Destination $backup
```

Restaurer seulement après arrêt du service et vérification de la sauvegarde :

```powershell
Copy-Item -LiteralPath $backup -Destination .\instance\infoconcours.db
```

Pour PostgreSQL, utiliser un profil libpq/PGService configuré dans l’environnement, puis sauvegarder avec pg_dump --format=custom --file=.\backups\infoconcours.dump --dbname=$env:PGSERVICE. Restaurer d’abord dans une nouvelle base de vérification avec pg_restore --dbname=$env:PGSERVICE_RESTORE .\backups\infoconcours.dump; ne pas restaurer par-dessus la base active sans procédure de reprise approuvée.

### Commandes Alembic

```powershell
$env:APP_ENV = "production"
$env:SECRET_KEY = "la-cle-secrete-de-l-environnement"
$env:AUTO_CREATE_SCHEMA = "0"
$env:AUTO_SEED_CONTENT = "0"
flask --app app db upgrade
flask --app app seed-content
```

Ne jamais passer DATABASE_URL de production lors d’un test ou d’une révision locale. Garder les futures révisions Alembic versionnées; ne pas modifier cette migration initiale après mise en service.

## Sécurité et configuration

- En production et hors développement, `SECRET_KEY` et `DATABASE_URL` doivent être configurés explicitement. En développement, l’application crée une clé temporaire aléatoire si aucune clé n’est fournie et utilise la base isolée `instance/infoconcours-phase8-dev.db` par défaut; les sessions locales expirent au redémarrage du processus.
- Les cookies sont HttpOnly, SameSite=Lax, protégés en HTTPS en production; Flask-Login utilise la protection de session forte.
- CSRF, hachage Werkzeug des mots de passe, limitation des tentatives de connexion, validation côté serveur et permissions admin sont activés.
- Les réponses incluent des en-têtes de sécurité usuels. Le mode debug est désactivé dans le lancement direct.
- Les dépendances sont bornées dans requirements.txt; Flask-Migrate et Alembic sont inclus.

## Lancer en local (PowerShell)

Depuis C:\Users\Lamiaa\Downloads\InfoConcours_Online :

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:APP_ENV = "development"
$env:SECRET_KEY = [guid]::NewGuid().ToString() + [guid]::NewGuid().ToString()
$env:DATABASE_URL = "sqlite:///infoconcours-phase8-dev.db"
$env:AUTO_CREATE_SCHEMA = "0"
$env:AUTO_SEED_CONTENT = "0"
python app.py
```

Ouvrir http://127.0.0.1:5000. Ces paramètres réutilisent la base de développement existante et empêchent le démarrage de créer des tables ou de semer des contenus. Pour une nouvelle base vide, appliquer séparément une migration après une sauvegarde. Cette base ne charge pas les utilisateurs de la base historique `instance/infoconcours.db`. Pour tester avec les données historiques, migrer d’abord une copie vérifiée et utiliser cette copie dans DATABASE_URL. Créer le premier administrateur après l’inscription :

### Démarrage rapide (Git Bash)

Avec l’environnement virtuel activé, depuis la racine du projet :

```bash
export APP_ENV=development
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export DATABASE_URL=sqlite:///infoconcours-phase8-dev.db
export AUTO_CREATE_SCHEMA=0
export AUTO_SEED_CONTENT=0
python app.py
```

Le démarrage réutilise la base isolée existante `instance/infoconcours-phase8-dev.db`, sans créer de schéma ni semer de contenu; la base historique `instance/infoconcours.db` n’est pas utilisée. Garde cette configuration pour préserver les contenus et tentatives existants. Une clé locale est générée dans le terminal pour la session :

```bash
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
```

```powershell
flask --app app make-admin NOM_UTILISATEUR
```

Exécuter toute la suite de tests :

```powershell
.\.venv\Scripts\python.exe -W ignore -m unittest discover -s tests -v
```

## Limites et revue qualité

- Les ressources sont un support pédagogique original, pas une couverture certifiée ou une interprétation d’exigences officielles.
- Les 200 questions et les leçons demandent encore une validation indépendante d’enseignants marocains; les contenus sont évalués dans [le rapport de qualité](/C:/Users/Lamiaa/Downloads/InfoConcours_Online/CONTENT_QUALITY_REPORT.md).
- Aucune clé IA n’est configurée dans cet environnement; l’évaluation sémantique réelle requiert la configuration serveur décrite plus haut. Le flux de correction manuelle fonctionne, sans notification externe à l’enseignant.
- Une vérification visuelle manuelle reste nécessaire sur les navigateurs de bureau, tablette et mobile, notamment pour le RTL, les formulaires d’exercices et l’administration.

## Fichiers principaux

- [app.py](/C:/Users/Lamiaa/Downloads/InfoConcours_Online/app.py) : modèles, routes, sécurité et calcul de maîtrise.
- [curriculum_data.py](/C:/Users/Lamiaa/Downloads/InfoConcours_Online/curriculum_data.py) : curriculum et banque intégrés.
- templates/ et static/ : pages, scripts, styles et graphiques.
- migrations/ : configuration Flask-Migrate/Alembic et migration additive.
- tests/ : suite fonctionnelle, qualité de corpus et migration.

## Adaptation, examens et expérience apprenant

- Le diagnostic initial présente trois questions tirées de chacune des huit matières (24 au total) pour obtenir une première mesure comparable par matière. Les matières sans réponses évaluées ne sont pas classées comme faibles.
- Les séries QCM et les examens blancs sélectionnent les niveaux à partir des résultats réels par matière. Les paliers par défaut sont Débutant (<40 %), Élémentaire (40–59 %), Intermédiaire (60–74 %), Avancé (75–89 %) et Expert / défi (90 % et plus). Ils sont configurables avec `ADAPTIVE_THRESHOLDS=40,60,75,90`. La sélection considère les résultats historiques, la récence, la difficulté et les erreurs enregistrées; les séries favorisent les questions non vues, puis les erreurs passées.
- La semence intégrée contient maintenant **200 questions distinctes**, soit 25 par matière, grâce à 96 questions nouvelles et non dupliquées. Les trois anciens niveaux (Facile/Moyen/Difficile) restent pris en charge; les nouveaux items emploient aussi Débutant, Élémentaire, Intermédiaire, Avancé et Expert. Les leçons contiennent 7 exercices publiés chacune (224 au total), dont cinq nouvelles activités ouvertes avec correction manuelle, en plus des exercices préexistants. Le rapport qualité indique les comptages par leçon. Selon les critères Phase 8, les 32 leçons restent incomplètes tant que la théorie n’atteint pas 1 500 mots et qu’une vidéo dédiée n’est pas vérifiée.
- La durée de l’examen blanc est configurable (`EXAM_DURATION_MINUTES`, valeur par défaut 240 minutes, plafonnée à 240); cette valeur est un paramètre de simulation et ne représente pas une durée officielle. Le navigateur garde les réponses et repères de révision en stockage local jusqu’à soumission; le serveur vérifie l’identifiant d’exécution et la date d’expiration.
- Les vidéos vérifiées sont intégrées aux leçons de leur chapitre et peuvent être marquées comme visionnées depuis la leçon. La banque de démarrage contient **0 vidéo vérifiée**; aucun lien n’est inventé. La recherche Web de phase 6 a fait ressortir des candidats, mais l’ouverture directe n’a pas permis de confirmer leur disponibilité; aucun n’a donc été marqué vérifié. Une leçon sans ressource affiche cet état et les administrateurs peuvent ajouter un lien puis le valider.
- L’académie présente la progression par matière. Le tableau de bord propose une prochaine leçon et une série QCM issues des évaluations disponibles. Le minuteur conserve la saisie manuelle existante et affiche l’historique réel par matière, ainsi que les totaux de la semaine.
- La révision Alembic `a3d91d2e4c10` ajoute le champ `learning_objective` de façon additive à la métadonnée de question. Elle ne supprime pas les lignes existantes.


