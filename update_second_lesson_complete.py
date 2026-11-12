
from __future__ import annotations
import json, os, sqlite3
from datetime import datetime
from pathlib import Path

# Run from project root: python update_second_lesson_complete.py
os.environ["AUTO_SEED_CONTENT"] = "0"
from app import create_app, db, CurriculumSubject, CurriculumModule, CurriculumChapter, CurriculumLesson, CourseExercise, ExerciseAttempt

EXPECTED_DB = "infoconcours-phase8-dev.db"
OBJECTIVES = [
    "Distinguer les boucles POUR, TANT QUE et RÉPÉTER-JUSQU’À selon le moment du test.",
    "Calculer le nombre d’itérations d’une boucle simple en tenant compte des bornes et du pas.",
    "Déterminer le nombre total d’exécutions d’une boucle imbriquée.",
    "Construire une table de trace pour suivre les compteurs et les variables.",
    "Formuler un invariant simple et vérifier son initialisation et sa conservation.",
    "Identifier les conditions nécessaires à la terminaison d’une boucle."
]
PREREQUISITES = "Maîtriser les variables, l’affectation, les comparaisons, les conditions, les boucles simples et le traçage manuel."

THEORY = """1. Rôle des structures répétitives
Une boucle permet d’exécuter plusieurs fois un même bloc d’instructions. Elle évite de recopier les mêmes instructions et convient au traitement de séries de valeurs, au parcours de tableaux et aux calculs répétés.

2. Les trois structures répétitives
• POUR : adaptée lorsque le nombre d’itérations est connu ou déterminé par un compteur.
• TANT QUE : la condition est testée avant le corps. Si elle est fausse au départ, le corps est exécuté zéro fois.
• RÉPÉTER ... JUSQU’À : la condition d’arrêt est testée après le corps. Le corps est donc exécuté au moins une fois.

Il faut préciser si les bornes sont incluses. Avec un pas de 1 et les bornes entières incluses, POUR i DE 1 À 5 prend les valeurs 1, 2, 3, 4 et 5 : cinq itérations. Avec un pas de 2, POUR i DE 0 À 10 prend 0, 2, 4, 6, 8 et 10 : six itérations.

3. Calculer le nombre d’itérations
Énumérer les valeurs du compteur en tenant compte de la valeur initiale, de la borne finale, du sens et du pas. Ne pas appliquer mécaniquement une formule si le pas ou les bornes changent.

4. Boucles imbriquées
Une boucle est imbriquée lorsqu’elle se trouve dans le corps d’une autre boucle. Si la boucle extérieure effectue n itérations et que la boucle intérieure en effectue m à chaque tour extérieur, le corps intérieur est exécuté n × m fois.

Exemple :
POUR i DE 1 À 3
    POUR j DE 1 À 4
        compteur ← compteur + 1
    FIN POUR
FIN POUR

La boucle extérieure effectue 3 tours et la boucle intérieure 4 tours pour chacun. L’incrémentation est donc exécutée 3 × 4 = 12 fois. Si compteur est initialisé à 0, sa valeur finale est 12. À chaque nouveau tour de i, j recommence à sa valeur initiale.

La multiplication directe n’est valable que si le nombre de tours intérieurs est constant. Si les bornes de j dépendent de i, calculer séparément le nombre de tours pour chaque valeur de i, puis additionner.

5. Table de trace
Pour l’exemple précédent, les couples (i,j) sont :
(1,1), (1,2), (1,3), (1,4),
(2,1), (2,2), (2,3), (2,4),
(3,1), (3,2), (3,3), (3,4).
La table de trace permet de vérifier l’ordre des exécutions, la réinitialisation du compteur intérieur et l’évolution des variables.

6. Invariant de boucle
Un invariant est une propriété logique qui reste vraie à chaque étape de la boucle. Il permet de justifier le résultat calculé.
Pour démontrer un invariant :
• Initialisation : la propriété est vraie avant la première itération.
• Conservation : si elle est vraie au début d’une itération, les instructions la rendent encore vraie à la fin.
• Conclusion : à la sortie, l’invariant et la condition d’arrêt permettent de déduire le résultat.

Exemple : somme ← 0; POUR i DE 1 À n : somme ← somme + i.
Avant l’itération d’indice i, un invariant est : somme contient 1+2+...+(i−1). Après l’ajout de i, somme contient 1+2+...+i. À la fin, somme vaut 1+2+...+n.

7. Terminaison
Une boucle TANT QUE doit faire évoluer son état vers une situation où sa condition devient fausse. Les variables de contrôle doivent être initialisées et mises à jour correctement.
Algorithme incorrect :
i ← 1
TANT QUE i ≤ 5 FAIRE
    AFFICHER i
FIN TANT QUE
La variable i ne change jamais : la condition reste vraie et la boucle ne termine pas.
Correction :
i ← 1
TANT QUE i ≤ 5 FAIRE
    AFFICHER i
    i ← i + 1
FIN TANT QUE
Les valeurs affichées sont 1, 2, 3, 4 et 5. Ensuite i vaut 6 et la boucle s’arrête.

8. Erreurs fréquentes
• Oublier qu’une borne peut être incluse.
• Compter uniquement les tours de la boucle extérieure.
• Oublier que le compteur intérieur recommence à sa valeur initiale.
• Multiplier les nombres d’itérations alors que la boucle intérieure varie.
• Confondre un exemple vérifié avec un invariant démontré.
• Oublier ou mal orienter la mise à jour du compteur.
• Ne pas vérifier que la condition d’arrêt peut devenir fausse.

9. Méthode au concours
1) Repérer chaque boucle et son compteur.
2) Énumérer les valeurs successives et relever le pas.
3) Vérifier les bornes inclusives ou exclusives.
4) Pour les boucles imbriquées, calculer les tours intérieurs pour chaque tour extérieur.
5) Construire une table de trace si des variables sont modifiées.
6) Pour un invariant, vérifier l’initialisation et la conservation.
7) Pour la terminaison, examiner la condition et la mise à jour.

À retenir : pour deux boucles imbriquées de tailles constantes n et m, le corps intérieur s’exécute n × m fois. Si le nombre de tours intérieurs varie, on additionne les nombres de tours. Un invariant justifie la progression du calcul; l’étude de la condition et de sa mise à jour permet de raisonner sur la terminaison."""

EXAMPLE = "On initialise compteur à 0. La boucle extérieure prend i=1,2,3 et la boucle intérieure prend j=1,2,3,4 à chaque tour. Pour i=1, compteur passe de 0 à 4; pour i=2, de 4 à 8; pour i=3, de 8 à 12. Le corps intérieur est exécuté 3 × 4 = 12 fois."
CODE = """ALGORITHME CompterIterationsImbriquees
VARIABLES i, j, compteur : ENTIER
DEBUT
    compteur ← 0
    POUR i DE 1 À 3
        POUR j DE 1 À 4
            compteur ← compteur + 1
        FIN POUR
    FIN POUR
    AFFICHER compteur
FIN

# Résultat : 12

# Version Python
compteur = 0
for i in range(1, 4):
    for j in range(1, 5):
        compteur += 1
print(compteur)  # 12"""
MAIN_EXERCISE = "On exécute : compteur ← 0; POUR i DE 0 À 5; POUR j DE 1 À 2; compteur ← compteur + 1; FIN POUR; FIN POUR. Les bornes sont incluses et le pas vaut 1. Combien de fois l’incrémentation est-elle exécutée ? Présente les valeurs de i et j et donne la valeur finale de compteur."
MAIN_SOLUTION = "La boucle extérieure prend 0, 1, 2, 3, 4 et 5 : 6 itérations. Pour chaque valeur de i, la boucle intérieure prend 1 et 2 : 2 itérations. Le corps intérieur est donc exécuté 6 × 2 = 12 fois. Comme compteur commence à 0 et augmente de 1 à chaque exécution, sa valeur finale est 12."
SUMMARY = "POUR convient lorsque le nombre d’itérations est déterminé; TANT QUE teste avant le corps et peut effectuer zéro tour; RÉPÉTER-JUSQU’À teste après le corps et en effectue au moins un. Pour des boucles imbriquées de tailles constantes n et m, le corps intérieur s’exécute n×m fois. Si le nombre de tours intérieurs varie, on additionne les tours. Un invariant est vrai à l’initialisation et conservé à chaque itération. Pour garantir la terminaison, vérifier la condition et la mise à jour des variables de contrôle."
REVISION = "À mémoriser : bornes inclusives/exclusives; pas; POUR, TANT QUE, RÉPÉTER-JUSQU’À; boucles imbriquées; produit n×m si les tailles sont constantes; somme si les tailles varient; table de trace; invariant (initialisation, conservation, conclusion); terminaison et boucle infinie."

# title: (prompt, solution, grading guide, learning objective, level)
EXERCISES = {
"Débutant — compter une boucle": ("Une boucle POUR i DE 2 À 7 utilise un pas de 1 et des bornes incluses. Écris les valeurs successives de i et calcule le nombre d’itérations.", "i prend 2, 3, 4, 5, 6 et 7. Il y a 6 itérations.", "Valeurs successives (2), bornes incluses (2), nombre exact (2).", "Calculer le nombre d’itérations d’une boucle simple.", "Débutant"),
"Élémentaire — boucles imbriquées": ("Une boucle extérieure s’exécute 4 fois. À chaque tour, la boucle intérieure s’exécute 3 fois. Combien de fois l’instruction intérieure est-elle exécutée ? Justifie.", "4 × 3 = 12 exécutions, car les 3 tours intérieurs sont réalisés pour chacun des 4 tours extérieurs.", "Identifier les deux nombres (2), multiplication (2), résultat justifié (2).", "Calculer le nombre d’exécutions dans deux boucles imbriquées.", "Élémentaire"),
"Intermédiaire — table de trace": ("Trace : somme←0; POUR i DE 1 À 3; somme←somme+i; FIN POUR. Donne somme après chaque itération et le résultat final.", "Initialement somme=0. Après i=1 : 1; après i=2 : 3; après i=3 : 6. Résultat final : 6.", "Initialisation (1), trois mises à jour correctes (3), résultat (2).", "Construire une table de trace et suivre un accumulateur.", "Intermédiaire"),
"Intermédiaire — nombre variable d’itérations": ("Pour i de 1 à 4, la boucle intérieure exécute j de 1 à i inclus. Calcule le nombre total d’exécutions en détaillant chaque tour extérieur.", "i=1 : 1 tour; i=2 : 2; i=3 : 3; i=4 : 4. Total = 1+2+3+4 = 10. Le produit 4×4 ne convient pas car le nombre de tours intérieurs varie.", "Détail des quatre nombres (4), somme (2), justification (2).", "Analyser des boucles imbriquées à bornes variables.", "Intermédiaire"),
"Avancé — invariant": ("On initialise somme←0 puis, pour i de 1 à n, on exécute somme←somme+i. Propose un invariant avant l’itération i et explique sa conservation.", "Avant l’itération i : somme=1+2+...+(i−1), avec somme=0 pour i=1. Après l’ajout de i, somme=1+2+...+i : la propriété est conservée pour l’itération suivante.", "Invariant (3), initialisation (2), conservation (3).", "Formuler et justifier un invariant simple.", "Avancé"),
"Avancé — terminaison": ("Analyse : i←10; TANT QUE i>0 FAIRE; AFFICHER i; i←i+1; FIN TANT QUE. Explique le problème et corrige pour afficher 10 à 1.", "i augmente au lieu de diminuer. La condition i>0 reste vraie : la boucle ne termine pas. Remplacer i←i+1 par i←i−1 affiche 10, 9, ..., 1 puis i=0 et arrêt.", "Erreur (2), explication (2), correction (2), trace et arrêt (2).", "Diagnostiquer et corriger une boucle non terminante.", "Avancé"),
"Défi concours — synthèse": ("Pour i de 1 à 5, puis j de 0 à i inclus, on incrémente compteur. Détermine le nombre total d’exécutions et explique pourquoi 5×6 ne convient pas.", "Pour i=1 à 5, les nombres de tours intérieurs sont 2, 3, 4, 5 et 6. Total = 2+3+4+5+6 = 20. Le produit 5×6 supposerait six tours intérieurs à chaque tour extérieur, ce qui est faux.", "Détail des tours (5), somme (2), justification (3).", "Résoudre un dénombrement de boucles imbriquées à bornes variables.", "Défi concours")
}

def main():
    app = create_app()
    with app.app_context():
        db_path = Path(db.engine.url.database).resolve()
        if db_path.name != EXPECTED_DB or db_path.parent.name != "instance":
            raise SystemExit(f"STOP : base inattendue ({db_path}). Aucun changement.")
        if not db_path.is_file():
            raise SystemExit(f"STOP : base introuvable ({db_path}).")
        subject = CurriculumSubject.query.filter_by(name="Algorithmique").one_or_none()
        module = CurriculumModule.query.filter_by(subject_id=subject.id, title="Construire un algorithme").one_or_none() if subject else None
        chapter = CurriculumChapter.query.filter_by(module_id=module.id, title="Boucles imbriquées et invariants").one_or_none() if module else None
        lesson = CurriculumLesson.query.filter_by(chapter_id=chapter.id, title="Raisonner sur les répétitions").one_or_none() if chapter else None
        if lesson is None:
            raise SystemExit("STOP : leçon cible absente ou ambiguë. Aucun changement.")
        old = CourseExercise.query.filter_by(lesson_id=lesson.id, published=True).all()
        old_ids = [e.id for e in old]
        attempts = ExerciseAttempt.query.filter(ExerciseAttempt.exercise_id.in_(old_ids)).count() if old_ids else 0
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = db_path.with_name(f"{db_path.stem}_before_lesson2_{stamp}.db")
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
            for ex in old:
                ex.published = False
            for title, data in EXERCISES.items():
                prompt, solution, guide, objective, level = data
                db.session.add(CourseExercise(
                    lesson_id=lesson.id, title=title, prompt_fr=prompt, prompt_ar="",
                    solution_fr=solution, solution_ar="", exercise_type="open",
                    options_json="[]", accepted_answers_json="[]", feedback_fr=solution,
                    grading_guide_fr=guide, learning_objective_fr=objective,
                    level=level, published=True
                ))
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        print("SUCCESS : leçon 2 mise à niveau.")
        print(f"Base : {db_path}")
        print(f"Sauvegarde : {backup}")
        print(f"Leçon : {lesson.title}")
        print(f"Théorie : {len(lesson.theory_fr)} caractères")
        print(f"Nouveaux exercices actifs : {len(EXERCISES)}")
        print(f"Anciennes versions archivées : {len(old)}")
        print(f"Tentatives préservées : {attempts}")
        print("QCM, autres leçons et progression des apprenants non modifiés.")

if __name__ == "__main__":
    main()
