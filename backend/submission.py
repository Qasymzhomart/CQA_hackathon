from __future__ import annotations

from typing import Any

from ai_analytics.schemas import AIEvaluation


OFFICIAL_ID_MAP = {
    "contact": "contact",
    "needs": "discovery",
    "identification": "identification",
    "consultation": "consultation",
    "empathy": "empathy",
    "dialog": "dialogue",
    "closing": "closure",
    "gross_errors": "critical",
}

OFFICIAL_IDS = [
    "contact",
    "discovery",
    "identification",
    "consultation",
    "empathy",
    "dialogue",
    "closure",
    "critical",
]

ALLOWED_VALUES = {
    "contact": {True, False},
    "discovery": {True, False, None},
    "identification": {True, False, None},
    "consultation": {0, 5, 10, 15, 20, None},
    "empathy": {True, False},
    "dialogue": {0, 4, 7, 10},
    "closure": {True, False, None},
    "critical": {True, False},
}


def message_id_to_turn(conversation: dict[str, Any]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, message in enumerate(conversation["transcript"], start=1):
        generated = f"M{index}"
        mapping[generated] = index
        actual = message.get("message_id")
        if actual:
            mapping[str(actual)] = index
    return mapping


def _evidence_turns(item: Any, mapping: dict[str, int]) -> list[int]:
    ids = list(item.evidence_ids)
    if not ids:
        ids = list(item.checked_message_ids)

    turns: list[int] = []
    for message_id in ids:
        turn = mapping.get(str(message_id))
        if turn is not None and turn not in turns:
            turns.append(turn)
    return turns


def _official_value(internal_id: str, item: Any):
    if not item.applicable:
        return None

    if internal_id == "gross_errors":
        return bool((item.score or 0) > 0 or item.critical_error)

    if internal_id in {"contact", "needs", "identification", "empathy", "closing"}:
        return bool(item.score)

    if internal_id in {"consultation", "dialog"}:
        if item.score is None:
            return None
        number = float(item.score)
        return int(number) if number.is_integer() else number

    raise ValueError(f"Unsupported internal criterion_id: {internal_id}")


def build_submission_entry(
    conversation: dict[str, Any],
    evaluation: AIEvaluation,
    final_score: float,
) -> dict[str, Any]:
    mapping = message_id_to_turn(conversation)
    items = {item.criterion_id: item for item in evaluation.criteria}

    criteria = []
    critical_flag = False

    for internal_id, official_id in OFFICIAL_ID_MAP.items():
        item = items.get(internal_id)
        if item is None:
            raise ValueError(f"Missing criterion: {internal_id}")

        value = _official_value(internal_id, item)
        if value not in ALLOWED_VALUES[official_id]:
            raise ValueError(
                f"{official_id}: invalid submission value {value!r}; "
                f"allowed: {sorted(ALLOWED_VALUES[official_id], key=lambda x: str(x))}"
            )

        if official_id == "critical":
            critical_flag = bool(value)

        criteria.append(
            {
                "criterion_id": official_id,
                "value": value,
                "rationale": item.reason.strip(),
                "evidence_turns": _evidence_turns(item, mapping),
            }
        )

    return {
        "conversation_id": conversation["conversation_id"],
        "status": "ok",
        "criteria": criteria,
        "score": {
            "final_score": round(float(final_score), 2),
            "critical_flag": critical_flag,
        },
    }


def error_submission_entry(conversation_id: str, error: str) -> dict[str, Any]:
    return {
        "conversation_id": conversation_id,
        "status": "error",
        "criteria": [],
        "score": None,
        "error": error,
    }


def validate_submission_document(
    document: dict[str, Any],
    *,
    expected_count: int,
) -> list[str]:
    errors: list[str] = []

    if document.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'")

    if not str(document.get("team_name", "")).strip():
        errors.append("team_name is required")

    model = document.get("model")
    if not isinstance(model, dict):
        errors.append("model object is required")
    else:
        if model.get("mode") not in {"local", "external_api", "hybrid"}:
            errors.append("model.mode must be local, external_api or hybrid")
        if not str(model.get("name", "")).strip():
            errors.append("model.name is required")

    results = document.get("results")
    if not isinstance(results, list):
        errors.append("results must be an array")
        return errors

    if len(results) != expected_count:
        errors.append(
            f"results must contain exactly {expected_count} entries; got {len(results)}"
        )

    ids = [str(x.get("conversation_id", "")) for x in results]
    if len(ids) != len(set(ids)):
        errors.append("conversation_id values must be unique")
    if any(not value for value in ids):
        errors.append("every result needs conversation_id")

    for result in results:
        cid = result.get("conversation_id", "<missing>")
        status = result.get("status")

        if status == "error":
            if result.get("criteria") != []:
                errors.append(f"{cid}: error status must have empty criteria")
            if result.get("score") is not None:
                errors.append(f"{cid}: error status must have score=null")
            if not str(result.get("error", "")).strip():
                errors.append(f"{cid}: error reason is required")
            continue

        if status != "ok":
            errors.append(f"{cid}: status must be ok or error")
            continue

        criteria = result.get("criteria")
        if not isinstance(criteria, list) or len(criteria) != 8:
            errors.append(f"{cid}: status=ok requires exactly 8 criteria")
            continue

        criterion_ids = [x.get("criterion_id") for x in criteria]
        if criterion_ids != OFFICIAL_IDS:
            errors.append(
                f"{cid}: criterion IDs/order must be exactly {OFFICIAL_IDS}"
            )

        for criterion in criteria:
            criterion_id = criterion.get("criterion_id")
            if criterion_id not in ALLOWED_VALUES:
                continue
            value = criterion.get("value")
            if value not in ALLOWED_VALUES[criterion_id]:
                errors.append(
                    f"{cid}/{criterion_id}: invalid value {value!r}"
                )
            if not str(criterion.get("rationale", "")).strip():
                errors.append(f"{cid}/{criterion_id}: rationale is required")
            turns = criterion.get("evidence_turns")
            if (
                not isinstance(turns, list)
                or any(not isinstance(x, int) or x < 1 for x in turns)
            ):
                errors.append(
                    f"{cid}/{criterion_id}: evidence_turns must be positive integers"
                )

        score = result.get("score")
        if not isinstance(score, dict):
            errors.append(f"{cid}: score object is required")
        else:
            final_score = score.get("final_score")
            if not isinstance(final_score, (int, float)) or not (0 <= final_score <= 100):
                errors.append(f"{cid}: final_score must be in 0..100")

            critical = next(
                (x for x in criteria if x.get("criterion_id") == "critical"),
                None,
            )
            if critical is not None:
                if score.get("critical_flag") != critical.get("value"):
                    errors.append(
                        f"{cid}: critical_flag must match critical criterion"
                    )

    return errors
