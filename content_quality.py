"""Evidence-based audits for seeded and administrator-authored academy lessons."""
import json
import re


LEVELS = ("Débutant", "Élémentaire", "Intermédiaire", "Avancé", "Défi concours")


def audit_lesson(lesson, chapter, exercises, verified_video_count=0):
    """Return measurable gaps; structural checks are not a claim of pedagogical accuracy."""
    objectives = [x for x in _json_list(lesson.objectives_fr) if len(x.strip()) >= 12]
    corrections = sum(1 for e in exercises if len((e.solution_fr or "").strip()) >= 120 and len((e.learning_objective_fr or "").strip()) >= 20 and len((e.grading_guide_fr or "").strip()) >= 40)
    theory_words=len(re.findall(r"\b[\wÀ-ÿœŒ’-]+\b",(lesson.theory_fr or ""),re.UNICODE))
    full_text=" ".join([lesson.title or "",lesson.objectives_fr or "",lesson.prerequisites_fr or "",lesson.theory_fr or "",lesson.example_fr or "",lesson.code_example or "",lesson.exercise_fr or "",lesson.solution_fr or "",lesson.summary_fr or "",lesson.revision_fr or ""]+[(e.title or "")+" "+(e.learning_objective_fr or "")+" "+(e.prompt_fr or "")+" "+(e.solution_fr or "") for e in exercises])
    course_words=len(re.findall(r"\b[\wÀ-ÿœŒ’-]+\b",full_text,re.UNICODE))
    fields = {
        "objectifs mesurables": len(objectives) >= 5,
        "prérequis": len((lesson.prerequisites_fr or "").strip()) >= 30,
        "théorie détaillée (cible 1 500 mots)": len((lesson.theory_fr or "").strip()) >= 2600 and theory_words >= 1500,
        "vocabulaire défini": _has_section(lesson.theory_fr, "vocabulaire et définitions") and _has_section(lesson.theory_fr, "terme") or _has_section(lesson.theory_fr, "définitions importantes"),
        "démonstration pas à pas": _has_section(lesson.theory_fr, "démonstration pas à pas") and len((lesson.theory_fr or "").split()) >= 400,
        "exemples pratiques": _count_examples(lesson) >= 3,
        "applications réelles": _has_section(lesson.theory_fr, "applications"),
        "erreurs fréquentes": _has_section(lesson.theory_fr, "erreurs fréquentes"),
        "conseils concours": _has_section(lesson.theory_fr, "conseil") or _has_section(lesson.theory_fr, "examen"),
        "exercices progressifs": all(any(e.level == level and len((e.prompt_fr or "").strip()) >= 80 and len((e.learning_objective_fr or "").strip()) >= 20 for e in exercises) for level in LEVELS),
        "corrections détaillées": corrections >= 5,
        "vidéo dédiée vérifiée": verified_video_count > 0,
        "résumé": len((lesson.summary_fr or "").strip()) >= 60,
        "fiche de révision": len((lesson.revision_fr or "").strip()) >= 60,
    }
    missing = [name for name, passed in fields.items() if not passed]
    return {
        "lesson": lesson,
        "chapter": chapter,
        "fields": fields,
        "missing": missing,
        "complete": not missing,
        # Automated checks cannot validate correctness or age-appropriateness.
        "expert_review": True,
        "exercise_count": len(exercises),
        "detailed_correction_count": corrections,
        "word_count": course_words,
        "theory_word_count": theory_words,
        "distinct_example_count": _count_examples(lesson),
        "verified_video_count": verified_video_count,
    }


def _json_list(value):
    try:
        data = json.loads(value or "[]")
        return data if isinstance(data, list) else []
    except (TypeError, ValueError):
        return []


def _count_examples(lesson):
    text = "\n".join((lesson.example_fr or "", lesson.code_example or ""))
    return sum(1 for marker in ("Exemple 1", "Exemple 2", "Exemple 3") if marker.casefold() in text.casefold())


def _has_section(text, marker):
    return marker.casefold() in (text or "").casefold()


def split_lesson_sections(text):
    """Split authored plain-text lesson theory into safe heading/body pairs."""
    sections=[]
    heading="Cours"
    body=[]
    for line in (text or "").splitlines():
        stripped=line.strip()
        letters=[c for c in stripped if c.isalpha()]
        is_heading=bool(stripped and len(stripped)<=100 and len(letters)>=3 and stripped==stripped.upper() and not stripped.startswith(("•","-","*")))
        if is_heading:
            if body:
                sections.append((heading,"\n".join(body).strip()))
            heading=stripped.title()
            body=[]
        else:
            body.append(line)
    if body:
        sections.append((heading,"\n".join(body).strip()))
    return [(title,body) for title,body in sections if body]
