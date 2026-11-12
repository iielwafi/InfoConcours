"""
Safe, targeted repair for the first Algorithmique lesson in InfoConcours.

Run from the project root:
    python repair_first_lesson_quality.py

This script:
- disables automatic content seeding before importing app.py;
- backs up the configured SQLite database;
- removes only the accidental trailing "Copier le code" / "نسخ الرمز"
  text from the lesson's stored Python code example;
- assigns a specific learning objective to each of the 8 QCM questions
  attached to the chapter "Données, conditions et itérations";
- preserves all exercise attempts, QCM attempts, progress, and other lessons.
"""

import os
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

# Prevent app.py from running seed_questions() during import.
os.environ["APP_ENV"] = "development"
os.environ["AUTO_SEED_CONTENT"] = "0"
os.environ["AUTO_CREATE_SCHEMA"] = "0"

from app import (
    app,
    db,
    CurriculumSubject,
    CurriculumModule,
    CurriculumChapter,
    CurriculumLesson,
    Question,
    QuestionMetadata,
)

OBJECTIVES_BY_PROMPT = {
    "Quelle valeur affiche x après x": (
        "Exécuter une suite d’affectations et déterminer la valeur finale d’une variable."
    ),
    "Combien de fois le corps s’exécute-t-il": (
        "Déterminer le nombre d’itérations d’une boucle POUR avec des bornes inclusives."
    ),
    "Quelle structure convient pour choisir entre trois cas": (
        "Choisir une structure conditionnelle adaptée à plusieurs cas exclusifs."
    ),
    "Dans une boucle TANT QUE, quand le test est-il évalué": (
        "Distinguer le moment d’évaluation de la condition dans une boucle TANT QUE."
    ),
    "Quelle valeur finale de s": (
        "Tracer une accumulation dans une boucle et calculer la somme finale."
    ),
    "Une note n est valide de 0 à 20 inclus": (
        "Écrire une condition logique qui vérifie un intervalle fermé."
    ),
    "On initialise somme à 0 puis on ajoute chaque valeur": (
        "Comprendre le nombre d’itérations et d’accumulations lors du parcours d’un tableau."
    ),
    "Pour compter les valeurs positives d’un tableau": (
        "Initialiser et utiliser correctement un compteur dans un parcours de tableau."
    ),
}


def sqlite_database_path(database_uri: str, instance_path: str) -> Path:
    prefix = "sqlite:///"
    if not database_uri.startswith(prefix):
        raise RuntimeError(
            "La base configurée n'est pas SQLite. Aucun changement n'a été effectué."
        )

    raw_path = database_uri[len(prefix):]
    path = Path(raw_path)

    # Flask-SQLAlchemy resolves relative SQLite paths from app.instance_path.
    if not path.is_absolute():
        path = Path(instance_path) / path

    return path.resolve()


def main():
    with app.app_context():
        db_path = sqlite_database_path(
            str(app.config["SQLALCHEMY_DATABASE_URI"]),
            app.instance_path,
        )

        if not db_path.exists():
            raise FileNotFoundError(
                f"Base introuvable : {db_path}\n"
                "Aucun fichier n'a été créé ni modifié."
            )

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = db_path.with_name(
            f"{db_path.stem}_before_quality_repair_{stamp}{db_path.suffix}"
        )

        # SQLite's backup API produces a consistent copy.
        source = sqlite3.connect(str(db_path))
        backup = sqlite3.connect(str(backup_path))
        try:
            source.backup(backup)
        finally:
            backup.close()
            source.close()

        subject = CurriculumSubject.query.filter_by(
            slug="algorithmique"
        ).first()

        if not subject:
            raise RuntimeError("Matière 'algorithmique' introuvable.")

        module = CurriculumModule.query.filter_by(
            subject_id=subject.id,
            title="Construire un algorithme",
        ).first()

        if not module:
            raise RuntimeError("Module 'Construire un algorithme' introuvable.")

        chapter = CurriculumChapter.query.filter_by(
            module_id=module.id,
            title="Données, conditions et itérations",
        ).first()

        if not chapter:
            raise RuntimeError("Chapitre 'Données, conditions et itérations' introuvable.")

        lesson = CurriculumLesson.query.filter_by(
            chapter_id=chapter.id,
            title="Écrire et tracer un algorithme",
        ).first()

        if not lesson:
            raise RuntimeError("Leçon 'Écrire et tracer un algorithme' introuvable.")

        original_code = lesson.code_example or ""
        cleaned_code = re.sub(
            r"[ \t]*(?:Copier le code|نسخ الرمز)\s*$",
            "",
            original_code,
            flags=re.IGNORECASE,
        ).rstrip()

        # Prepare and validate all metadata changes before committing.
        metadata_rows = (
            QuestionMetadata.query
            .filter_by(chapter_id=chapter.id)
            .all()
        )

        question_by_id = {
            q.id: q
            for q in Question.query.filter(
                Question.id.in_([m.question_id for m in metadata_rows])
            ).all()
        }

        objective_updates = []
        matched_prompts = set()

        for metadata in metadata_rows:
            question = question_by_id.get(metadata.question_id)
            if not question:
                continue

            prompt = (question.prompt_fr or "").strip()
            matched_key = next(
                (key for key in OBJECTIVES_BY_PROMPT if prompt.startswith(key)),
                None,
            )

            if matched_key:
                objective_updates.append(
                    (metadata, OBJECTIVES_BY_PROMPT[matched_key], prompt)
                )
                matched_prompts.add(matched_key)

        missing = set(OBJECTIVES_BY_PROMPT) - matched_prompts
        if missing:
            raise RuntimeError(
                "Certaines questions QCM attendues sont introuvables. "
                "Aucune modification n'a été validée.\n"
                + "\n".join(sorted(missing))
            )

        try:
            lesson.code_example = cleaned_code

            for metadata, objective, _prompt in objective_updates:
                metadata.learning_objective = objective

            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        print("SUCCESS: réparation ciblée terminée.")
        print(f"Base : {db_path}")
        print(f"Sauvegarde : {backup_path}")
        print(f"Leçon : {lesson.title}")
        print(
            "Code : "
            + ("nettoyé" if cleaned_code != original_code else "déjà propre")
        )
        print(f"Objectifs QCM corrigés : {len(objective_updates)}")
        print("Tentatives d'exercices et QCM : conservées.")
        print("Progression des apprenants : conservée.")
        print("Autres leçons et exercices : non modifiés.")


if __name__ == "__main__":
    main()
