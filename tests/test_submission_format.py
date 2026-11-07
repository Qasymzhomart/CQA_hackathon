from backend.submission import (
    OFFICIAL_IDS,
    build_submission_entry,
    validate_submission_document,
)
from ai_analytics.schemas import AICriterionResult, AIEvaluation


def test_official_submission_mapping():
    conversation = {
        "conversation_id": "demo-1",
        "transcript": [
            {"speaker": "client", "text": "Question"},
            {"speaker": "operator", "text": "Hello"},
        ],
    }
    evaluation = AIEvaluation(
        conversation_id="demo-1",
        criteria=[
            AICriterionResult(criterion_id="contact", applicable=True, answer="YES", score=1, reason="ok", evidence_ids=["M2"], checked_message_ids=["M2"], critical_error=False),
            AICriterionResult(criterion_id="needs", applicable=False, answer="N/A", score=None, reason="n/a", evidence_ids=[], checked_message_ids=["M1"], critical_error=False),
            AICriterionResult(criterion_id="identification", applicable=False, answer="N/A", score=None, reason="n/a", evidence_ids=[], checked_message_ids=["M1"], critical_error=False),
            AICriterionResult(criterion_id="consultation", applicable=True, answer="15", score=15, reason="ok", evidence_ids=["M2"], checked_message_ids=["M2"], critical_error=False),
            AICriterionResult(criterion_id="empathy", applicable=True, answer="YES", score=1, reason="ok", evidence_ids=["M2"], checked_message_ids=["M2"], critical_error=False),
            AICriterionResult(criterion_id="dialog", applicable=True, answer="7", score=7, reason="ok", evidence_ids=["M2"], checked_message_ids=["M2"], critical_error=False),
            AICriterionResult(criterion_id="closing", applicable=True, answer="NO", score=0, reason="no", evidence_ids=[], checked_message_ids=["M2"], critical_error=False),
            AICriterionResult(criterion_id="gross_errors", applicable=True, answer="NO", score=0, reason="none", evidence_ids=[], checked_message_ids=["M2"], critical_error=False),
        ],
    )

    entry = build_submission_entry(conversation, evaluation, 81.25)
    assert [x["criterion_id"] for x in entry["criteria"]] == OFFICIAL_IDS
    assert entry["criteria"][0]["evidence_turns"] == [2]
    assert entry["criteria"][1]["value"] is None
    assert entry["criteria"][3]["value"] == 15
    assert entry["criteria"][5]["value"] == 7
    assert entry["score"]["critical_flag"] is False

    doc = {
        "schema_version": "1.0",
        "team_name": "Team",
        "model": {"mode": "external_api", "name": "gemini-test"},
        "results": [entry],
    }
    assert validate_submission_document(doc, expected_count=1) == []
