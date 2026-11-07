from __future__ import annotations

from collections import Counter
from typing import Any

from .models import Conversation


EXPECTED_TOTAL = 65
EXPECTED_LANGUAGES = {"RU": 35, "KZ": 15, "EN": 15}
EXPECTED_CHANNELS = {"agent_chat": 60, "voice_call": 5}


def _normalize_channel(value: str) -> str:
    mapping = {
        "agent chat": "agent_chat",
        "agent_chat": "agent_chat",
        "voice call": "voice_call",
        "voice_call": "voice_call",
    }
    normalized = mapping.get(str(value).strip().lower())
    if normalized is None:
        raise ValueError(f"Unsupported channel: {value!r}")
    return normalized


def normalize_dataset(payload: dict[str, Any]) -> list[Conversation]:
    records = payload.get("records")
    if records is None and isinstance(payload.get("data"), dict):
        records = payload["data"].get("records")

    if not isinstance(records, list):
        raise ValueError("Dataset must contain records or data.records")

    normalized_records = []
    for record in records:
        item = dict(record)
        item["channel"] = _normalize_channel(item.get("channel", ""))
        normalized_records.append(item)

    return [Conversation(**record) for record in normalized_records]


def dataset_stats(records: list[Conversation]) -> dict:
    languages = Counter(x.language for x in records)
    channels = Counter(x.channel for x in records)
    return {
        "total": len(records),
        "languages": dict(languages),
        "channels": dict(channels),
    }


def validate_dev_dataset(records: list[Conversation]) -> dict:
    stats = dataset_stats(records)
    errors: list[str] = []

    if stats["total"] != EXPECTED_TOTAL:
        errors.append(f'Expected {EXPECTED_TOTAL} records, got {stats["total"]}')

    for key, expected in EXPECTED_LANGUAGES.items():
        actual = stats["languages"].get(key, 0)
        if actual != expected:
            errors.append(f"Expected {expected} {key} records, got {actual}")

    for key, expected in EXPECTED_CHANNELS.items():
        actual = stats["channels"].get(key, 0)
        if actual != expected:
            errors.append(f"Expected {expected} {key} records, got {actual}")

    return {"valid": not errors, "errors": errors, **stats}
