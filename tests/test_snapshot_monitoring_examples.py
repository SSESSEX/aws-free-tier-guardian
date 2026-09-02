from pathlib import Path

from app.snapshots.diff import diff_resources
from app.snapshots.report import render_snapshot_diff_markdown
from app.snapshots.store import load_snapshot


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = PROJECT_ROOT / "examples" / "snapshot-monitoring"
BEFORE_PATH = EXAMPLE_DIR / "aws-config-before.example.json"
AFTER_PATH = EXAMPLE_DIR / "aws-config-after.example.json"
DIFF_PATH = EXAMPLE_DIR / "aws-config-diff.example.md"


def test_snapshot_monitoring_examples_match_generated_diff():
    previous_snapshot = load_snapshot(BEFORE_PATH)
    current_snapshot = load_snapshot(AFTER_PATH)

    diff_result = diff_resources(
        previous_snapshot["resources"],
        current_snapshot["resources"],
    )

    assert diff_result["summary"] == {
        "previous_count": 4,
        "current_count": 4,
        "added_count": 1,
        "removed_count": 1,
        "changed_count": 1,
        "unchanged_count": 2,
    }

    generated_markdown = render_snapshot_diff_markdown(
        previous_snapshot,
        current_snapshot,
        diff_result,
    )

    assert DIFF_PATH.read_text(encoding="utf-8") == generated_markdown


def test_snapshot_monitoring_examples_use_consistent_resource_counts():
    for snapshot_path in (BEFORE_PATH, AFTER_PATH):
        snapshot = load_snapshot(snapshot_path)

        assert snapshot["resource_count"] == len(snapshot["resources"])
        assert snapshot["metadata"]["data_classification"] == "sanitised-example"
