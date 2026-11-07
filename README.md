# CQA Hackathon — Conversation Quality Analytics

Prototype for automatic contact-center conversation quality evaluation.

## What is implemented

- Editable checklist with 7 weighted criteria and a separate "Грубые ошибки" flag.
- Conversation model for RU / KZ / EN.
- Support for agent chat and voice-call transcripts.
- Deterministic weighted scoring in the backend.
- N/A exclusion with proportional redistribution of the remaining weights to 100%.
- Evidence quotes and explanations for every evaluated criterion.
- Appeals with mandatory comments.
- Reviewer score override followed by automatic final-score recalculation.
- DEV dataset validation for the expected distribution:
  - 65 total conversations
  - 35 RU / 15 KZ / 15 EN
  - 60 agent_chat / 5 voice_call
- Tests for scoring and dataset validation.

## Project structure

```
backend/
  main.py          FastAPI endpoints
  models.py        Pydantic data models
  scoring.py       final-score calculation
  dataset.py       DEV dataset normalization/validation

data/
  checklist_v1.json
  dev_sample.json

scripts/
  import_dev.py    organizer API downloader for group_id=DEV

tests/
  test_scoring.py
  test_dataset.py

API_CONTRACT.md    frontend integration contract
requirements.txt
```

## Run backend

Python 3.11+ recommended.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

macOS / Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Open:

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health check: http://localhost:8000/health

CORS is enabled for hackathon frontend integration.

## Import organizer DEV data

Set the organizer endpoint in an environment variable. The script automatically requests `group_id=DEV`.

Windows CMD:

```bat
set CQA_DATASET_URL=https://YOUR_DATASET_ENDPOINT
python scripts/import_dev.py
```

PowerShell:

```powershell
$env:CQA_DATASET_URL="https://YOUR_DATASET_ENDPOINT"
python scripts/import_dev.py
```

If the API requires a bearer token:

```powershell
$env:CQA_DATASET_TOKEN="YOUR_TOKEN"
```

The script validates the expected 65-record DEV distribution and saves the normalized result to `data/dev_dataset.json`.

## Run tests

```bash
pytest -q
```

## Frontend integration

See [API_CONTRACT.md](API_CONTRACT.md).

Important rule: the frontend should display the score returned by the backend. It should not calculate the final weighted score itself.

## Initial checklist weights

| Criterion | Weight |
|---|---:|
| Установление контакта | 10% |
| Выявление потребности | 15% |
| Идентификация | 20% |
| Корректная и полная консультация | 20% |
| Эмпатия и клиентоориентированность | 15% |
| Управление диалогом, скорость и грамотность | 15% |
| Завершение | 5% |
| Грубые ошибки | separate flag |

Total scored weight: **100%**.

## Demo flow

1. Import/select a conversation.
2. Open the transcript or call record.
3. Evaluate all checklist criteria.
4. Show answer, score, weight, explanation, and evidence.
5. Show the calculated final score.
6. Submit an appeal with a comment.
7. Reviewer confirms or changes the criterion score.
8. Backend recalculates and returns the final result.


## Frontend (added for the hackathon)

Frontend is a plain HTML/CSS/JavaScript app under `frontend/`, compatible with embedding in a Dynamics 365 HTML component after adjusting the API base URL.

Start backend (terminal 1):
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Start frontend (terminal 2):
```bash
python -m http.server 5500 --directory frontend
```

Open **http://localhost:5500**.

The frontend uses `http://localhost:8000` as its API URL. To point at a deployed backend, run `localStorage.setItem("cqa_api_base", "https://YOUR-API-HOST")` in the browser console and reload. For production replace permissive CORS with a specific trusted origin.

### Demo walkthrough (under five minutes)
1. Click **Загрузить демо** to import three *synthetic* sample conversations (RU, KZ, EN). The app intentionally does not bundle the real organizer records.
2. Open a conversation and press **Запустить оценку**; the frontend calls the Gemini AI endpoint and the backend returns weighted score, criteria, explanations, N/A and evidence.
3. Click an evidence reference (M1, M2, …) to scroll and highlight the exact transcript message.
4. Appeal a criterion and visit **Апелляции** to confirm or change its score, entering a reviewer reason. The backend recalculates the final score.
5. Under **Чек-лист**, change a criterion weight/type/name or add one; maintain **100%** total weights and save. Re-evaluate the conversation.

**Limitations:** The main frontend evaluation flow uses the Gemini AI endpoint and is still a hackathon prototype, not a production quality-audit system. The separate `/api/evaluate/{conversation_id}` endpoint remains a demo heuristic fallback. FastAPI currently keeps conversations, evaluations, appeals and checklist edits **in process memory**; restart clears them. The user may re-import demo or organizer JSON after restart. Real organizer's 65 conversations are **not** bundled. The Voice Call demo has no real audio link.

### New endpoints
- `POST /api/evaluate/{conversation_id}`: create heuristic evaluation.
- `GET /api/evaluations`: list evaluation records.
- `GET /api/appeals`: list appeals.
- `POST /api/appeals`: body includes `evaluation_id`, `criterion_id` and `comment`.
- `POST /api/reviews`: body includes `evaluation_id`, `criterion_id`, `confirmed_score`, `reviewer_comment`.

Security: no account login is needed for the demo, as specified in the task. Do not expose the reviewer endpoints or permissive CORS publicly without adding authorization.


## Real AI evaluation with Gemini

Set your Gemini API key in the same terminal where the backend will run:

```powershell
$env:GEMINI_API_KEY="YOUR_GEMINI_KEY"
$env:CQA_AI_MODEL="gemini-3.5-flash-lite"
uvicorn backend.main:app --reload
```

Then use Swagger:

`POST /api/ai/evaluate/{conversation_id}`

This endpoint uses Gemini structured output, validates criterion IDs, N/A rules,
score ranges and evidence message IDs, retries once on an invalid model result,
then passes the validated criterion results to backend weighted scoring.

`POST /api/evaluate/{conversation_id}` remains a demo-only heuristic fallback.
