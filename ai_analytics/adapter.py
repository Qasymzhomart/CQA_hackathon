from __future__ import annotations

from typing import Any

from .schemas import AIEvaluation


def to_backend_results(
    evaluation: AIEvaluation,
    conversation: dict[str, Any],
) -> list[dict[str, Any]]:
    """Convert AI contract to backend CriterionResult-compatible records.

    Evidence text is resolved only from source transcript IDs, so model-generated
    quotes can never enter the backend.
    """
    transcript_by_id: dict[str, dict[str, Any]] = {}
    for i, msg in enumerate(conversation["transcript"], start=1):
        message_id = str(msg.get("message_id") or f"M{i}")
        transcript_by_id[message_id] = msg

    results = []
    for item in evaluation.criteria:
        evidence = []
        for message_id in item.evidence_ids:
            source = transcript_by_id[message_id]
            evidence.append(
                f'{message_id}: {source.get("text", "")}'
            )

        na = not item.applicable
        results.append(
            {
                "criterion_id": item.criterion_id,
                "answer": item.answer,
                "raw_score": 0.0 if item.score is None else item.score,
                "explanation": item.reason,
                "evidence": evidence,
                "evidence_ids": item.evidence_ids,
                "checked_message_ids": item.checked_message_ids,
                "critical_error": item.critical_error,
                "na": na,
                "na_reason": item.reason if na else None,
            }
        )
    return results
