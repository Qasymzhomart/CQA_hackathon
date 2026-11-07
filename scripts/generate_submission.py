"""Generate the official CQA Hackathon results.json submission.

DEV:
    python scripts/generate_submission.py --set dev --team-name "TEAM NAME"

PROD after importing the control group:
    python scripts/generate_submission.py --set prod \
        --dataset data/control_id_dataset.json \
        --team-name "TEAM NAME"

The script is resumable and rate-limit aware. Progress is stored under data/
rather than results/, so each final results folder contains only results.json.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_analytics import DEFAULT_MODEL
from ai_analytics.adapter import to_backend_results
from ai_analytics.evaluator import evaluate_conversation
from backend.models import Criterion, CriterionResult
from backend.scoring import calculate_weighted_score
from backend.submission import (
    build_submission_entry,
    error_submission_entry,
    validate_submission_document,
)


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def is_rate_limit(exc: Exception) -> bool:
    text = str(exc).lower()
    return (
        "429" in text
        or "resource_exhausted" in text
        or "rate limit" in text
        or "quota exceeded" in text
    )


def evaluate_with_retry(
    conversation: dict,
    criteria_payload: list[dict],
    *,
    rate_wait: float,
    max_rate_retries: int,
):
    for attempt in range(max_rate_retries + 1):
        try:
            return evaluate_conversation(conversation, criteria_payload)
        except Exception as exc:
            if not is_rate_limit(exc) or attempt >= max_rate_retries:
                raise
            print(
                "  Rate limit. Waiting {:.0f}s, retry {}/{}...".format(
                    rate_wait,
                    attempt + 1,
                    max_rate_retries,
                )
            )
            time.sleep(rate_wait)
    raise RuntimeError("Unreachable")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", choices=["dev", "prod"], required=True)
    parser.add_argument("--dataset")
    parser.add_argument("--team-name", default=os.getenv("CQA_TEAM_NAME"))
    parser.add_argument(
        "--checklist",
        default="data/checklist_v1.json",
        help="Checklist JSON to use. For PROD you can pass an exported active checklist.",
    )
    parser.add_argument("--delay", type=float, default=6.0)
    parser.add_argument("--rate-wait", type=float, default=40.0)
    parser.add_argument("--rate-retries", type=int, default=5)
    args = parser.parse_args()

    if not args.team_name or not args.team_name.strip():
        raise SystemExit(
            'Team name required. Use --team-name "..." or set CQA_TEAM_NAME.'
        )

    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY is not set")

    if args.dataset:
        dataset_path = ROOT / args.dataset
    elif args.set == "dev":
        dataset_path = ROOT / "data" / "dev_dataset.json"
    else:
        raise SystemExit("--dataset is required for prod")

    if not dataset_path.exists():
        raise SystemExit(f"Dataset not found: {dataset_path}")

    checklist_path = ROOT / args.checklist
    if not checklist_path.exists():
        raise SystemExit(f"Checklist not found: {checklist_path}")

    dataset = json.loads(dataset_path.read_text(encoding="utf-8-sig"))
    checklist = json.loads(checklist_path.read_text(encoding="utf-8-sig"))

    records = dataset["records"]
    expected_count = 65 if args.set == "dev" else 10
    if len(records) != expected_count:
        raise SystemExit(
            f"{args.set} requires exactly {expected_count} conversations; "
            f"dataset has {len(records)}"
        )

    criteria_payload = checklist["criteria"]
    typed_criteria = [Criterion(**item) for item in criteria_payload]

    progress_path = ROOT / "data" / f"submission_{args.set}_progress.json"
    output_path = ROOT / "results" / args.set / "results.json"

    progress: list[dict] = []
    if progress_path.exists():
        try:
            previous = json.loads(progress_path.read_text(encoding="utf-8-sig"))
            if isinstance(previous, list):
                progress = previous
        except Exception:
            progress = []

    dataset_ids = {x["conversation_id"] for x in records}
    progress = [
        item for item in progress
        if item.get("conversation_id") in dataset_ids
    ]
    completed = {item["conversation_id"] for item in progress}

    if completed:
        print(f"Resuming {len(completed)} saved conversations.")

    for index, conversation in enumerate(records, start=1):
        cid = conversation["conversation_id"]
        if cid in completed:
            print(f"[{index}/{len(records)}] {cid} - already saved")
            continue

        print(f"[{index}/{len(records)}] {cid}")

        try:
            run = evaluate_with_retry(
                conversation,
                criteria_payload,
                rate_wait=args.rate_wait,
                max_rate_retries=args.rate_retries,
            )
            backend_payload = to_backend_results(run.evaluation, conversation)
            backend_results = [
                CriterionResult(**item)
                for item in backend_payload
            ]
            calculation = calculate_weighted_score(
                typed_criteria,
                backend_results,
            )
            entry = build_submission_entry(
                conversation,
                run.evaluation,
                calculation["final_score"],
            )
        except Exception as exc:
            error_text = str(exc).strip() or exc.__class__.__name__
            print(f"  ERROR: {error_text}")
            entry = error_submission_entry(cid, error_text[:500])

        progress.append(entry)
        completed.add(cid)
        save_json(progress_path, progress)
        print(f"  saved {len(progress)}/{len(records)}")

        if args.delay > 0 and len(progress) < len(records):
            time.sleep(args.delay)

    # Preserve original dataset order.
    by_id = {item["conversation_id"]: item for item in progress}
    ordered = [by_id[record["conversation_id"]] for record in records]

    model_name = os.getenv("CQA_AI_MODEL", DEFAULT_MODEL)
    document = {
        "schema_version": "1.0",
        "team_name": args.team_name.strip(),
        "model": {
            "mode": "external_api",
            "name": model_name,
        },
        "results": ordered,
    }

    errors = validate_submission_document(
        document,
        expected_count=expected_count,
    )
    if errors:
        save_json(output_path, document)
        print("Submission validation FAILED:")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)

    save_json(output_path, document)
    print("Submission validation: OK")
    print("Saved:", output_path)
    print("Records:", len(ordered))
    print(
        "Errors:",
        sum(1 for item in ordered if item.get("status") == "error"),
    )


if __name__ == "__main__":
    main()
