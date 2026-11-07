"""Download and validate the organizer DEV dataset.

Usage (PowerShell):
    $env:CQA_DATASET_URL="https://...&group_id=DEV"
    python scripts/import_dev.py

You may pass either:
- the full organizer URL that already contains group_id=DEV; or
- the base organizer URL without group_id.

The response may contain records directly or under data.records.
"""

import json
import os
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.dataset import normalize_dataset, validate_dev_dataset


def ensure_group_id(url: str, group_id: str = "DEV") -> str:
    parts = urlsplit(url)
    query_items = parse_qsl(parts.query, keep_blank_values=True)

    if not any(key == "group_id" for key, _ in query_items):
        query_items.append(("group_id", group_id))

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query_items),
            parts.fragment,
        )
    )


def main() -> None:
    base_url = os.getenv("CQA_DATASET_URL")
    if not base_url:
        raise SystemExit("Set CQA_DATASET_URL to the organizer dataset endpoint")

    url = ensure_group_id(base_url, "DEV")
    headers = {"Accept": "application/json"}

    token = os.getenv("CQA_DATASET_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with urlopen(Request(url, headers=headers), timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("isSuccess") is False:
        raise SystemExit(f"Organizer API returned an error: {payload.get('error')}")

    records = normalize_dataset(payload)
    validation = validate_dev_dataset(records)

    out = ROOT / "data" / "dev_dataset.json"
    out.write_text(
        json.dumps(
            {
                "dataset_group_id": "DEV",
                "total_records": len(records),
                "records": [x.model_dump() for x in records],
                "validation": validation,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(json.dumps(validation, ensure_ascii=False, indent=2))
    print(f"Saved: {out}")

    if not validation["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
