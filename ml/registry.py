"""Private, append-only group exposure history; never store labels here."""

import argparse
import csv
import hashlib
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

PURPOSES = ("fit", "tune", "label_analysis", "evaluation")


def initialize(directory: Path) -> None:
    directory.mkdir()
    (directory / "events").mkdir()
    with (directory / "registry.json").open("x", encoding="utf-8") as output:
        json.dump({"version": 1}, output)


def _valid_groups(groups) -> bool:
    return (
        isinstance(groups, list)
        and bool(groups)
        and all(isinstance(g, str) and g.strip() and g == g.strip() for g in groups)
        and len(set(groups)) == len(groups)
    )


def _history(directory: Path) -> list[dict]:
    header = json.loads((directory / "registry.json").read_text(encoding="utf-8"))
    if header != {"version": 1} or type(header["version"]) is not int:
        raise ValueError("Invalid registry version")
    events = []
    for path in (directory / "events").iterdir():
        event = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(event, dict) or set(event) != {
            "version",
            "run_id",
            "actor",
            "purpose",
            "recorded_at",
            "groups",
        }:
            raise ValueError("Invalid registry event")
        if (
            type(event["version"]) is not int
            or event["version"] != 1
            or event["purpose"] not in (*PURPOSES, "test_reserved")
            or not all(isinstance(event[k], str) and event[k].strip() for k in ("actor", "run_id"))
            or not _valid_groups(event["groups"])
        ):
            raise ValueError("Invalid registry event")
        stamp = datetime.fromisoformat(event["recorded_at"])
        if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
            raise ValueError("Invalid registry timestamp")
        events.append(event)
    return events


@contextmanager
def _locked(directory: Path):
    # Exclusive creation makes check + append one operation for cooperating writers.
    lock = directory / ".write-lock"
    with lock.open("x", encoding="utf-8"):
        pass
    try:
        yield
    finally:
        lock.unlink()


def _append(directory: Path, groups: list[str], run_id: str, actor: str, purpose: str) -> dict:
    event = {
        "version": 1,
        "run_id": run_id.strip(),
        "actor": actor.strip(),
        "purpose": purpose,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "groups": sorted(groups),
    }
    path = directory / "events" / f"{uuid4().hex}.json"
    with path.open("x", encoding="utf-8") as output:
        json.dump(event, output, indent=2, allow_nan=False)
    return {
        "registry_status": "checked",
        "registry_run_id": run_id.strip(),
        "registry_event_id": path.name,
        "registry_event_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def record(directory: Path, groups_csv: Path, run_id: str, actor: str, purpose: str) -> None:
    if not run_id.strip() or not actor.strip():
        raise ValueError("Run and actor must not be blank")
    with groups_csv.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or "property_group_id" not in reader.fieldnames:
            raise ValueError("Missing property_group_id column")
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("Duplicate CSV column")
        groups = [row["property_group_id"] for row in reader]
    record_groups(directory, {purpose: groups}, run_id, actor)


def record_groups(directory: Path, exposures: dict, run_id: str, actor: str) -> None:
    """Append all exposures under one lock, or none if any check fails."""
    if not run_id.strip() or not actor.strip():
        raise ValueError("Run and actor must not be blank")
    if not all(_valid_groups(groups) for groups in exposures.values()):
        raise ValueError("Invalid or duplicate group identity")
    with _locked(directory):
        events = _history(directory)
        reserved = exposures.get("test_reserved", [])
        if any(set(reserved).intersection(e["groups"]) for e in events):
            raise ValueError("Previously exposed or reserved groups; new test refused")
        for purpose, groups in exposures.items():
            _append(directory, groups, run_id, actor, purpose)


@contextmanager
def evaluation_claim(directory: Path, groups: list[str], run_id: str, actor: str):
    """Consume a matching reservation before labels; keep failure evidence and writer lock."""
    if not run_id.strip() or not actor.strip() or not _valid_groups(groups):
        raise ValueError("Invalid evaluation identity or groups")
    with _locked(directory):
        events = _history(directory)
        related = [event for event in events if set(groups).intersection(event["groups"])]
        if len(related) != 1 or (
            related[0]["purpose"] != "test_reserved"
            or related[0]["run_id"] != run_id.strip()
            or set(related[0]["groups"]) != set(groups)
        ):
            raise ValueError("Registry requires exact unused test reservation for this run")
        evidence = _append(directory, groups, run_id, actor, "evaluation")
        yield evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--registry-dir", type=Path, required=True)
    for name in ("record", "reserve-test"):
        write = commands.add_parser(name)
        write.add_argument("--registry-dir", type=Path, required=True)
        write.add_argument("--groups-csv", type=Path, required=True)
        write.add_argument("--run-id", required=True)
        write.add_argument("--actor", required=True)
        if name == "record":
            write.add_argument("--purpose", choices=PURPOSES, required=True)
    args = parser.parse_args()
    try:
        if args.command == "init":
            initialize(args.registry_dir)
        else:
            purpose = "test_reserved" if args.command == "reserve-test" else args.purpose
            record(args.registry_dir, args.groups_csv, args.run_id, args.actor, purpose)
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    print("Private exposure history recorded; this does not approve a release.")


if __name__ == "__main__":
    main()
