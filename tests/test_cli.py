"""Tests for the openscout command-line interface."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from openscout.cli import main


def test_list_sports_command(capsys):
    exit_code = main(["list-sports"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "basketball:" in captured.out
    assert "soccer:" in captured.out
    assert "ts_pct" in captured.out


def test_analyze_command_with_json_input(tmp_path, capsys):
    data_file = tmp_path / "box.json"
    data_file.write_text(json.dumps({"pts": 25, "fga": 18, "fta": 6}))

    args = ["analyze", "--sport", "basketball", "--metric", "ts_pct", "--input", str(data_file)]
    exit_code = main(args)
    captured = capsys.readouterr()

    assert exit_code == 0
    assert float(captured.out.strip()) == pytest.approx(25 / (2 * (18 + 0.44 * 6)))


def test_analyze_command_with_csv_input(tmp_path, capsys):
    data_file = tmp_path / "passes.csv"
    data_file.write_text("completed\nTrue\nTrue\nFalse\nTrue\n")

    args = ["analyze", "--sport", "soccer", "--metric", "pass_pct", "--input", str(data_file)]
    exit_code = main(args)
    captured = capsys.readouterr()

    assert exit_code == 0
    assert float(captured.out.strip()) == pytest.approx(75.0)


def test_analyze_command_unknown_sport_returns_error_exit_code(tmp_path, capsys):
    data_file = tmp_path / "box.json"
    data_file.write_text(json.dumps({"pts": 1}))

    args = ["analyze", "--sport", "cricket", "--metric", "runs", "--input", str(data_file)]
    exit_code = main(args)
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "error" in captured.err


def test_analyze_command_missing_input_file_returns_error_exit_code(capsys):
    exit_code = main(
        ["analyze", "--sport", "basketball", "--metric", "ts_pct", "--input", "does-not-exist.json"]
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "error" in captured.err


def test_demo_command_basketball_default_metric(capsys):
    exit_code = main(["demo", "--sport", "basketball"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "ts_pct result" in captured.out
    assert "synthetic" in captured.out


def test_demo_command_soccer_with_explicit_metric(capsys):
    exit_code = main(["demo", "--sport", "soccer", "--metric", "pass_pct"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "pass_pct result" in captured.out


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "openscout" in captured.out


def test_console_script_is_actually_installed_and_runnable():
    """End-to-end check that the `openscout` console_script entry point
    from pyproject.toml is wired up correctly, not just the Python API."""
    result = subprocess.run(
        [sys.executable, "-m", "openscout.cli", "list-sports"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "basketball" in result.stdout
