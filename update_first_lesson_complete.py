"""One-pass, backup-first improvement of the first InfoConcours lesson and its seven guided exercises.
Existing exercise versions are archived, never deleted; attempts remain attached to their original versions.
Run from the project root with the project's virtual environment active:
    python update_first_lesson_complete.py
Only instance/infoconcours-phase8-dev.db is eligible.
"""
from __future__ import annotations
import json, sqlite3, os
from datetime import datetime
from pathlib import Path

# Prevent app.py from auto-running seed/enrichment routines during this one-off update.
os.environ["AUTO_SEED_CONTENT"] = "0"

from app import (create_app, db, CurriculumSubject, CurriculumModule,
                 CurriculumChapter, CurriculumLesson, CourseExercise,
                 ExerciseAttempt)

EXPECTED_DB = "infoconcours-phase8-dev.db"
EXPECTED_LENGTHS = {
    "objectives_fr": 645, "prerequisites_fr": 119, "theory_fr": 7772,
    "theory_ar": 204, "example_fr": 490, "code_example": 174,
    "exercise_fr": 241, "solution_fr": 275, "summary_fr": 455,
    "revision_fr": 265,
}

OBJECTIVES = [
    "Définir un algorithme et expliquer les critères de finitude, de précision et d’effectivité.",
    "Décomposer un problème en données d’entrée, traitements, contraintes et résultats attendus.",
    "Déclarer et initialiser des variables, choisir leurs types et distinguer affectation et comparaison.",
    "Construire des traitements séquentiels, conditionnels et répétitifs adaptés à un énoncé.",
    "Tracer une exécution et justifier l’évolution des variables à chaque instruction.",
    "Détecter les erreurs d’initialisation, de logique, de bornes et de terminaison, y compris dans les cas limites.",
]
PREREQUISITES = (
    "Savoir lire un énoncé, effectuer les quatre opérations, comparer des nombres, "
    "reconnaître une condition vraie ou fausse et suivre une suite d’instructions simples."
)
THEORY = r'''1. Définition d’un algorithme
Un algorithme est une suite finie et ordonnée d’instructions non ambiguës qui transforme des données en résultats pour résoudre un problème. Il décrit une méthode indépendante du langage de programmation.

Un algorithme doit respecter trois propriétés essentielles :
• Finitude : il termine après un nombre fini d’étapes pour toute donnée appartenant au domaine prévu.
• Précision : chaque instruction est suffisamment claire pour être exécutée sans interprétation.
• Effectivité : chaque opération demandée est réalisable en un nombre fini d’opérations élémentaires.
La correction signifie en plus que le résultat produit respecte la spécification du problème.

2. Analyser l’énoncé : entrées, traitements et sorties
Avant d’écrire le pseudo-code, identifier :
• Entrées : les informations fournies (valeurs, tableau, nombre d’éléments).
• Contraintes : les conditions que ces informations doivent respecter.
• Traitements : les calculs, comparaisons et répétitions nécessaires.
• Sorties : les résultats à afficher ou à retourner.

Exemple — moyenne de trois notes : entrées n1, n2 et n3; contrainte éventuelle 0 ≤ ni ≤ 20; traitement moyenne ← (n1+n2+n3)/3; sortie : moyenne. Il faut aussi préciser si les notes sont supposées valides ou si l’algorithme doit les contrôler.

3. Variables, constantes et types
Une variable est un nom associé à une valeur susceptible de changer pendant l’exécution. Une constante désigne une valeur qui reste fixe dans le traitement considéré. Déclarer une variable revient à préciser son nom et, selon la notation utilisée, son type.

Types courants :
• ENTIER : 0, 12, -5; pour un nombre entier.
• RÉEL : 3.14, -2.5; pour une valeur pouvant comporter une partie décimale.
• CARACTÈRE : 'A'; pour un caractère.
• CHAÎNE : "Bonjour"; pour un texte.
• BOOLÉEN : VRAI ou FAUX; pour le résultat d’un test.

Une variable doit recevoir une valeur avant toute utilisation qui dépend de cette valeur. Le type choisi doit être compatible avec les opérations prévues.

4. Affectation et opérateurs
L’affectation se note ← : on évalue d’abord l’expression à droite, puis on range son résultat dans la variable à gauche. Ainsi, si x ← 3 puis x ← x + 4, la seconde instruction lit l’ancienne valeur de x, calcule 7 et remplace x par 7. Ce n’est pas une égalité mathématique.

Opérateurs arithmétiques : +, -, *, /, DIV (quotient entier) et MOD (reste de la division entière). Exemple : 17 DIV 5 = 3 et 17 MOD 5 = 2.
Opérateurs de comparaison : =, ≠, <, >, ≤ et ≥. Leur résultat est booléen.
Opérateurs logiques : ET, OU et NON. Exemple : 0 ≤ note ET note ≤ 20 teste l’appartenance à l’intervalle fermé [0,20].

5. Structure séquentielle
Dans une séquence, les instructions s’exécutent une seule fois, dans l’ordre écrit. Une instruction utilise les valeurs produites par les instructions précédentes.

LIRE a
LIRE b
somme ← a + b
AFFICHER somme

Si a=6 et b=4, somme devient 10. Inverser ou supprimer une instruction peut changer le résultat.

6. Structures conditionnelles
Une condition choisit les instructions à exécuter selon le résultat VRAI ou FAUX d’une expression booléenne.

SI condition ALORS
    instructions_si_vrai
SINON
    instructions_si_faux
FIN SI

La branche SINON est facultative. Pour plusieurs cas, on peut utiliser SINON SI. Les cas doivent être ordonnés et couvrir les situations attendues sans chevauchement involontaire.

Exemple :
SI note < 10 ALORS
    AFFICHER "Non admis"
SINON
    AFFICHER "Admis"
FIN SI

Pour une classification par seuils, tester les seuils du plus élevé au plus faible ou construire des intervalles disjoints. Tester d’abord note ≥ 10 rendrait les tests suivants inaccessibles si l’on voulait distinguer plusieurs mentions.

7. Structures répétitives
Une boucle répète un bloc d’instructions. Le choix dépend de la connaissance du nombre d’itérations et du moment où la condition est testée.
• POUR : adaptée à un nombre d’itérations déterminé, souvent piloté par un compteur.
• TANT QUE : teste la condition avant le corps; zéro itération est possible.
• RÉPÉTER ... JUSQU’À : teste après le corps; le corps s’exécute au moins une fois.

Toute boucle doit avoir une initialisation cohérente, une condition d’arrêt et une mise à jour qui permet d’atteindre cette condition. Une variable de contrôle qui ne change pas peut provoquer une boucle infinie. Vérifier si les bornes sont inclusives : POUR i de 1 à 5 inclus réalise cinq itérations.

8. Traçage manuel
Le traçage consiste à simuler les instructions dans leur ordre et à noter les valeurs après chaque affectation. Pour une condition, noter VRAI ou FAUX; pour une boucle, compter les tours et vérifier l’évolution de la condition.

Exemple : x ← 2; y ← x + 3; x ← y * 2. Après la première instruction x=2; après la deuxième y=5; après la troisième x=10. La valeur finale de y reste 5.

Une table de trace peut contenir : numéro d’étape, instruction, x, y, résultat du test et sortie. Elle permet de repérer une mauvaise initialisation, une affectation oubliée ou une erreur de borne.

9. Méthode complète de résolution
1) Reformuler précisément ce qui est demandé.
2) Lister les entrées, sorties et contraintes.
3) Définir les variables, leurs types et leurs valeurs initiales.
4) Décomposer le traitement en étapes simples.
5) Choisir séquence, condition et/ou boucle.
6) Écrire le pseudo-code avec une indentation lisible.
7) Tracer un cas normal, un cas limite et, si nécessaire, une entrée invalide.
8) Vérifier le résultat, les bornes et la terminaison.

10. Erreurs classiques à éviter
• Utiliser une variable avant son initialisation.
• Confondre ← (affectation) et = (comparaison dans un test).
• Oublier de mettre à jour le compteur d’une boucle.
• Se tromper entre < et ≤ ou entre une borne incluse et exclue.
• Diviser par zéro lorsque l’effectif est nul.
• Ajouter la valeur sentinelle (par exemple -1) au calcul alors qu’elle sert uniquement à arrêter la saisie.
• Ne pas traiter le tableau vide ou une donnée hors domaine.

À retenir : un bon algorithme n’est pas seulement un code qui semble fonctionner sur un exemple; il doit respecter les contraintes, traiter les cas limites et terminer.'''
EXAMPLE = '''On cherche le maximum de trois réels a, b et c. On initialise maxi avec a, puis on compare successivement b et c à maxi. Si une valeur est supérieure, maxi est remplacé. Pour a=4, b=9 et c=2 : maxi vaut d’abord 4; le test 9>4 est vrai, donc maxi devient 9; le test 2>9 est faux, donc maxi reste 9. Le résultat affiché est 9.'''
CODE = '''ALGORITHME MaximumTroisNombres
VARIABLES a, b, c, maxi : REEL
DEBUT
    LIRE a, b, c
    maxi ← a
    SI b > maxi ALORS
        maxi ← b
    FIN SI
    SI c > maxi ALORS
        maxi ← c
    FIN SI
    AFFICHER maxi
FIN

# Version Python

def maximum_trois(a, b, c):
    maxi = a
    if b > maxi:
        maxi = b
    if c > maxi:
        maxi = c
    return maxi

print(maximum_trois(4, 9, 2))  # 9'''
MAIN_EXERCISE = '''On exécute l’algorithme du maximum avec a=4, b=9 et c=2. Présenter une table de trace indiquant, après chaque instruction, la valeur de maxi et le résultat de chaque comparaison. Donner la sortie finale et expliquer pourquoi elle est correcte.'''
MAIN_SOLUTION = '''Initialisation : maxi ← a, donc maxi=4. Première comparaison : b>maxi donne 9>4, soit VRAI; on affecte donc maxi←9. Deuxième comparaison : c>maxi donne 2>9, soit FAUX; maxi reste 9. La sortie est 9. Après le traitement de a et b, maxi contient leur maximum; la comparaison avec c conserve cette propriété pour les trois valeurs.'''
SUMMARY = '''Un algorithme est une suite finie, précise et effective d’instructions. Avant de l’écrire, identifier entrées, contraintes, traitements et sorties. Une variable stocke une valeur; ← affecte et les opérateurs de comparaison produisent VRAI ou FAUX. La séquence exécute dans l’ordre, SI/SINON choisit une branche et les boucles POUR, TANT QUE et RÉPÉTER-JUSQU’À répètent selon des règles différentes. Tracer les variables, vérifier les bornes et prévoir les cas limites permet de détecter les erreurs.'''
REVISION = '''À mémoriser : finitude, précision, effectivité; entrée / contrainte / traitement / sortie; variable / constante / type; affectation ← et comparaison =; DIV = quotient entier, MOD = reste; ET / OU / NON; SI / SINON; POUR / TANT QUE / RÉPÉTER-JUSQU’À. Pour chaque boucle, vérifier initialisation, condition, mise à jour et arrêt. Toujours tracer au moins un cas normal et un cas limite.'''

EXERCISES = {
    "Exercice guidé": {
        "prompt": "Trace l’algorithme du maximum pour a=4, b=9 et c=2. Complète les valeurs successives de maxi et indique VRAI ou FAUX pour chaque comparaison.",
        "solution": "maxi=4 après initialisation. 9>4 est VRAI : maxi devient 9. 2>9 est FAUX : maxi reste 9. Sortie : 9.",
        "guide": "Vérifier la valeur initiale (2 points), l’évaluation des deux tests (2 points), la mise à jour (2 points) et la conclusion justifiée (2 points).",
        "objective": "Tracer l’exécution et justifier l’évolution d’une variable.", "level": "Moyen"},
    "Application : contrôle de saisie": {
        "prompt": "Écris un pseudo-code qui lit des notes jusqu’à la saisie de -1. Il ignore toute note hors de [0,20], compte les notes valides et calcule leur moyenne. La sentinelle -1 ne doit jamais entrer dans la somme. Prévois le cas où aucune note valide n’a été saisie.",
        "solution": "somme←0; compteur←0; LIRE note; TANT QUE note≠-1 FAIRE; SI 0≤note ET note≤20 ALORS somme←somme+note; compteur←compteur+1; FIN SI; LIRE note; FIN TANT QUE; SI compteur>0 ALORS AFFICHER somme/compteur SINON AFFICHER 'Aucune note valide' FIN SI. La lecture suivante dans la boucle et l’exclusion de -1 assurent l’arrêt et évitent de compter la sentinelle.",
        "guide": "Initialisation (2), condition d’arrêt (2), validation inclusive des bornes (2), mise à jour somme/compteur (2), traitement compteur nul (2).",
        "objective": "Construire une boucle avec validation, sentinelle et cas limite.", "level": "Moyen"},
    "Débutant — repérer la notion": {
        "prompt": "Pour calculer la moyenne de quatre notes, identifie les entrées, le traitement, la sortie et une contrainte possible sur les notes. Explique chaque élément en une phrase.",
        "solution": "Entrées : les quatre notes. Traitement : additionner les notes puis diviser la somme par 4. Sortie : la moyenne. Contrainte possible : chaque note appartient à [0,20].",
        "guide": "Un point pour chaque élément correctement identifié et un point pour une explication claire.",
        "objective": "Décomposer un problème en entrées, traitement, sortie et contraintes.", "level": "Débutant"},
    "Élémentaire — expliquer la démarche": {
        "prompt": "On donne x←5 puis x←x+2 puis y←2*x. Donne la valeur de x et de y après chaque instruction. Explique pourquoi x←x+2 n’est pas une égalité mathématique.",
        "solution": "Après x←5 : x=5. Après x←x+2 : l’ancienne valeur 5 est augmentée de 2, donc x=7. Après y←2*x : y=14 et x reste 7. La flèche indique une affectation qui remplace la valeur stockée; ce n’est pas une équation à résoudre.",
        "guide": "Valeurs intermédiaires correctes (3), explication de l’affectation (2).",
        "objective": "Distinguer affectation et égalité et tracer des variables.", "level": "Élémentaire"},
    "Intermédiaire — transférer": {
        "prompt": "Écris un algorithme qui parcourt un tableau de notes et compte combien sont strictement supérieures ou égales à 10. Teste-le sur [8,10,13,7,10] et donne la valeur du compteur après chaque élément.",
        "solution": "compteur←0; POUR chaque note du tableau : SI note≥10 ALORS compteur←compteur+1 FIN SI; FIN POUR; AFFICHER compteur. Trace : 8→0; 10→1; 13→2; 7→2; 10→3. Sortie : 3.",
        "guide": "Initialisation à zéro (1), boucle complète (2), condition inclusive ≥10 (2), trace (3), résultat (1).",
        "objective": "Combiner boucle, condition et compteur.", "level": "Intermédiaire"},
    "Avancé — diagnostiquer une erreur": {
        "prompt": "Analyse : i←1; TANT QUE i≤5 FAIRE AFFICHER i FIN TANT QUE. Explique pourquoi l’algorithme ne termine pas. Propose une correction et précise les valeurs affichées.",
        "solution": "i ne change jamais dans le corps. La condition i≤5 reste donc vraie avec i=1 et la boucle est infinie. Ajouter i←i+1 après AFFICHER i. L’algorithme affiche alors 1,2,3,4,5 puis s’arrête lorsque i devient 6.",
        "guide": "Identifier la variable non mise à jour (2), expliquer la condition toujours vraie (2), proposer la mise à jour (2), donner la trace et l’arrêt (2).",
        "objective": "Diagnostiquer une boucle non terminante et la corriger.", "level": "Avancé"},
    "Défi concours — synthèse argumentée": {
        "prompt": "Écris un algorithme qui lit exactement 5 entiers, calcule leur somme et détermine le plus grand. Présente les entrées, les variables initialisées, le pseudo-code et une trace sur 4, 9, 2, 9, -1. Explique le traitement des égalités et des nombres négatifs.",
        "solution": "LIRE la première valeur; somme←valeur; maxi←valeur. POUR i de 2 à 5 : LIRE valeur; somme←somme+valeur; SI valeur>maxi ALORS maxi←valeur FIN SI; FIN POUR; AFFICHER somme, maxi. Sur 4,9,2,9,-1 : somme successive 4,13,15,24,23; maxi successif 4,9,9,9,9. Sorties : somme=23 et maximum=9. Initialiser avec la première valeur permet de traiter correctement un tableau composé uniquement de nombres négatifs; utiliser > conserve le premier maximum en cas d’égalité, sans changer la valeur maximale.",
        "guide": "Entrées et variables (2), initialisation robuste (2), boucle de 4 lectures restantes (2), somme et maximum (2), trace et justification des égalités/négatifs (2).",
        "objective": "Mobiliser séquence, boucle, condition, accumulation et maximum dans un problème complet.", "level": "Défi concours"},
}

app = create_app()
with app.app_context():
    db_path = Path(db.engine.url.database).resolve()
    if db_path.name != EXPECTED_DB or db_path.parent.name != "instance":
        raise SystemExit(f"STOP: base inattendue: {db_path}. Aucun changement.")
    if not db_path.exists():
        raise SystemExit(f"STOP: base introuvable: {db_path}")

    subject = CurriculumSubject.query.filter_by(name="Algorithmique").one_or_none()
    module = CurriculumModule.query.filter_by(subject_id=subject.id, title="Construire un algorithme").one_or_none() if subject else None
    chapter = CurriculumChapter.query.filter_by(module_id=module.id, title="Données, conditions et itérations").one_or_none() if module else None
    lesson = CurriculumLesson.query.filter_by(chapter_id=chapter.id, title="Écrire et tracer un algorithme").one_or_none() if chapter else None
    if lesson is None:
        raise SystemExit("STOP: leçon cible absente ou ambiguë. Aucun changement.")

    current = {field: len(getattr(lesson, field) or "") for field in EXPECTED_LENGTHS}
    if current != EXPECTED_LENGTHS:
        raise SystemExit(f"STOP: contenu modifié depuis la dernière vérification. Longueurs actuelles={current}. Aucun changement.")

    exercises = CourseExercise.query.filter_by(lesson_id=lesson.id, published=True).all()
    by_title = {ex.title: ex for ex in exercises}
    missing = sorted(set(EXERCISES) - set(by_title))
    if missing:
        raise SystemExit(f"STOP: exercices attendus introuvables: {missing}. Aucun changement.")
    # Preserve old exercise rows and every submitted attempt. The old versions
    # will be unpublished; fresh rows with the improved prompts become active.
    exercise_ids = [by_title[t].id for t in EXERCISES]
    attempts = ExerciseAttempt.query.filter(ExerciseAttempt.exercise_id.in_(exercise_ids)).count()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = db_path.with_name(f"{db_path.stem}_before_complete_lesson_{stamp}.db")
    with sqlite3.connect(str(db_path)) as src, sqlite3.connect(str(backup)) as dst:
        src.backup(dst)

    try:
        lesson.objectives_fr = json.dumps(OBJECTIVES, ensure_ascii=False)
        lesson.prerequisites_fr = PREREQUISITES
        lesson.theory_fr = THEORY
        lesson.example_fr = EXAMPLE
        lesson.code_example = CODE
        lesson.exercise_fr = MAIN_EXERCISE
        lesson.solution_fr = MAIN_SOLUTION
        lesson.summary_fr = SUMMARY
        lesson.revision_fr = REVISION
        # Keep the existing Darija support field unchanged; the platform's course content is French-first.
        for title, data in EXERCISES.items():
            old_ex = by_title[title]
            old_ex.published = False
            replacement = CourseExercise(
                lesson_id=lesson.id,
                title=title,
                prompt_fr=data["prompt"],
                prompt_ar="",
                solution_fr=data["solution"],
                solution_ar="",
                exercise_type="open",
                options_json="[]",
                accepted_answers_json="[]",
                feedback_fr=data["solution"],
                grading_guide_fr=data["guide"],
                learning_objective_fr=data["objective"],
                level=data["level"],
                published=True,
            )
            db.session.add(replacement)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    db.session.refresh(lesson)
    print("SUCCESS: complete first-lesson refresh applied.")
    print(f"Database: {db_path}")
    print(f"Backup:   {backup}")
    print(f"Lesson:   {lesson.title}")
    print(f"Theory:   {len(lesson.theory_fr)} characters")
    print(f"New active exercises created: {len(EXERCISES)}")
    print(f"Previous exercise versions archived: {len(EXERCISES)}")
    print(f"Existing attempts preserved: {attempts}")
    print("QCM, other lessons, student progress, and submitted answers were not deleted or rewritten.")
