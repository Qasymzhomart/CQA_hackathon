from __future__ import annotations

from .models import Criterion, CriterionResult


def calculate_weighted_score(
    criteria: list[Criterion],
    results: list[CriterionResult],
) -> dict:
    """Deterministic final scoring.

    - N/A criteria are excluded.
    - Remaining criterion weights are redistributed proportionally to 100%.
    - Final score is rounded to two decimals.
    - Gross-error flags are reported separately and do not silently alter weights.
    """
    criteria_by_id = {c.id: c for c in criteria}
    result_by_id = {r.criterion_id: r for r in results}

    applicable = []
    gross_errors = []

    for criterion in criteria:
        result = result_by_id.get(criterion.id)
        if result is None:
            continue

        if criterion.response_type == "flag":
            if result.raw_score > 0:
                gross_errors.append(
                    {
                        "criterion_id": criterion.id,
                        "name": criterion.name,
                        "explanation": result.explanation,
                        "evidence": result.evidence,
                    }
                )
            continue

        if result.na:
            continue

        applicable.append((criterion, result))

    active_weight = sum(c.weight for c, _ in applicable)
    if active_weight <= 0:
        return {
            "final_score": 0.0,
            "criteria": [],
            "gross_errors": gross_errors,
        }

    breakdown = []
    final_score = 0.0

    for criterion, result in applicable:
        redistributed_weight = criterion.weight / active_weight * 100.0
        normalized_score = min(result.raw_score / criterion.scale_max, 1.0)
        contribution = normalized_score * redistributed_weight
        final_score += contribution

        breakdown.append(
            {
                "criterion_id": criterion.id,
                "name": criterion.name,
                "original_weight": criterion.weight,
                "effective_weight": round(redistributed_weight, 2),
                "raw_score": result.raw_score,
                "contribution": round(contribution, 2),
                "explanation": result.explanation,
                "evidence": result.evidence,
            }
        )

    return {
        "final_score": round(final_score, 2),
        "criteria": breakdown,
        "gross_errors": gross_errors,
    }
