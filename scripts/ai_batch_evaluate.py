"""Run the real Gemini evaluator on a balanced DEV sample.

Default sample:
- 10 RU
- 5 KZ
- 5 EN

Examples:
    python scripts/ai_batch_evaluate.py
    python scripts/ai_batch_evaluate.py --ru 10 --kz 5 --en 5

Input: data/dev_dataset.json
Output: data/ai_batch_results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_analytics.evaluator import evaluate_conversation


def take_by_language(records: list[dict], language: str, count: int) -> list[dict]:
    selected = [x for x in records if x.get("language") == language][:count]
    if len(selected) < count:
        raise SystemExit(
            f"Not enough {language} records: requested {count}, found {len(selected)}"
        )
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ru", type=int, default=10)
    parser.add_argument("--kz", type=int, default=5)
    parser.add_argument("--en", type=int, default=5)
    args = parser.parse_args()

    dataset_path = ROOT / "data" / "dev_dataset.json"
    if not dataset_path.exists():
        raise SystemExit("data/dev_dataset.json not found")

    checklist_path = ROOT / "data" / "checklist_v1.json"

    # utf-8-sig accepts files written by Windows PowerShell with a UTF-8 BOM.
    dataset = json.loads(dataset_path.read_text(encoding="utf-8-sig"))
    checklist = json.loads(checklist_path.read_text(encoding="utf-8-sig"))

    all_records = dataset["records"]
    records = (
        take_by_language(all_records, "RU", args.ru)
        + take_by_language(all_records, "KZ", args.kz)
        + take_by_language(all_records, "EN", args.en)
    )
    criteria = checklist["criteria"]

    print("Selected:", dict(Counter(x["language"] for x in records)))

    output = []
    for index, conversation in enumerate(records, start=1):
        print("[{}/{}] {} ({})".format(
            index,
            len(records),
            conversation["conversation_id"],
            conversation["language"],
        ))
        run = evaluate_conversation(conversation, criteria)
        output.append({
            "conversation_id": conversation["conversation_id"],
            "language": conversation["language"],
            "prompt_version": run.prompt_version,
            "retry_count": run.retry_count,
            "latency_ms": run.latency_ms,
            "usage": run.usage.model_dump(),
            "evaluation": run.evaluation.model_dump(),
        })

    out_path = ROOT / "data" / "ai_batch_results.json"
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total_cost = sum(x["usage"]["estimated_cost_usd"] for x in output)
    total_calls = sum(x["usage"]["calls"] for x in output)
    languages = Counter(x["language"] for x in output)

    print("Saved:", out_path)
    print("Evaluations:", len(output))
    print("Languages:", dict(languages))
    print("LLM calls:", total_calls)
    print("Estimated total cost: ${:.6f}".format(total_cost))


if __name__ == "__main__":
    main()
