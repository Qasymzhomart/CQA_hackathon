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
              weight=20, response_type="scale", scale_max=20, allow_na=True),
    Criterion(id="empathy", name="Эмпатия и клиентоориентированность",
              description="Тон и формулировки учитывают ситуацию клиента.",
              weight=15, response_type="binary", allow_na=False),
    Criterion(id="dialog", name="Управление диалогом, скорость и грамотность",
              description="Логичность, понятность, грамотность и управление ходом разговора.",
              weight=15, response_type="scale", scale_max=10, allow_na=False),
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

# Demo-only rule-based evaluator. It does not use a language model.
from .models import CriterionResult
import re

def _contains(text, words):
    return any(word in text for word in words)

@app.post("/api/evaluate/{conversation_id}")
def auto_evaluate(conversation_id: str):
    conversation = CONVERSATIONS.get(conversation_id)
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    utterances = conversation.transcript
    operator = [(idx, u) for idx, u in enumerate(utterances) if u.speaker.lower() in ("operator", "agent")]
    clients = [u for u in utterances if u.speaker.lower() == "client"]
    all_operator = " ".join(u.text.lower() for _, u in operator)
    all_client = " ".join(u.text.lower() for u in clients)
    first = operator[0][1].text.lower() if operator else ""
    last = operator[-1][1].text.lower() if operator else ""
    hello = _contains(first, ("здравств", "добрый", "сәлем", "қайырлы", "hello", "hi ", "good morning", "good afternoon"))
    intro = _contains(first, ("менің атым", "мен ", "менеджер", "меня зовут", "my name", "this is ", "оператор"))
    need = _contains(all_operator, ("уточн", "подскаж", "какой", "какая", "қай", "нақтыл", "which", "could you", "please tell", "?"))
    # Identification is relevant only when protected actions or account-specific information are requested.
    protected = _contains(all_client, ("перевод", "вывод", "снять", "сменить пароль", "balance", "withdraw", "transfer", "құпиясөз", "аударым", "баланс"))
    identified = _contains(all_operator, ("удостовер", "документ", "код подтвержд", "verify your", "verification", "жеке бас", "растау", "идентификац"))
    guidance = _contains(all_operator, ("открой", "выбер", "нажм", "проверь", "обратит", "бөлім", "таңда", "ашыңыз", "click", "open ", "select ", "follow ", "download"))
    empathy = _contains(all_operator, ("помогу", "понима", "сожале", "кешір", "түсін", "көмектес", "sorry", "understand", "happy to help", "help"))
    closing = _contains(last, ("спасибо", "до свид", "всего добр", "рахмет", "сау бол", "көмек қажет", "thank you", "goodbye", "anything else"))
    gross = _contains(all_operator, ("переведите мне лично", "мой личный счет", "оплатите мне", "send money to me", "жеке шотыма"))
    checks = {
        "contact": (1 if hello and intro else 0, "Приветствие и представление проверены в первом ответе."),
        "needs": (1 if need else 0, "Проверены уточняющие вопросы оператора."),
        "identification": (1 if identified else 0, "Проверено подтверждение личности до защищённых действий."),
        "consultation": (20 if guidance else 10 if operator else 0, "Эвристика оценивает наличие конкретных инструкций; правильность фактов требует ручной проверки."),
        "empathy": (1 if empathy else 0, "Проверены вежливые и поддерживающие формулировки."),
        "dialog": (10 if len(operator)>1 else 7 if operator else 0, "Оценена связность по количеству ответов; скорость и грамотность требуют ручной проверки."),
        "closing": (1 if closing else 0, "Проверено прощание или итог в последнем ответе."),
        "gross_errors": (1 if gross else 0, "Поиск явных формулировок грубого нарушения (не исчерпывающая проверка).")
    }
    results = []
    for c in CHECKLIST:
        raw, reason = checks.get(c.id, (0, "Для нового критерия нужна ручная проверка."))
        na = (c.id == "identification" and not protected and c.allow_na) or (c.id == "needs" and not clients and c.allow_na)
        if c.response_type == "scale":
            options = [0, 5, 10, 15, 20] if c.scale_max == 20 else [0, 4, 7, 10]
            raw = min(options, key=lambda x: abs(x - raw)) if c.id not in ("consultation", "dialog") else raw
        raw = min(float(raw), c.scale_max) if c.response_type != "flag" else float(raw)
        evidence_items = [f"M{i+1}: {u.text}" for i,u in operator[:2]]
        if c.id == "closing" and operator:
            evidence_items = [f"M{operator[-1][0]+1}: {operator[-1][1].text}"]
        results.append(CriterionResult(criterion_id=c.id, answer="N/A" if na else ("YES" if raw else "NO"),
            raw_score=raw, explanation=reason, evidence=evidence_items,
            na=na, na_reason="Запрос не требовал идентификации." if na and c.id=="identification" else "Недостаточно данных для оценки." if na else None))
    calculation = calculate_weighted_score(CHECKLIST, results)
    evaluation_id = str(uuid4())
    record = {"evaluation_id":evaluation_id,"conversation_id":conversation_id,
              "checklist_version":CHECKLIST_VERSION,"results":[x.model_dump() for x in results],
              **calculation,"status":"evaluated","assessment_method":"demo_heuristics"}
    EVALUATIONS[evaluation_id] = record
    return record

@app.get("/api/appeals")
def list_appeals():
    return APPEALS

@app.get("/api/evaluations")
def list_evaluations():
    return list(EVALUATIONS.values())
