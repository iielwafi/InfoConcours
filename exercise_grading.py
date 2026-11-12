"""Safe, server-side grading helpers for curriculum exercises.

Open responses are never graded by textual similarity. Without a configured AI
provider, they remain pending teacher review.
"""
from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from urllib.error import URLError
from urllib.request import Request, urlopen


CONFIDENCE_THRESHOLD = 0.70
MAX_TIMEOUT_SECONDS = 20


def normalize_short_answer(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value).casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = "".join(char if char.isalnum() else " " for char in value)
    return " ".join(value.split())


def _numeric_value(value: str):
    text = str(value).strip().replace("−", "-").replace("٫", ".")
    if not re.fullmatch(r"[-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][-+]?\d+)?", text):
        return None
    try:
        number = Decimal(text.replace(",", "."))
        return number if number.is_finite() else None
    except InvalidOperation:
        return None


def short_answer_matches(submitted: str, accepted: list[str]) -> bool:
    normalized = normalize_short_answer(submitted)
    submitted_number = _numeric_value(submitted)
    for candidate in accepted:
        if normalized == normalize_short_answer(candidate):
            return True
        candidate_number = _numeric_value(candidate)
        if submitted_number is not None and candidate_number is not None and submitted_number == candidate_number:
            return True
    return False


def ai_grading_configured() -> bool:
    provider = os.environ.get("EXERCISE_GRADING_PROVIDER", "openai").strip().lower()
    return provider == "openai" and bool(os.environ.get("OPENAI_API_KEY", "").strip())


def _extract_response_text(payload: dict) -> str:
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                return content["text"]
    raise ValueError("Missing text output")


def _validate_ai_result(result) -> dict:
    if isinstance(result, str):
        result = json.loads(result)
    if not isinstance(result, dict):
        raise ValueError("Invalid evaluation object")
    score = result.get("score")
    confidence = result.get("confidence")
    category = result.get("classification")
    explanation = result.get("explanation_fr")
    missing = result.get("missing_concepts", [])
    expected = result.get("expected_answer_fr", "")
    if isinstance(score, bool) or not isinstance(score, (float, int)) or not math.isfinite(score) or not 0 <= score <= 100:
        raise ValueError("Invalid score")
    if isinstance(confidence, bool) or not isinstance(confidence, (float, int)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError("Invalid confidence")
    if category not in {"correct", "partially_correct", "incorrect"}:
        raise ValueError("Invalid classification")
    if not isinstance(explanation, str) or not explanation.strip() or len(explanation) > 2000:
        raise ValueError("Invalid explanation")
    if not isinstance(missing, list) or len(missing) > 20 or any(not isinstance(item, str) or len(item) > 300 for item in missing):
        raise ValueError("Invalid missing concepts")
    if not isinstance(expected, str) or len(expected) > 4000:
        raise ValueError("Invalid expected answer")
    return {"score": float(score), "confidence": float(confidence), "classification": category,
            "explanation_fr": explanation.strip(), "missing_concepts": [x.strip() for x in missing if x.strip()],
            "expected_answer_fr": expected.strip()}


def evaluate_open_answer(exercise, submitted_answer: str, evaluator=None) -> dict:
    """Call configured AI (or an injected test evaluator); return validated fields."""
    if evaluator is not None:
        return _validate_ai_result(evaluator(exercise, submitted_answer))
    if not ai_grading_configured():
        raise RuntimeError("not_configured")

    endpoint = os.environ.get("EXERCISE_GRADING_API_URL", "https://api.openai.com/v1/responses").strip()
    if not endpoint.startswith("https://"):
        raise RuntimeError("invalid_endpoint")
    model = os.environ.get("EXERCISE_GRADING_MODEL", "gpt-4o-mini").strip()
    if not model or len(model) > 100:
        raise RuntimeError("invalid_model")
    instructions = (
        "Tu es un correcteur pédagogique prudent pour des exercices d’informatique. "
        "Évalue le sens, les concepts essentiels, le raisonnement, la méthode, la pertinence "
        "et l’objectif pédagogique; n’exige pas les mêmes mots que le corrigé. N’invente pas "
        "de critères. Si l’énoncé, la solution ou la réponse ne permettent pas une évaluation "
        "fiable, choisis une confiance basse. Réponds uniquement avec un objet JSON : "
        '{"score":number 0..100,"classification":"correct|partially_correct|incorrect",'
        '"explanation_fr":"...","missing_concepts":["..."],"expected_answer_fr":"...",'
        '"confidence":number 0..1}.'
    )
    content = {
        "title": exercise.title,
        "question": exercise.prompt_fr,
        "expected_solution": exercise.solution_fr,
        "rubric": exercise.grading_guide_fr or "",
        "learning_objective": exercise.learning_objective_fr or "",
        "student_answer": submitted_answer,
    }
    body = json.dumps({"model": model, "instructions": instructions,
                       "input": json.dumps(content, ensure_ascii=False),
                       "text": {"format": {"type": "json_object"}}, "max_output_tokens": 700}, ensure_ascii=False).encode("utf-8")
    request = Request(endpoint, data=body, headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"].strip(),
                                                    "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=MAX_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read(128_000).decode("utf-8"))
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("provider_unavailable") from exc
    return _validate_ai_result(_extract_response_text(payload))
