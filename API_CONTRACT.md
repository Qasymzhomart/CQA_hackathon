# Frontend ↔ Backend contract

Backend base URL: `http://localhost:8000`

## Checklist
- `GET /api/checklist` — current editable checklist.
- `PUT /api/checklist` — replace checklist. Scored weights must total 100.

## Conversations
- `POST /api/conversations/import` — import normalized conversations.
- `GET /api/conversations` — list all conversations.
- Filters: `?language=RU`, `?channel=agent_chat`.
- `GET /api/conversations/{conversation_id}` — transcript + audio URL.

## Evaluation
- `POST /api/evaluations`
- `GET /api/evaluations/{evaluation_id}`

Each criterion result should contain:
```json
{
  "criterion_id": "consultation",
  "answer": "yes",
  "raw_score": 1,
  "explanation": "Operator gave the requested instructions.",
  "evidence": ["Откройте раздел Отчеты..."],
  "na": false,
  "na_reason": null
}
```

The backend calculates the final weighted score. The frontend should not calculate it.

## Appeals and review
- `POST /api/appeals` — requires an appeal comment.
- `POST /api/reviews` — reviewer can confirm/change a criterion score; backend recalculates final score.

## Scoring rules
- N/A criterion is removed from scoring.
- Remaining weights are redistributed proportionally to total 100%.
- Final score and effective weights are rounded to 2 decimals.
- `Грубые ошибки` is a separate flag, not part of the 100% weight.


## Updated demo interface contract
- `POST /api/evaluate/{conversation_id}`: automatically produces a demo heuristic evaluation.
- `GET /api/evaluations`: lists all current in-memory evaluations.
- `GET /api/appeals`: lists current appeals.
- `POST /api/appeals` body: `{"evaluation_id":"…","criterion_id":"contact","comment":"…"}`.
- `POST /api/reviews` body: `{"evaluation_id":"…","criterion_id":"contact","confirmed_score":1,"reviewer_comment":"…"}`.
- `GET /api/checklist` and `PUT /api/checklist`: current criterion configuration.
- `GET /api/conversations`, `GET /api/conversations/{id}`, `POST /api/conversations/import`.

`/api/evaluate` returns an `evaluation_id`, `conversation_id`, `status`, `final_score`, `results` (including `explanation`, `evidence`, `na` and `na_reason`), weighted `criteria` contributions and `gross_errors`. Transcript message references are 1-based `M1`, `M2`, etc.

**Note:** This is a demonstration evaluation flow, not model-powered analysis. API state is in-memory and disappears when the backend process restarts.


## Real AI evaluation

`POST /api/ai/evaluate/{conversation_id}`

Runs the AI/Analytics pipeline:

1. dynamic checklist + transcript with message IDs;
2. structured LLM output;
3. validation of criterion IDs, score ranges, N/A, and evidence IDs;
4. one retry if validation fails;
5. conversion to backend results;
6. backend calculates the final weighted score.

Required server environment:

```bash
OPENAI_API_KEY=...
CQA_AI_MODEL=gpt-5.4-mini-2026-03-17
```

The response also contains `prompt_version`, `model`, `retry_count`,
`latency_ms`, token usage, and `estimated_cost_usd`.

The existing `POST /api/evaluate/{conversation_id}` endpoint is demo-only
rule-based heuristics and should not be presented as the production AI evaluator.
