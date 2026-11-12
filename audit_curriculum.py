"""
Audit rapide et sans modification du contenu InfoConcours.
Depuis la racine du projet :
    python audit_curriculum.py

Ce script ne modifie aucune donnée et ne lance aucun seed.
"""
import os
os.environ["AUTO_SEED_CONTENT"] = "0"

from app import create_app, db, CurriculumSubject, CurriculumModule, CurriculumChapter, CurriculumLesson, CourseExercise

app = create_app()

with app.app_context():
    print("\n=== AUDIT CURRICULUM INFOCONCOURS ===")
    subjects = CurriculumSubject.query.order_by(CurriculumSubject.position).all()
    total_lessons = 0
    total_exercises = 0

    for subject in subjects:
        print(f"\nMATIÈRE : {subject.name}")
        modules = CurriculumModule.query.filter_by(subject_id=subject.id).order_by(CurriculumModule.position).all()
        for module in modules:
            print(f"  MODULE : {module.title}")
            chapters = CurriculumChapter.query.filter_by(module_id=module.id).order_by(CurriculumChapter.position).all()
            for chapter in chapters:
                lessons = CurriculumLesson.query.filter_by(chapter_id=chapter.id).order_by(CurriculumLesson.id).all()
                for lesson in lessons:
                    total_lessons += 1
                    exercises = CourseExercise.query.filter_by(lesson_id=lesson.id, published=True).all()
                    total_exercises += len(exercises)
                    fields = {
                        "objectifs": len(lesson.objectives_fr or ""),
                        "prérequis": len(lesson.prerequisites_fr or ""),
                        "théorie": len(lesson.theory_fr or ""),
                        "exemple": len(lesson.example_fr or ""),
                        "code": len(lesson.code_example or ""),
                        "exercice principal": len(lesson.exercise_fr or ""),
                        "solution": len(lesson.solution_fr or ""),
                        "résumé": len(lesson.summary_fr or ""),
                        "révision": len(lesson.revision_fr or ""),
                    }
                    # Repères indicatifs pour identifier rapidement les contenus courts.
                    missing = [name for name, size in fields.items() if size == 0]
                    short = [name for name, size in fields.items()
                             if size > 0 and size < (500 if name == "théorie" else 50)]
                    status = "À COMPLÉTER" if missing or short else "CONTENU PRÉSENT"
                    print(f"    - {lesson.title} | {status}")
                    print(f"      théorie={fields['théorie']} caractères | exercices actifs={len(exercises)}")
                    if missing:
                        print("      champs vides : " + ", ".join(missing))
                    if short:
                        print("      champs courts : " + ", ".join(short))

    print("\n=== TOTAL ===")
    print(f"Matières : {len(subjects)}")
    print(f"Leçons : {total_lessons}")
    print(f"Exercices actifs : {total_exercises}")
    print("AUDIT TERMINÉ — aucune donnée n'a été modifiée.")
