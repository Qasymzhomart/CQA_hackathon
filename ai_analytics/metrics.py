from __future__ import annotations

from collections import Counter
from typing import Any


def score_accuracy(rows: list[dict[str, Any]]) -> float:
    comparable = [r for r in rows if r.get("human_score") is not None]
    if not comparable:
        return 0.0
    correct = sum(
        1 for r in comparable
        if r.get("human_score") == r.get("ai_score")
    )
    return round(correct / len(comparable) * 100, 2)


def evidence_accuracy(rows: list[dict[str, Any]]) -> float:
    comparable = [
        r for r in rows
        if r.get("human_evidence") is not None
    ]
    if not comparable:
        return 0.0
    correct = sum(
        1 for r in comparable
        if set(r.get("human_evidence", [])) == set(r.get("ai_evidence", []))
    )
    return round(correct / len(comparable) * 100, 2)


def na_accuracy(rows: list[dict[str, Any]]) -> float:
    comparable = [
        r for r in rows
        if r.get("human_applicable") is not None
    ]
    if not comparable:
        return 0.0
    correct = sum(
        1 for r in comparable
        if r.get("human_applicable") == r.get("ai_applicable")
    )
    return round(correct / len(comparable) * 100, 2)


def error_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(r["error_type"] for r in rows if r.get("error_type")))
