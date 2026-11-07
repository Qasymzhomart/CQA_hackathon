"""Download an organizer dataset by group_id and normalize it.

PowerShell:
    $env:CQA_DATASET_URL="FULL_ORGANIZER_URL"
    python scripts/import_dataset.py --group-id DEV
    python scripts/import_dataset.py --group-id CONTROL_ID

If the URL already contains group_id, --group-id replaces only that value.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.dataset import normalize_dataset, validate_dev_dataset


def with_group_id(url: str, group_id: str) -> str:
    parts = urlsplit(url)
    query_items = parse_qsl(parts.query, keep_blank_values=True)

    replaced = False
    updated = []
    for key, value in query_items:
        if key == "group_id":
            updated.append((key, group_id))
            replaced = True
        else:
            updated.append((key, value))

    if not replaced:
        updated.append(("group_id", group_id))

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(updated),
            parts.fragment,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group-id", default="DEV")
    args = parser.parse_args()

    base_url = os.getenv("CQA_DATASET_URL")
    if not base_url:
        raise SystemExit("Set CQA_DATASET_URL to the organizer dataset endpoint")

    url = with_group_id(base_url, args.group_id)
    headers = {"Accept": "application/json"}

    token = os.getenv("CQA_DATASET_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with urlopen(Request(url, headers=headers), timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("isSuccess") is False:
        raise SystemExit(f"Organizer API returned an error: {payload.get('error')}")

    records = normalize_dataset(payload)
    dataset_group_id = (
        payload.get("data", {}).get("dataset_group_id")
        or payload.get("dataset_group_id")
        or args.group_id
    )

    result = {
        "dataset_group_id": dataset_group_id,
        "total_records": len(records),
        "records": [x.model_dump() for x in records],
    }

    if args.group_id.upper() == "DEV":
        result["validation"] = validate_dev_dataset(records)
        if not result["validation"]["valid"]:
            print(json.dumps(result["validation"], ensure_ascii=False, indent=2))
            raise SystemExit(1)

    safe_name = "".join(
        c.lower() if c.isalnum() else "_"
        for c in args.group_id
    ).strip("_") or "dataset"
    out = ROOT / "data" / f"{safe_name}_dataset.json"
    out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"group_id: {dataset_group_id}")
    print(f"records: {len(records)}")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
