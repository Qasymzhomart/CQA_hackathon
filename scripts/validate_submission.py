"""Validate an official CQA Hackathon results.json before push."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.submission import validate_submission_document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--expected", type=int, required=True)
    args = parser.parse_args()

    path = ROOT / args.path
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    errors = validate_submission_document(
        document,
        expected_count=args.expected,
    )

    if errors:
        print("INVALID")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)

    print("VALID")
    print("records:", len(document["results"]))


if __name__ == "__main__":
    main()
