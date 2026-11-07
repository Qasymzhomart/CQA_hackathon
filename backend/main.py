from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    AppealRequest,
    Conversation,
    Criterion,
    EvaluationRequest,
    ReviewRequest,
)
from .scoring import calculate_weighted_score


app = FastAPI(title="CQA Hackathon API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

CHECKLIST_VERSION = "v1"
CHECKLIST = [
    Criterion(id="contact", name="Установление контакта",
              description="Приветствие, представление и корректное начало диалога.",
              weight=10, response_type="binary", allow_na=False),
    Criterion(id="needs", name="Выявление потребности",
              description="Оператор уточняет запрос и понимает цель клиента.",
              weight=15, response_type="binary", allow_na=True),
    Criterion(id="identification", name="Идентификация",
              description="Корректная идентификация клиента, когда она требуется сценарием.",
              weight=20, response_type="binary", allow_na=True),
    Criterion(id="consultation", name="Корректная и полная консультация",
              description="Ответ точный, полный и соответствует запросу.",
              weight=20, response_type="binary", allow_na=False),
    Criterion(id="empathy", name="Эмпатия и клиентоориентированность",
              description="Тон и формулировки учитывают ситуацию клиента.",
              weight=15, response_type="binary", allow_na=True),
    Criterion(id="dialog", name="Управление диалогом, скорость и грамотность",
              description="Логичность, понятность, грамотность и управление ходом разговора.",
              weight=15, response_type="binary", allow_na=False),
    Criterion(id="closing", name="Завершение",
              description="Корректное завершение и проверка, что вопрос клиента решен.",
              weight=5, response_type="binary", allow_na=True),
    Criterion(id="gross_errors", name="Грубые ошибки",
              description="Отдельный флаг критических нарушений. Не входит в весовую сумму.",
              weight=0, response_type="flag", allow_na=False),
]

CONVERSATIONS: dict[str, Conversation] = {}
EVALUATIONS: dict[str, dict] = {}
APPEALS: list[dict] = []


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/checklist")
def get_checklist():
    return {
        "version": CHECKLIST_VERSION,
        "criteria": [c.model_dump() for c in CHECKLIST],
    }


@app.put("/api/checklist")
def replace_checklist(criteria: list[Criterion]):
    global CHECKLIST
    scored_weight = sum(c.weight for c in criteria if c.response_type != "flag")
    if round(scored_weight, 6) != 100:
        raise HTTPException(
            status_code=400,
            detail=f"Scored criteria weights must total 100, got {scored_weight}",
        )
    CHECKLIST = criteria
    return {"version": CHECKLIST_VERSION, "criteria": [c.model_dump() for c in CHECKLIST]}


@app.post("/api/conversations/import")
def import_conversations(records: list[Conversation]):
    for item in records:
        CONVERSATIONS[item.conversation_id] = item
    return {
        "imported": len(records),
        "total": len(CONVERSATIONS),
    }


@app.get("/api/conversations")
def list_conversations(language: str | None = None, channel: str | None = None):
    items = list(CONVERSATIONS.values())
    if language:
        items = [x for x in items if x.language == language]
    if channel:
        items = [x for x in items if x.channel == channel]
    return [x.model_dump() for x in items]


@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    item = CONVERSATIONS.get(conversation_id)
    if not item:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return item.model_dump()


@app.post("/api/evaluations")
def create_evaluation(payload: EvaluationRequest):
    if payload.conversation_id not in CONVERSATIONS:
        raise HTTPException(status_code=404, detail="Conversation not found")

    calculation = calculate_weighted_score(CHECKLIST, payload.results)
    evaluation_id = str(uuid4())

    record = {
        "evaluation_id": evaluation_id,
        "conversation_id": payload.conversation_id,
        "checklist_version": CHECKLIST_VERSION,
        "results": [x.model_dump() for x in payload.results],
        **calculation,
        "status": "evaluated",
    }
    EVALUATIONS[evaluation_id] = record
    return record


@app.get("/api/evaluations/{evaluation_id}")
def get_evaluation(evaluation_id: str):
    record = EVALUATIONS.get(evaluation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return record


@app.post("/api/appeals")
def create_appeal(payload: AppealRequest):
    record = EVALUATIONS.get(payload.evaluation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    if not payload.comment.strip():
        raise HTTPException(status_code=400, detail="Appeal comment is required")

    appeal = {
        "appeal_id": str(uuid4()),
        "evaluation_id": payload.evaluation_id,
        "comment": payload.comment,
        "status": "open",
    }
    APPEALS.append(appeal)
    record["status"] = "appealed"
    return appeal


@app.post("/api/reviews")
def reviewer_override(payload: ReviewRequest):
    record = EVALUATIONS.get(payload.evaluation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    updated_results = deepcopy(record["results"])
    found = False
    for item in updated_results:
        if item["criterion_id"] == payload.criterion_id:
            item["raw_score"] = payload.confirmed_score
            item["reviewer_comment"] = payload.reviewer_comment
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Criterion result not found")

    from .models import CriterionResult

    typed_results = [CriterionResult(**x) for x in updated_results]
    calculation = calculate_weighted_score(CHECKLIST, typed_results)

    record.update(
        {
            "results": updated_results,
            **calculation,
            "status": "reviewed",
        }
    )
    return record
