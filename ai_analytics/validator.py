from __future__ import annotations

from typing import Any

from .schemas import AIEvaluation


def normalize_message_ids(conversation: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for i, msg in enumerate(conversation["transcript"], start=1):
        ids.add(str(msg.get("message_id") or f"M{i}"))
    return ids


def validate_ai_evaluation(
    evaluation: AIEvaluation,
    conversation: dict[str, Any],
    criteria: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    expected = {
        str(c.get("id", c.get("criterion_id"))): c
        for c in criteria
    }
    actual_ids = [item.criterion_id for item in evaluation.criteria]

    if evaluation.conversation_id != conversation["conversation_id"]:
        errors.append("conversation_id does not match input")

    if len(actual_ids) != len(set(actual_ids)):
        errors.append("duplicate criterion_id in AI response")

    missing = set(expected) - set(actual_ids)
    unknown = set(actual_ids) - set(expected)
    if missing:
        errors.append("missing criterion_id: " + ", ".join(sorted(missing)))
    if unknown:
        errors.append("unknown criterion_id: " + ", ".join(sorted(unknown)))

    valid_message_ids = normalize_message_ids(conversation)

    for item in evaluation.criteria:
        criterion = expected.get(item.criterion_id)
        if criterion is None:
            continue

        allow_na = bool(criterion.get("allow_na", True))
        response_type = criterion.get("response_type", criterion.get("answer_type", "binary"))
        max_score = float(criterion.get("scale_max", criterion.get("max_score", 1)))
        min_score = float(criterion.get("min_score", 0))
        allowed_values = criterion.get("allowed_values")
        if allowed_values is None and response_type in ("binary", "boolean", "flag"):
            allowed_values = [0, 1]

        if not item.reason.strip():
            errors.append(f"{item.criterion_id}: reason is empty")

        bad_evidence = set(item.evidence_ids) - valid_message_ids
        if bad_evidence:
            errors.append(
                f"{item.criterion_id}: invalid evidence_ids "
                + ", ".join(sorted(bad_evidence))
            )

        bad_checked = set(item.checked_message_ids) - valid_message_ids
        if bad_checked:
            errors.append(
                f"{item.criterion_id}: invalid checked_message_ids "
                + ", ".join(sorted(bad_checked))
            )

        if not item.applicable:
            if not allow_na:
                errors.append(f"{item.criterion_id}: N/A is not allowed")
            if item.answer.upper() != "N/A":
                errors.append(f"{item.criterion_id}: non-applicable answer must be N/A")
            if item.score is not None:
                errors.append(f"{item.criterion_id}: N/A score must be null")
            continue

        if item.answer.upper() == "N/A":
            errors.append(f"{item.criterion_id}: applicable criterion cannot answer N/A")
        if item.score is None:
            errors.append(f"{item.criterion_id}: applicable score cannot be null")
            continue
        if item.score < min_score or item.score > max_score:
            errors.append(
                f"{item.criterion_id}: score {item.score} outside {min_score}..{max_score}"
            )
        if allowed_values is not None and item.score not in allowed_values:
            errors.append(
                f"{item.criterion_id}: score {item.score} must be one of {allowed_values}"
            )

    return errors
