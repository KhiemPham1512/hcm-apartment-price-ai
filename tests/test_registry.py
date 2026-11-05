"""Private exposure registry CLI; synthetic group identities only."""

import json
import subprocess
import sys

import pytest


def cli(*args):
    return subprocess.run(
        [sys.executable, "-B", "-m", "ml.registry", *map(str, args)],
        capture_output=True,
        text=True,
    )


def test_records_group_usage_without_labels_or_overwriting_history(tmp_path):
    registry = tmp_path / "registry"
    groups = tmp_path / "groups.csv"
    groups.write_text("property_group_id,asking_price_vnd\n001,123\n002,456\n", encoding="utf-8")
    result = cli("init", "--registry-dir", registry)
    assert result.returncode == 0, result.stderr
    args = [
        "record",
        "--registry-dir",
        registry,
        "--groups-csv",
        groups,
        "--run-id",
        "synthetic-run",
        "--actor",
        "TV6",
        "--purpose",
        "fit",
    ]
    result = cli(*args)
    assert result.returncode == 0, result.stderr
    events = list((registry / "events").glob("*.json"))
    original = events[0].read_bytes()
    event = json.loads(original)
    assert event["groups"] == ["001", "002"]
    assert event["purpose"] == "fit"
    assert event["run_id"] == "synthetic-run"
    assert event["actor"] == "TV6"
    assert "asking_price_vnd" not in original.decode()
    assert cli(*args).returncode == 0
    assert events[0].read_bytes() == original
    assert len(list((registry / "events").glob("*.json"))) == 2


@pytest.mark.parametrize("purpose", ["fit", "tune", "label_analysis", "evaluation"])
def test_new_test_rejects_any_exposed_group_even_in_another_run(tmp_path, purpose):
    registry = tmp_path / "registry"
    groups = tmp_path / "groups.csv"
    groups.write_text("property_group_id\n001\n", encoding="utf-8")
    assert cli("init", "--registry-dir", registry).returncode == 0
    assert (
        cli(
            "record",
            "--registry-dir",
            registry,
            "--groups-csv",
            groups,
            "--run-id",
            "old",
            "--actor",
            "TV2",
            "--purpose",
            purpose,
        ).returncode
        == 0
    )
    before = {p.name: p.read_bytes() for p in (registry / "events").iterdir()}
    result = cli(
        "reserve-test",
        "--registry-dir",
        registry,
        "--groups-csv",
        groups,
        "--run-id",
        "new",
        "--actor",
        "TV6",
    )
    assert result.returncode != 0
    assert "Previously exposed or reserved groups" in result.stderr
    assert "001" not in result.stderr  # Do not print private identities in diagnostics.
    assert {p.name: p.read_bytes() for p in (registry / "events").iterdir()} == before


def test_test_reservation_cannot_be_claimed_twice(tmp_path):
    registry = tmp_path / "registry"
    groups = tmp_path / "groups.csv"
    groups.write_text("property_group_id\n001\n002\n", encoding="utf-8")
    assert cli("init", "--registry-dir", registry).returncode == 0
    args = [
        "reserve-test",
        "--registry-dir",
        registry,
        "--groups-csv",
        groups,
        "--run-id",
        "new",
        "--actor",
        "TV6",
    ]
    result = cli(*args)
    assert result.returncode == 0, result.stderr
    events = list((registry / "events").glob("*.json"))
    assert json.loads(events[0].read_text(encoding="utf-8"))["purpose"] == "test_reserved"
    assert cli(*args).returncode != 0
    assert len(list((registry / "events").glob("*.json"))) == 1


@pytest.mark.parametrize("problem", ["missing", "corrupt_header", "corrupt_event", "locked"])
def test_incomplete_or_busy_history_never_becomes_a_clean_registry(tmp_path, problem):
    registry = tmp_path / "registry"
    groups = tmp_path / "groups.csv"
    groups.write_text("property_group_id\n001\n", encoding="utf-8")
    if problem != "missing":
        assert cli("init", "--registry-dir", registry).returncode == 0
        if problem == "corrupt_header":
            (registry / "registry.json").write_text('{"version":true}', encoding="utf-8")
        elif problem == "corrupt_event":
            (registry / "events" / "broken.json").write_text("{}", encoding="utf-8")
        else:
            (registry / ".write-lock").write_text("another writer", encoding="utf-8")
    result = cli(
        "reserve-test",
        "--registry-dir",
        registry,
        "--groups-csv",
        groups,
        "--run-id",
        "new",
        "--actor",
        "TV6",
    )
    assert result.returncode != 0
    assert not registry.exists() or not any(
        p.name != "broken.json" for p in (registry / "events").iterdir()
    )
    if problem == "locked":
        assert (registry / ".write-lock").read_text(encoding="utf-8") == "another writer"
    elif problem != "missing":
        assert not (registry / ".write-lock").exists()


@pytest.mark.parametrize(
    "content",
    [
        "wrong_column\n001\n",
        "property_group_id\n",
        'property_group_id\n" "\n',
        "property_group_id\n001\n001\n",
    ],
)
def test_invalid_group_manifest_does_not_create_history(tmp_path, content):
    registry = tmp_path / "registry"
    assert cli("init", "--registry-dir", registry).returncode == 0
    groups = tmp_path / "groups.csv"
    groups.write_text(content, encoding="utf-8")
    assert (
        cli(
            "record",
            "--registry-dir",
            registry,
            "--groups-csv",
            groups,
            "--run-id",
            "new",
            "--actor",
            "TV6",
            "--purpose",
            "fit",
        ).returncode
        != 0
    )
    assert not list((registry / "events").iterdir())


def test_concurrent_test_claims_have_only_one_success(tmp_path):
    registry = tmp_path / "registry"
    groups = tmp_path / "groups.csv"
    groups.write_text("property_group_id\n001\n", encoding="utf-8")
    assert cli("init", "--registry-dir", registry).returncode == 0
    command = [
        sys.executable,
        "-B",
        "-m",
        "ml.registry",
        "reserve-test",
        "--registry-dir",
        str(registry),
        "--groups-csv",
        str(groups),
        "--run-id",
        "new",
        "--actor",
        "TV6",
    ]
    processes = [
        subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)
    ]
    for process in processes:
        process.communicate(timeout=30)
    assert sum(process.returncode == 0 for process in processes) == 1
    assert len(list((registry / "events").glob("*.json"))) == 1


def test_ambiguous_group_column_is_rejected_instead_of_losing_an_identity(tmp_path):
    registry = tmp_path / "registry"
    assert cli("init", "--registry-dir", registry).returncode == 0
    groups = tmp_path / "groups.csv"
    groups.write_text("property_group_id,property_group_id\n001,002\n", encoding="utf-8")
    result = cli(
        "record",
        "--registry-dir",
        registry,
        "--groups-csv",
        groups,
        "--run-id",
        "new",
        "--actor",
        "TV6",
        "--purpose",
        "fit",
    )
    assert result.returncode != 0
    assert not list((registry / "events").iterdir())


def test_mixed_reservation_is_atomic_and_exposure_facts_can_be_recorded_after_reserving(tmp_path):
    registry = tmp_path / "registry"
    assert cli("init", "--registry-dir", registry).returncode == 0
    groups = tmp_path / "groups.csv"
    groups.write_text("property_group_id\n001\n", encoding="utf-8")
    common = [
        "--registry-dir",
        registry,
        "--groups-csv",
        groups,
        "--run-id",
        "new",
        "--actor",
        "TV6",
    ]
    assert cli("reserve-test", *common).returncode == 0
    assert cli("record", *common, "--purpose", "label_analysis").returncode == 0
    before = {p.name: p.read_bytes() for p in (registry / "events").iterdir()}
    groups.write_text("property_group_id\n001\n002\n", encoding="utf-8")
    assert cli("reserve-test", *common).returncode != 0
    assert {p.name: p.read_bytes() for p in (registry / "events").iterdir()} == before
    # The unused group was not consumed by the rejected mixed request.
    groups.write_text("property_group_id\n002\n", encoding="utf-8")
    assert cli("reserve-test", *common).returncode == 0
