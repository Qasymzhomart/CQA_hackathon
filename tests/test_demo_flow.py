"""Regression tests for the complete demo workflow."""
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_demo_evaluation_appeal_and_recalculation():
    conversation_id = "test-" + str(uuid4())
    transcript = [
        {"timestamp": "00:01", "speaker": "client", "text": "Здравствуйте, где отчет?"},
        {"timestamp": "00:03", "speaker": "operator", "text": "Здравствуйте! Меня зовут Анна. Помогу, уточните за какой период?"},
        {"timestamp": "00:12", "speaker": "client", "text": "За октябрь"},
        {"timestamp": "00:18", "speaker": "operator", "text": "Откройте Отчеты, выберите октябрь и нажмите Скачать. Спасибо!"},
    ]
    imported = client.post("/api/conversations/import", json=[{
        "conversation_id": conversation_id, "channel": "agent_chat",
        "language": "RU", "transcript": transcript, "audio_url": None
    }])
    assert imported.status_code == 200
    evaluation = client.post("/api/evaluate/" + conversation_id)
    assert evaluation.status_code == 200, evaluation.text
    before = evaluation.json()
    assert 0 <= before["final_score"] <= 100
    assert any(r["na"] and r["criterion_id"] == "identification" for r in before["results"])
    assert any("M" in ev for r in before["results"] for ev in r["evidence"])
    assert any(r["criterion_id"] == "consultation" for r in before["criteria"])

    appeal = client.post("/api/appeals", json={
        "evaluation_id": before["evaluation_id"], "criterion_id": "contact",
        "comment": "Проверьте приветствие и представление."
    })
    assert appeal.status_code == 200, appeal.text
    assert appeal.json()["criterion_id"] == "contact"
    assert appeal.json()["status"] == "open"

    review = client.post("/api/reviews", json={
        "evaluation_id": before["evaluation_id"], "criterion_id": "contact",
        "confirmed_score": 0, "reviewer_comment": "Представление не засчитывается."
    })
    assert review.status_code == 200, review.text
    after = review.json()
    assert after["status"] == "reviewed"
    assert after["final_score"] <= before["final_score"]
    assert any(a["status"] == "reviewed" and a["appeal_id"] == appeal.json()["appeal_id"]
               for a in client.get("/api/appeals").json())

def test_checklist_scales_and_na():
    response = client.get("/api/checklist")
    assert response.status_code == 200
    by_id = {c["id"]: c for c in response.json()["criteria"]}
    assert by_id["consultation"]["scale_max"] == 20
    assert by_id["consultation"]["response_type"] == "scale"
    assert by_id["dialog"]["scale_max"] == 10
    assert by_id["dialog"]["response_type"] == "scale"
    assert sum(c["weight"] for c in by_id.values() if c["response_type"] != "flag") == 100
