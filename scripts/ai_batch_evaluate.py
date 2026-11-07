"""Run the real LLM evaluator on DEV conversations.

Examples:
    set GEMINI_API_KEY=...
    python scripts/ai_batch_evaluate.py
    python scripts/ai_batch_evaluate.py --limit 20

Input: data/dev_dataset.json (preferred) or data/dev_sample.json.
Output: data/ai_batch_results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_analytics.evaluator import evaluate_conversation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    dataset_path = ROOT / "data" / "dev_dataset.json"
    if not dataset_path.exists():
        dataset_path = ROOT / "data" / "dev_sample.json"

    checklist_path = ROOT / "data" / "checklist_v1.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    checklist = json.loads(checklist_path.read_text(encoding="utf-8"))

    records = dataset["records"][: args.limit]
    criteria = checklist["criteria"]

    output = []
    for index, conversation in enumerate(records, start=1):
        print("[{}/{}] {}".format(index, len(records), conversation["conversation_id"]))
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
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    total_cost = sum(x["usage"]["estimated_cost_usd"] for x in output)
    total_calls = sum(x["usage"]["calls"] for x in output)
    print("Saved: {}".format(out_path))
    print("Evaluations: {}".format(len(output)))
    print("LLM calls: {}".format(total_calls))
    print("Estimated total cost: ${:.6f}".format(total_cost))


if __name__ == "__main__":
    main()
