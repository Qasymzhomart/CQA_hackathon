"""Download and validate the organizer DEV dataset.

Usage:
    set CQA_DATASET_URL=https://.../endpoint
    python scripts/import_dev.py

The endpoint is called with ?group_id=DEV. The response may contain
records directly or under data.records.
"""

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.dataset import normalize_dataset, validate_dev_dataset


def main() -> None:
    base_url = os.getenv("CQA_DATASET_URL")
    if not base_url:
        raise SystemExit("Set CQA_DATASET_URL to the organizer dataset endpoint")

    separator = "&" if "?" in base_url else "?"
    url = f"{base_url}{separator}{urlencode({'group_id': 'DEV'})}"
    headers = {"Accept": "application/json"}

    token = os.getenv("CQA_DATASET_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with urlopen(Request(url, headers=headers), timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

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
