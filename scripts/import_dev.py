"""Backward-compatible DEV importer.

Prefer:
    python scripts/import_dataset.py --group-id DEV
"""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    script = Path(__file__).with_name("import_dataset.py")
    raise SystemExit(
        subprocess.call([sys.executable, str(script), "--group-id", "DEV"])
    )


if __name__ == "__main__":
    main()
