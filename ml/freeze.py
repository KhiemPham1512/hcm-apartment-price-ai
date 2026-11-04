"""Record reviewed candidate bytes before final holdout evaluation."""

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ARTIFACTS = ("candidates.joblib", "splits.csv", "holdout.csv")


def _hash(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def freeze(run_dir: Path, reviewer: str) -> dict:
    reviewer = reviewer.strip()
    if not reviewer:
        raise ValueError("Reviewer must not be blank")
    if (run_dir / "evaluation.json").exists():
        raise ValueError("Already evaluated; cannot create retrospective freeze evidence")
    record = {
        "version": 1,
        "reviewer": reviewer,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": {name: _hash(run_dir / name) for name in ARTIFACTS},
    }
    with (run_dir / "freeze.json").open("x", encoding="utf-8") as output:
        json.dump(record, output, indent=2, allow_nan=False)
    return record


def verify_freeze(run_dir: Path) -> dict:
    """Verify reviewed bytes before callers deserialize candidate or test data."""
    payload = (run_dir / "freeze.json").read_bytes()
    record = json.loads(payload)
    if not isinstance(record, dict) or set(record) != {
        "version",
        "reviewer",
        "frozen_at",
        "artifacts",
    }:
        raise ValueError("Invalid freeze record fields")
    if type(record["version"]) is not int or record["version"] != 1:
        raise ValueError("Unsupported freeze record version")
    if not isinstance(record["reviewer"], str) or not record["reviewer"].strip():
        raise ValueError("Invalid freeze reviewer")
    stamp = datetime.fromisoformat(record["frozen_at"])
    if stamp.tzinfo is None or stamp.utcoffset() is None or stamp > datetime.now(timezone.utc):
        raise ValueError("Invalid freeze timestamp")
    hashes = record["artifacts"]
    if not isinstance(hashes, dict) or set(hashes) != set(ARTIFACTS):
        raise ValueError("Invalid frozen artifact set")
    for name in ARTIFACTS:
        expected = hashes[name]
        if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
            raise ValueError(f"Invalid frozen hash: {name}")
        if _hash(run_dir / name) != expected:
            raise ValueError(f"Frozen {name.removesuffix('.csv')} data was modified after review")
    return record | {"sha256": hashlib.sha256(payload).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--reviewer", required=True)
    args = parser.parse_args()
    try:
        freeze(args.run_dir, args.reviewer)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print("Candidate bytes frozen; labels not evaluated; release not approved.")


if __name__ == "__main__":
    main()
