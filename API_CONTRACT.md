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
