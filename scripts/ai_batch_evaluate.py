"""Run Gemini evaluator on a balanced DEV sample without losing progress.

Default sample:
- 10 RU
- 5 KZ
- 5 EN

The script:
- waits between conversations to stay under free-tier request limits;
- automatically retries Gemini 429 / RESOURCE_EXHAUSTED responses;
- writes data/ai_batch_results.json after every completed conversation;
- resumes already saved conversations on the next run.

Examples:
    python scripts/ai_batch_evaluate.py
    python scripts/ai_batch_evaluate.py --delay 6
    python scripts/ai_batch_evaluate.py --ru 10 --kz 5 --en 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
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


def save_results(path: Path, output: list[dict]) -> None:
    path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def evaluate_with_rate_limit_retry(
    conversation: dict,
    criteria: list[dict],
    *,
    max_rate_retries: int = 3,
    wait_seconds: float = 40.0,
):
    for attempt in range(max_rate_retries + 1):
        try:
            return evaluate_conversation(conversation, criteria)
        except Exception as exc:
            message = str(exc)
            is_rate_limit = (
                "429" in message
                or "RESOURCE_EXHAUSTED" in message
                or "rate limit" in message.lower()
                or "quota exceeded" in message.lower()
            )
            if not is_rate_limit or attempt >= max_rate_retries:
                raise

            print(
                "  Gemini rate limit reached. Waiting {:.0f}s and retrying "
                "({}/{})...".format(
                    wait_seconds,
                    attempt + 1,
                    max_rate_retries,
                )
            )
            time.sleep(wait_seconds)

    raise RuntimeError("Unreachable")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ru", type=int, default=10)
    parser.add_argument("--kz", type=int, default=5)
    parser.add_argument("--en", type=int, default=5)
    parser.add_argument(
        "--delay",
        type=float,
        default=6.0,
        help="Pause between completed conversations (seconds).",
    )
    parser.add_argument(
        "--rate-wait",
        type=float,
        default=40.0,
        help="Wait after Gemini 429 before retrying (seconds).",
    )
    args = parser.parse_args()

    dataset_path = ROOT / "data" / "dev_dataset.json"
    if not dataset_path.exists():
        raise SystemExit("data/dev_dataset.json not found")

    checklist_path = ROOT / "data" / "checklist_v1.json"
    out_path = ROOT / "data" / "ai_batch_results.json"

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
    selected_ids = {x["conversation_id"] for x in records}

    print("Selected:", dict(Counter(x["language"] for x in records)))

    output: list[dict] = []
    if out_path.exists():
        try:
            previous = json.loads(out_path.read_text(encoding="utf-8-sig"))
            if isinstance(previous, list):
                output = [
                    item
                    for item in previous
                    if item.get("conversation_id") in selected_ids
                ]
        except Exception:
            output = []

    completed_ids = {x["conversation_id"] for x in output}
    if completed_ids:
        print("Resuming saved results:", len(completed_ids))

    for index, conversation in enumerate(records, start=1):
        conversation_id = conversation["conversation_id"]
        language = conversation["language"]

        if conversation_id in completed_ids:
            print(
                "[{}/{}] {} ({}) - already saved".format(
                    index,
                    len(records),
                    conversation_id,
                    language,
                )
            )
            continue

        print(
            "[{}/{}] {} ({})".format(
                index,
                len(records),
                conversation_id,
                language,
            )
        )

        run = evaluate_with_rate_limit_retry(
            conversation,
            criteria,
            wait_seconds=args.rate_wait,
        )

        output.append({
            "conversation_id": conversation_id,
            "language": language,
            "prompt_version": run.prompt_version,
            "retry_count": run.retry_count,
            "latency_ms": run.latency_ms,
            "usage": run.usage.model_dump(),
            "evaluation": run.evaluation.model_dump(),
        })

        save_results(out_path, output)
        completed_ids.add(conversation_id)
        print("  saved ({}/{})".format(len(output), len(records)))

        if args.delay > 0 and len(output) < len(records):
            time.sleep(args.delay)

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
