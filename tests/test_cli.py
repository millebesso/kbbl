"""`kbbl run <scenario>` — loads, prints the chamber, holds a Bilateral, exits.

Nothing here calls the model. Most tests record a Bilateral against a scripted stand-in and
then replay those Cassettes through the real CLI, which exercises the whole wiring for free;
one test replays the committed recordings of an actual Run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from conftest import CASSETTES, FOUR_PARTY, Model, positions, spoken, two_party
from kbbl.agents import bilateral
from kbbl.cassettes import Cassettes
from kbbl.cli import main
from kbbl.scenario import load_scenario


@pytest.fixture
def replay(tmp_path: Path) -> list[str]:
    """Cassettes for the two Bilaterals these tests ask for, recorded off a scripted Agent."""
    scenario = load_scenario(FOUR_PARTY)
    model = Model(
        spoken("Abstain and the broadband money is yours."),
        spoken("Not for that price."),
        spoken("Then we are done here.", "impasse"),
    )
    for counterparty in ("FF", "MI"):
        bilateral(
            scenario,
            formateur=scenario.parties[0],
            counterparty=scenario.party(counterparty),
            cassettes=Cassettes(tmp_path / scenario.name, live=model),
        )
    return ["--replay", "--cassettes", str(tmp_path)]


def test_run_prints_the_chamber_and_exits_zero(
    replay: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["run", str(FOUR_PARTY), *replay])

    out = capsys.readouterr().out
    assert code == 0
    assert "four-party" in out
    assert "FF" in out
    assert "349" in out
    assert "175" in out


def test_run_holds_a_bilateral_and_prints_the_transcript(
    replay: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["run", str(FOUR_PARTY), *replay])

    out = capsys.readouterr().out
    assert code == 0
    assert "Bilateral: NP meets FF" in out
    assert "Formateur: NP" in out
    assert "Abstain and the broadband money is yours." in out
    assert "Ended: NP declared impasse" in out


def test_the_formateur_can_be_pointed_at_another_party(
    replay: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["run", str(FOUR_PARTY), "--meet", "MI", *replay])

    assert code == 0
    assert "Bilateral: NP meets MI" in capsys.readouterr().out


def test_replay_is_identical_every_time(
    replay: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """The Transcript is a function of the Cassettes, not of when it was replayed."""
    main(["run", str(FOUR_PARTY), *replay])
    once = capsys.readouterr().out
    main(["run", str(FOUR_PARTY), *replay])

    assert capsys.readouterr().out == once


def test_a_missing_cassette_explains_itself_without_a_stack_trace(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["run", str(FOUR_PARTY), "--replay", "--cassettes", str(tmp_path)])

    captured = capsys.readouterr()
    assert code != 0
    assert "--replay" in captured.err
    assert "Traceback" not in captured.err


def test_a_party_the_formateur_cannot_meet_is_reported(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["run", str(FOUR_PARTY), "--meet", "XX", "--replay"])

    captured = capsys.readouterr()
    assert code != 0
    assert "XX" in captured.err
    assert "FF" in captured.err


def test_the_formateur_may_not_be_sent_to_meet_itself(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["run", str(FOUR_PARTY), "--meet", "NP", "--replay"])

    assert code != 0
    assert "cannot meet itself" in capsys.readouterr().err


def test_a_malformed_mandate_fails_without_a_stack_trace(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    two_party(tmp_path / "invented", positions=positions(environment=6))

    code = main(["run", str(tmp_path / "invented"), "--replay"])

    captured = capsys.readouterr()
    assert code != 0
    assert "AA" in captured.err
    assert "positions.environment" in captured.err
    assert "Traceback" not in captured.err


def test_the_committed_cassettes_replay_a_real_bilateral(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The recorded Run itself, replayed — the check that the Cassettes on disk still fit."""
    if not (CASSETTES / "four-party").is_dir():
        pytest.skip(
            f"no committed Cassettes in {CASSETTES}; record them with "
            "`uv run kbbl run fixtures/four-party`"
        )

    code = main(["run", str(FOUR_PARTY), "--replay", "--cassettes", str(CASSETTES)])

    assert code == 0, capsys.readouterr().err
    assert "Bilateral: NP meets FF" in capsys.readouterr().out


def test_the_module_entry_point_runs_a_scenario(replay: list[str]) -> None:
    finished = subprocess.run(
        [sys.executable, "-m", "kbbl", "run", str(FOUR_PARTY), *replay],
        capture_output=True,
        text=True,
        check=False,
    )

    assert finished.returncode == 0, finished.stderr
    assert "349" in finished.stdout


def test_the_console_script_runs_a_scenario(replay: list[str]) -> None:
    """`uv run kbbl run <scenario>` is the documented interface, so it is the one tested."""
    script = Path(sys.executable).parent / "kbbl"
    if not script.exists():
        pytest.skip("kbbl console script is not installed in this environment")

    finished = subprocess.run(
        [str(script), "run", str(FOUR_PARTY), *replay],
        capture_output=True,
        text=True,
        check=False,
    )

    assert finished.returncode == 0, finished.stderr
    assert "349" in finished.stdout
