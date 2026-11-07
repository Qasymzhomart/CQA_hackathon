from backend.models import Criterion, CriterionResult
from backend.scoring import calculate_weighted_score


def test_full_score_is_100():
    criteria = [
        Criterion(id="a", name="A", weight=40, scale_max=1),
        Criterion(id="b", name="B", weight=60, scale_max=1),
    ]
    results = [
        CriterionResult(
            criterion_id="a", answer="yes", raw_score=1,
            explanation="ok", evidence=["quote a"]
        ),
        CriterionResult(
            criterion_id="b", answer="yes", raw_score=1,
            explanation="ok", evidence=["quote b"]
        ),
    ]
    assert calculate_weighted_score(criteria, results)["final_score"] == 100.0


def test_na_redistributes_remaining_weight_to_100():
    criteria = [
        Criterion(id="a", name="A", weight=40, scale_max=1),
        Criterion(id="b", name="B", weight=60, scale_max=1),
    ]
    results = [
        CriterionResult(
            criterion_id="a", answer="N/A", raw_score=0,
            explanation="Not applicable", evidence=[],
            na=True, na_reason="Scenario does not require it"
        ),
        CriterionResult(
            criterion_id="b", answer="yes", raw_score=1,
            explanation="ok", evidence=["quote b"]
        ),
    ]
    result = calculate_weighted_score(criteria, results)
    assert result["final_score"] == 100.0
    assert result["criteria"][0]["effective_weight"] == 100.0


def test_gross_error_is_separate_flag():
    criteria = [
        Criterion(id="a", name="A", weight=100, scale_max=1),
        Criterion(id="gross", name="Gross errors", weight=0, response_type="flag"),
    ]
    results = [
        CriterionResult(
            criterion_id="a", answer="yes", raw_score=1,
            explanation="ok", evidence=["quote"]
        ),
        CriterionResult(
            criterion_id="gross", answer="yes", raw_score=1,
            explanation="Critical violation", evidence=["bad quote"]
        ),
    ]
    result = calculate_weighted_score(criteria, results)
    assert result["final_score"] == 100.0
    assert len(result["gross_errors"]) == 1
