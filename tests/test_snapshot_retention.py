import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.snapshots.retention import prune_snapshot_history


def _write_history(directory, count, *, suffix=".json", snapshot_name="aws-config"):
    directory.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 8, 1, tzinfo=timezone.utc)
    paths = []

    for index in range(count):
        timestamp = (start + timedelta(minutes=15 * index)).strftime(
            "%Y%m%dT%H%M%SZ"
        )
        path = directory / f"{snapshot_name}-{timestamp}{suffix}"
        path.write_text(f"generated test artifact {index}\n", encoding="utf-8")
        paths.append(path)

    return paths


@pytest.mark.parametrize(
    ("snapshot_count", "report_count", "retention_count"),
    [
        (5, 4, 2),
        (3, 7, 2),
        (2, 2, 2),
        (1, 0, 2),
        (0, 0, 2),
        (3, 2, 10),
        (673, 673, 672),
    ],
)
def test_retention_caps_each_directory_independently(
    tmp_path, snapshot_count, report_count, retention_count
):
    snapshot_dir = tmp_path / "snapshots"
    report_dir = tmp_path / "diffs"
    snapshots = _write_history(snapshot_dir, snapshot_count)
    reports = _write_history(report_dir, report_count, suffix="-diff.md")
    original_contents = {
        path: path.read_bytes() for path in [*snapshots, *reports]
    }

    result = prune_snapshot_history(
        retention_count=retention_count,
        snapshot_dir=snapshot_dir,
        report_dir=report_dir,
    )

    assert result.deleted_snapshots == tuple(snapshots[:-retention_count])
    assert result.deleted_reports == tuple(reports[:-retention_count])
    assert sorted(snapshot_dir.iterdir()) == snapshots[-retention_count:]
    assert sorted(report_dir.iterdir()) == reports[-retention_count:]
    for path in [*snapshots[-retention_count:], *reports[-retention_count:]]:
        assert path.read_bytes() == original_contents[path]

    second_result = prune_snapshot_history(
        retention_count=retention_count,
        snapshot_dir=snapshot_dir,
        report_dir=report_dir,
    )
    assert second_result.deleted_snapshots == ()
    assert second_result.deleted_reports == ()


def test_retention_orders_by_filename_not_modification_time(tmp_path):
    snapshots = _write_history(tmp_path / "snapshots", 4)
    reports = _write_history(tmp_path / "diffs", 4, suffix="-diff.md")
    for paths in (snapshots, reports):
        for index, path in enumerate(paths):
            os.utime(path, (1000 - index, 1000 - index))

    result = prune_snapshot_history(
        retention_count=2,
        snapshot_dir=tmp_path / "snapshots",
        report_dir=tmp_path / "diffs",
    )

    assert result.deleted_snapshots == tuple(snapshots[:2])
    assert result.deleted_reports == tuple(reports[:2])


def test_retention_leaves_unrelated_and_malformed_files_untouched(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    report_dir = tmp_path / "diffs"
    snapshots = _write_history(snapshot_dir, 3)
    reports = _write_history(report_dir, 3, suffix="-diff.md")
    untouched = []
    for directory, suffix in [(snapshot_dir, ".json"), (report_dir, "-diff.md")]:
        for name in [
            "aws_guardian_report.json",
            "README.md",
            "aws-config-before.example.json",
            f"other-20260801T000000Z{suffix}",
            f"aws-config-backup-20260801T000000Z{suffix}",
            f"aws-config-20260801T000000Z{suffix}.tmp",
            f"aws-config-20260801T000000Z{suffix}.bak",
            f"aws-config-20261301T000000Z{suffix}",
            f"aws-config-20260230T000000Z{suffix}",
            f"aws-config-20260801T240000Z{suffix}",
            f"aws-config-20260801T00000Z{suffix}",
        ]:
            path = directory / name
            path.write_text("unrelated test data", encoding="utf-8")
            untouched.append(path)

        nested = directory / f"aws-config-20260801T010000Z{suffix}"
        nested.mkdir()
        child = nested / f"aws-config-20260801T000000Z{suffix}"
        child.write_text("nested test data", encoding="utf-8")
        untouched.append(child)

    snapshot_in_report_dir = report_dir / snapshots[0].name
    report_in_snapshot_dir = snapshot_dir / reports[0].name
    for path in (snapshot_in_report_dir, report_in_snapshot_dir):
        path.write_text("wrong directory", encoding="utf-8")
        untouched.append(path)
    original_contents = {path: path.read_bytes() for path in untouched}

    result = prune_snapshot_history(
        retention_count=2, snapshot_dir=snapshot_dir, report_dir=report_dir
    )

    assert result.deleted_snapshots == (snapshots[0],)
    assert result.deleted_reports == (reports[0],)
    for path in untouched:
        assert path.read_bytes() == original_contents[path]


def test_retention_excludes_file_symlinks_from_cleanup_and_counts(tmp_path):
    snapshots = _write_history(tmp_path / "snapshots", 3)
    reports = _write_history(tmp_path / "diffs", 3, suffix="-diff.md")
    target = tmp_path / "outside-history.json"
    target.write_text("keep me", encoding="utf-8")
    links = []

    for directory, suffix in [
        (tmp_path / "snapshots", ".json"),
        (tmp_path / "diffs", "-diff.md"),
    ]:
        for timestamp in ("20250701T000000Z", "20270901T000000Z"):
            link = directory / f"aws-config-{timestamp}{suffix}"
            link.symlink_to(target)
            links.append(link)
        broken_link = directory / f"aws-config-20280901T000000Z{suffix}"
        broken_link.symlink_to(tmp_path / "missing")
        links.append(broken_link)

    result = prune_snapshot_history(
        retention_count=2,
        snapshot_dir=tmp_path / "snapshots",
        report_dir=tmp_path / "diffs",
    )

    assert result.deleted_snapshots == (snapshots[0],)
    assert result.deleted_reports == (reports[0],)
    assert all(link.is_symlink() for link in links)
    assert target.read_text(encoding="utf-8") == "keep me"


@pytest.mark.parametrize("linked_directory", ["snapshots", "diffs"])
def test_retention_rejects_directory_symlinks_before_any_deletion(
    tmp_path, linked_directory
):
    directories = {
        "snapshots": tmp_path / "snapshots",
        "diffs": tmp_path / "diffs",
    }
    target = tmp_path / "symlink-target"
    target.mkdir()
    directories[linked_directory].symlink_to(target, target_is_directory=True)
    snapshots = _write_history(directories["snapshots"], 3)
    reports = _write_history(directories["diffs"], 3, suffix="-diff.md")

    with pytest.raises(ValueError, match="must not be a symlink"):
        prune_snapshot_history(
            retention_count=2,
            snapshot_dir=directories["snapshots"],
            report_dir=directories["diffs"],
        )

    assert all(path.exists() for path in [*snapshots, *reports])


@pytest.mark.parametrize("retention_count", [None, 0, 1, -5, True, False, 2.5, "2"])
def test_retention_rejects_invalid_counts_without_deleting(tmp_path, retention_count):
    snapshots = _write_history(tmp_path / "snapshots", 3)
    reports = _write_history(tmp_path / "diffs", 3, suffix="-diff.md")

    with pytest.raises(ValueError, match="integer of at least 2"):
        prune_snapshot_history(
            retention_count=retention_count,
            snapshot_dir=tmp_path / "snapshots",
            report_dir=tmp_path / "diffs",
        )

    assert all(path.exists() for path in [*snapshots, *reports])


def test_retention_normalises_the_selected_snapshot_name(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    report_dir = tmp_path / "diffs"
    snapshots = _write_history(snapshot_dir, 3, snapshot_name="portfolio-scan")
    reports = _write_history(
        report_dir, 3, suffix="-diff.md", snapshot_name="portfolio-scan"
    )
    other_snapshots = _write_history(snapshot_dir, 3)
    other_reports = _write_history(report_dir, 3, suffix="-diff.md")

    result = prune_snapshot_history(
        retention_count=2,
        snapshot_dir=snapshot_dir,
        report_dir=report_dir,
        snapshot_name="Portfolio_Scan",
    )

    assert result.deleted_snapshots == (snapshots[0],)
    assert result.deleted_reports == (reports[0],)
    assert all(path.exists() for path in [*other_snapshots, *other_reports])


def test_retention_rejects_empty_snapshot_name(tmp_path):
    snapshots = _write_history(tmp_path / "snapshots", 3)

    with pytest.raises(ValueError, match="snapshot_name"):
        prune_snapshot_history(
            retention_count=2,
            snapshot_dir=tmp_path / "snapshots",
            report_dir=tmp_path / "diffs",
            snapshot_name="",
        )

    assert all(path.exists() for path in snapshots)


def test_retention_missing_directories_is_a_noop(tmp_path):
    result = prune_snapshot_history(
        retention_count=2,
        snapshot_dir=tmp_path / "missing-snapshots",
        report_dir=tmp_path / "missing-diffs",
    )

    assert result.deleted_snapshots == ()
    assert result.deleted_reports == ()
    assert list(tmp_path.iterdir()) == []


def test_retention_validates_both_directories_before_deleting(tmp_path):
    snapshots = _write_history(tmp_path / "snapshots", 3)
    invalid_report_dir = tmp_path / "not-a-directory"
    invalid_report_dir.write_text("keep me", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        prune_snapshot_history(
            retention_count=2,
            snapshot_dir=tmp_path / "snapshots",
            report_dir=invalid_report_dir,
        )

    assert all(path.exists() for path in snapshots)
    assert invalid_report_dir.read_text(encoding="utf-8") == "keep me"


def test_retention_surfaces_filesystem_deletion_errors(tmp_path, monkeypatch):
    snapshots = _write_history(tmp_path / "snapshots", 3)

    def fail_unlink(self):
        raise PermissionError("cleanup denied")

    monkeypatch.setattr(Path, "unlink", fail_unlink)

    with pytest.raises(PermissionError, match="cleanup denied"):
        prune_snapshot_history(
            retention_count=2,
            snapshot_dir=tmp_path / "snapshots",
            report_dir=tmp_path / "diffs",
        )

    assert all(path.exists() for path in snapshots)
