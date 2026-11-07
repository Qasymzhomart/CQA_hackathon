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
