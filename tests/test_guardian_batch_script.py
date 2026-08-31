import os
from pathlib import Path
import shutil
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_guardian_batch.sh"


def _create_test_project(tmp_path):
    project_root = tmp_path / "project"
    scripts_dir = project_root / "scripts"
    scripts_dir.mkdir(parents=True)

    copied_script = scripts_dir / SCRIPT_PATH.name
    shutil.copy2(SCRIPT_PATH, copied_script)
    copied_script.chmod(0o755)

    return project_root, copied_script


def _write_fake_python(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """#!/usr/bin/env bash
{
    printf 'cwd=%s\n' "$PWD"
    printf 'arg=%s\n' "$@"
} > "${GUARDIAN_TEST_CAPTURE_PATH}"

exit "${GUARDIAN_TEST_EXIT_CODE:-0}"
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _run_script(script_path, *, cwd, capture_path, exit_code=0, path=None, args=None):
    environment = os.environ.copy()
    environment["GUARDIAN_TEST_CAPTURE_PATH"] = str(capture_path)
    environment["GUARDIAN_TEST_EXIT_CODE"] = str(exit_code)

    if path is not None:
        environment["PATH"] = path

    return subprocess.run(
        [str(script_path), *(args or [])],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_batch_script_uses_project_venv_and_forwards_arguments(tmp_path):
    project_root, script_path = _create_test_project(tmp_path)
    fake_python = project_root / ".venv" / "bin" / "python"
    capture_path = tmp_path / "capture.txt"
    outside_directory = tmp_path / "outside"

    outside_directory.mkdir()
    _write_fake_python(fake_python)

    result = _run_script(
        script_path,
        cwd=outside_directory,
        capture_path=capture_path,
        args=["--snapshot-name", "portfolio-scan"],
    )

    assert result.returncode == 0
    assert capture_path.read_text(encoding="utf-8").splitlines() == [
        f"cwd={project_root}",
        "arg=-m",
        "arg=app.snapshots.run_guardian_batch",
        "arg=--snapshot-name",
        "arg=portfolio-scan",
    ]
    assert f"Project root: {project_root}" in result.stdout
    assert f"Python: {fake_python}" in result.stdout
    assert f"Snapshots directory: {project_root / 'reports' / 'snapshots'}" in result.stdout
    assert (
        f"Diff reports directory: {project_root / 'reports' / 'snapshot-diffs'}"
        in result.stdout
    )


def test_batch_script_falls_back_to_python3_when_venv_is_unavailable(tmp_path):
    project_root, script_path = _create_test_project(tmp_path)
    fake_bin_dir = tmp_path / "fake-bin"
    fake_python = fake_bin_dir / "python3"
    capture_path = tmp_path / "capture.txt"

    _write_fake_python(fake_python)

    result = _run_script(
        script_path,
        cwd=tmp_path,
        capture_path=capture_path,
        path=f"{fake_bin_dir}:{os.environ['PATH']}",
    )

    assert result.returncode == 0
    assert "arg=app.snapshots.run_guardian_batch" in capture_path.read_text(
        encoding="utf-8"
    )
    assert "Python: python3" in result.stdout


def test_batch_script_propagates_batch_runner_failure(tmp_path):
    project_root, script_path = _create_test_project(tmp_path)
    fake_python = project_root / ".venv" / "bin" / "python"
    capture_path = tmp_path / "capture.txt"

    _write_fake_python(fake_python)

    result = _run_script(
        script_path,
        cwd=tmp_path,
        capture_path=capture_path,
        exit_code=7,
    )

    assert result.returncode == 7
    assert "Batch monitoring completed successfully." not in result.stdout
    assert "Snapshots directory:" not in result.stdout
