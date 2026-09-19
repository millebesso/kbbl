"""`kbbl run <scenario>` — loads, prints the chamber, exits."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from conftest import FOUR_PARTY, positions, two_party
from kbbl.cli import main


def test_run_prints_the_chamber_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["run", str(FOUR_PARTY)])

    out = capsys.readouterr().out
    assert code == 0
    assert "four-party" in out
    assert "FF" in out
    assert "349" in out
    assert "175" in out


def test_a_malformed_mandate_fails_without_a_stack_trace(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    two_party(tmp_path, positions=positions(environment=6))

    code = main(["run", str(tmp_path)])

    captured = capsys.readouterr()
    assert code != 0
    assert "AA" in captured.err
    assert "positions.environment" in captured.err
    assert "Traceback" not in captured.err


def test_the_module_entry_point_runs_a_scenario() -> None:
    finished = subprocess.run(
        [sys.executable, "-m", "kbbl", "run", str(FOUR_PARTY)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert finished.returncode == 0, finished.stderr
    assert "349" in finished.stdout


def test_the_console_script_runs_a_scenario() -> None:
    """`uv run kbbl run <scenario>` is the documented interface, so it is the one tested."""
    script = Path(sys.executable).parent / "kbbl"
    if not script.exists():
        pytest.skip("kbbl console script is not installed in this environment")

    finished = subprocess.run(
        [str(script), "run", str(FOUR_PARTY)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert finished.returncode == 0, finished.stderr
    assert "349" in finished.stdout
