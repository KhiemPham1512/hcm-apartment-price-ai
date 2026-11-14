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


def test_windows_utf8_bom_manifest_keeps_string_groups(tmp_path):
    registry = tmp_path / "registry"
    assert cli("init", "--registry-dir", registry).returncode == 0
    groups = tmp_path / "groups.csv"
    groups.write_text("property_group_id\n001\n", encoding="utf-8-sig")
    result = cli(
        "reserve-test",
        "--registry-dir",
        registry,
        "--groups-csv",
        groups,
        "--run-id",
        "windows-export",
        "--actor",
        "TV6",
    )
    assert result.returncode == 0, result.stderr
    event = json.loads(next((registry / "events").iterdir()).read_text(encoding="utf-8"))
    assert event["groups"] == ["001"]


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


def train_cli(tmp_path, listings, data_kind, *args):
    """Synthetic rows; data_kind="real" only exercises the real-mode gate."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    listings.assign(
        published_at=now - timedelta(days=30),
        price_observed_at=now - timedelta(days=1),
        source_snapshot_at=now,
    ).to_csv(tmp_path / "input.csv", index=False)
    card = {
        "dataset_version": "synthetic-registry-test",
        "data_kind": data_kind,
        "geography_version": "hcm_current_v1",
        "license_reference": "synthetic test fixture",
        "source_verified": False,
        "grouping_version": "fixture-v1",
        "district_labels": {f"fixture_{i}": f"Fixture {i}" for i in range(3)},
    }
    (tmp_path / "card.json").write_text(json.dumps(card), encoding="utf-8")
    command = [sys.executable, "-B", "-m", "ml.train", "--csv", tmp_path / "input.csv"]
    command += ["--dataset-card", tmp_path / "card.json", "--output", tmp_path / "run", *args]
    return subprocess.run(list(map(str, command)), capture_output=True, text=True)


def test_training_records_fit_and_tune_groups_then_registered_evaluation_passes(tmp_path, listings):
    registry = tmp_path / "registry"
    assert cli("init", "--registry-dir", registry).returncode == 0
    trained = train_cli(
        tmp_path,
        listings,
        "synthetic",
        "--registry-dir",
        registry,
        "--run-id",
        "r1",
        "--actor",
        "TV6",
    )
    assert trained.returncode == 0, trained.stderr
    events = [json.loads(p.read_text(encoding="utf-8")) for p in (registry / "events").iterdir()]
    splits = (tmp_path / "run" / "splits.csv").read_text(encoding="utf-8").splitlines()[1:]
    expected = {"fit": "train", "tune": "validation"}
    assert sorted(e["purpose"] for e in events) == ["fit", "tune"]
    for event in events:
        assert event["run_id"] == "r1" and event["actor"] == "TV6"
        assert event["groups"] == sorted(
            row.split(",")[2] for row in splits if row.split(",")[3] == expected[event["purpose"]]
        )
    assert "asking_price_vnd" not in json.dumps(events)
    test_groups = tmp_path / "test-groups.csv"
    test_groups.write_text(
        "property_group_id\n"
        + "\n".join(row.split(",")[2] for row in splits if row.endswith(",test")),
        encoding="utf-8",
    )
    reserve = ["--groups-csv", test_groups, "--run-id", "r1", "--actor", "TV6"]
    assert cli("reserve-test", "--registry-dir", registry, *reserve).returncode == 0
    for command in (
        ["ml.freeze", "--run-dir", tmp_path / "run", "--reviewer", "technical-test-reviewer"],
        ["ml.evaluate", "--run-dir", tmp_path / "run", "--registry-dir", registry]
        + ["--run-id", "r1", "--actor", "TV6"],
    ):
        result = subprocess.run(
            [sys.executable, "-B", "-m", *map(str, command)], capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("problem", ["real_without_registry", "partial", "missing", "busy"])
def test_training_registry_gate_fails_before_fit_without_output_or_history(
    tmp_path, listings, problem
):
    registry = tmp_path / "registry"
    if problem != "missing":
        assert cli("init", "--registry-dir", registry).returncode == 0
    if problem == "busy":
        (registry / ".write-lock").write_text("another writer", encoding="utf-8")
    args = {
        "real_without_registry": [],
        "partial": ["--registry-dir", registry, "--run-id", "r1"],
    }.get(problem, ["--registry-dir", registry, "--run-id", "r1", "--actor", "TV6"])
    data_kind = "real" if problem == "real_without_registry" else "synthetic"
    result = train_cli(tmp_path, listings, data_kind, *args)
    assert result.returncode != 0
    assert not (tmp_path / "run").exists()
    if registry.exists():
        assert not list((registry / "events").iterdir())
    if problem == "busy":
        assert (registry / ".write-lock").read_text(encoding="utf-8") == "another writer"
