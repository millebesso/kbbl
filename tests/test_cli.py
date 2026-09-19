"""`kbbl run <scenario>` — loads, prints the chamber, spends five Rounds, exits.

Nothing here calls the model. Most tests record an Attempt against a scripted stand-in and
then replay those Cassettes through the real CLI, which exercises the whole wiring for free;
two replay the committed recordings of an actual Run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from conftest import (
    CASSETTES,
    FOUR_PARTY,
    Model,
    leaks,
    positions,
    recorded_requests,
    spoken,
    two_party,
)
from kbbl.cassettes import Cassettes
from kbbl.cli import main
from kbbl.loop import attempt
from kbbl.models import Run
from kbbl.referee import ROUNDS
from kbbl.scenario import load_scenario

COMMITTED = CASSETTES / "four-party"

NOT_RECORDED = (
    f"no committed Cassettes in {COMMITTED}; record them with "
    "`uv run kbbl run fixtures/four-party`"
)


@pytest.fixture
def replay(tmp_path: Path) -> list[str]:
    """Cassettes for a whole Attempt, recorded off a scripted Agent."""
    scenario = load_scenario(FOUR_PARTY)
    model = Model(
        spoken("Abstain and the broadband money is yours."),
        spoken("Not for that price."),
        spoken("Then we are done here.", "impasse"),
        chooses=["FF", "MI", "GV", "MI", "FF"],
    )
    attempt(
        scenario,
        formateur=scenario.parties[0],
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


def test_run_spends_five_rounds_and_prints_them_as_five_meetings(
    replay: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["run", str(FOUR_PARTY), *replay])

    out = capsys.readouterr().out
    assert code == 0
    assert "Formateur: NP" in out
    for number, counterparty in enumerate(("FF", "MI", "GV", "MI", "FF"), start=1):
        assert f"Round {number} of {ROUNDS} — NP meets {counterparty}" in out
        assert f"Why NP chose {counterparty}" in out
    assert "Abstain and the broadband money is yours." in out
    assert "Ended: NP declared impasse" in out


def test_the_formateur_is_no_longer_pointed_at_a_party_from_the_command_line(
    replay: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """`--meet` stood in for a choice the Formateur now makes for itself."""
    with pytest.raises(SystemExit):
        main(["run", str(FOUR_PARTY), "--meet", "MI", *replay])

    assert "unrecognized arguments: --meet" in capsys.readouterr().err


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


def test_a_scenario_of_one_party_has_nobody_to_meet(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    alone = tmp_path / "alone"
    alone.mkdir()
    (alone / "AA.json").write_text(
        (FOUR_PARTY / "NP.json")
        .read_text(encoding="utf-8")
        .replace('"seats": 140', '"seats": 349')
        .replace('"prefer_not": [\n    "GV"\n  ]', '"prefer_not": []'),
        encoding="utf-8",
    )

    code = main(["run", str(alone), "--replay"])

    captured = capsys.readouterr()
    assert code != 0
    assert "nobody for NP to meet" in captured.err
    assert "Traceback" not in captured.err


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


def test_the_committed_cassettes_replay_a_real_attempt(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The recorded Run itself, replayed — the check that the Cassettes on disk still fit."""
    if not COMMITTED.is_dir():
        pytest.skip(NOT_RECORDED)

    code = main(["run", str(FOUR_PARTY), "--replay", "--cassettes", str(CASSETTES)])

    out = capsys.readouterr()
    assert code == 0, out.err
    assert f"Round {ROUNDS} of {ROUNDS} — NP meets" in out.out


def test_the_recorded_run_shows_no_party_a_bilateral_it_was_not_in() -> None:
    """The asymmetry, audited against the requests a live Run actually sent (§5.1).

    The scripted equivalent lives in `test_loop.py`. This one is over the recording: what
    reached the model, rather than what the stand-in was handed.
    """
    if not COMMITTED.is_dir():
        pytest.skip(NOT_RECORDED)

    scenario = load_scenario(FOUR_PARTY)
    rounds = attempt(
        scenario,
        formateur=scenario.parties[0],
        cassettes=Cassettes(COMMITTED, replay=True),
    )
    run = Run(scenario=scenario.name, formateur=scenario.parties[0].name, rounds=rounds)

    assert leaks(recorded_requests(COMMITTED), run) == []


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
