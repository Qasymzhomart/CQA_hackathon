"""Build manual-vs-AI quality metrics from data/manual_review.csv."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_analytics.metrics import error_summary, evidence_accuracy, na_accuracy, score_accuracy


def parse_bool(value: str):
    if value == "":
        return None
    return value.strip().lower() in {"1", "true", "yes"}


def parse_score(value: str):
    if value == "":
        return None
    return float(value)


def parse_ids(value: str):
    if value == "":
        return None
    return [x.strip() for x in value.split(";") if x.strip()]


def main() -> None:
    path = ROOT / "data" / "manual_review.csv"
    if not path.exists():
        raise SystemExit("Create data/manual_review.csv from manual_review_template.csv first.")

    rows = []
    with path.open(encoding="utf-8", newline="") as fh:
        for raw in csv.DictReader(fh):
            rows.append({
                **raw,
                "human_score": parse_score(raw["human_score"]),
                "ai_score": parse_score(raw["ai_score"]),
                "human_evidence": parse_ids(raw["human_evidence"]),
                "ai_evidence": parse_ids(raw["ai_evidence"]),
                "human_applicable": parse_bool(raw["human_applicable"]),
                "ai_applicable": parse_bool(raw["ai_applicable"]),
            })

    report = {
        "rows": len(rows),
        "score_accuracy_percent": score_accuracy(rows),
        "evidence_accuracy_percent": evidence_accuracy(rows),
        "na_accuracy_percent": na_accuracy(rows),
        "error_summary": error_summary(rows),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
