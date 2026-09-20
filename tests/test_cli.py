"""`kbbl run <scenario>` — loads, prints the chamber, runs one whole Attempt, exits.

Nothing here calls the model. Most tests record an Attempt against a scripted stand-in and
then replay those Cassettes through the real CLI, which exercises the whole wiring for free;
two replay the committed recordings of an actual Run.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from conftest import (
    CASSETTES,
    FOUR_PARTY,
    Model,
    leaks,
    positions,
    recorded_requests,
    spoken,
    stood_down,
    tabled,
    two_party,
)
from kbbl.cassettes import Cassettes
from kbbl.cli import main
from kbbl.loop import attempt
from kbbl.referee import ROUNDS
from kbbl.scenario import load_scenario

COMMITTED = CASSETTES / "four-party"

NOT_RECORDED = (
    f"no committed Cassettes in {COMMITTED}; record them with "
    "`uv run kbbl run fixtures/four-party`"
)


def recorded(tmp_path: Path, model: Model) -> list[str]:
    """Record a whole Attempt off a scripted Agent, and the flags that replay it.

    `--out` is in the flags every test here uses, because a Run writes its artifacts
    wherever it is pointed and the default is a directory in the repo.
    """
    scenario = load_scenario(FOUR_PARTY)
    attempt(
        scenario,
        formateur=scenario.parties[0],
        cassettes=Cassettes(tmp_path / scenario.name, live=model),
    )
    return ["--replay", "--cassettes", str(tmp_path), "--out", str(tmp_path / "out")]


def bargaining(
    tables: dict[str, Any] | None = None, ballots: Sequence[str] = ()
) -> Model:
    """The five Rounds every Attempt here spends, and what this one does with them."""
    return Model(
        spoken("Abstain and the broadband money is yours."),
        spoken("Not for that price."),
        spoken("Then we are done here.", "impasse"),
        chooses=["FF", "MI", "GV", "MI", "FF"],
        tables=tables,
        ballots=ballots,
    )


@pytest.fixture
def replay(tmp_path: Path) -> list[str]:
    """Cassettes for a whole Attempt whose Proposal the chamber lets through."""
    return recorded(
        tmp_path,
        bargaining(
            tabled("NP", "MI", economic=2, law_and_order=3),
            ["Yes", "No", "No", "Yes"],
        ),
    )


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
    """The Transcript is a function of the Cassettes, not of when it was replayed.

    The line naming where the artifacts went is not: every Run gets a directory of its own,
    so replaying twice writes two of them (`test_artifacts.py` is where that is checked).
    """
    main(["run", str(FOUR_PARTY), *replay])
    once = capsys.readouterr().out
    main(["run", str(FOUR_PARTY), *replay])

    assert _without_the_directory(capsys.readouterr().out) == _without_the_directory(once)


def _without_the_directory(out: str) -> str:
    return "\n".join(line for line in out.splitlines() if not line.startswith("Written to "))


def test_a_missing_cassette_explains_itself_without_a_stack_trace(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        [
            "run",
            str(FOUR_PARTY),
            "--replay",
            "--cassettes",
            str(tmp_path),
            "--out",
            str(tmp_path / "out"),
        ]
    )

    captured = capsys.readouterr()
    assert code != 0
    assert "--replay" in captured.err
    assert "Traceback" not in captured.err
    assert not (tmp_path / "out").exists(), "a Run that paid for nothing wrote a directory"


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

    code = main(["run", str(alone), "--replay", "--out", str(tmp_path / "out")])

    captured = capsys.readouterr()
    assert code != 0
    assert "nobody for NP to meet" in captured.err
    assert "Traceback" not in captured.err


def test_a_malformed_mandate_fails_without_a_stack_trace(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    two_party(tmp_path / "invented", positions=positions(environment=6))

    code = main(
        ["run", str(tmp_path / "invented"), "--replay", "--out", str(tmp_path / "out")]
    )

    captured = capsys.readouterr()
    assert code != 0
    assert "AA" in captured.err
    assert "positions.environment" in captured.err
    assert "Traceback" not in captured.err


def test_the_committed_cassettes_replay_a_real_attempt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The recorded Run itself, replayed — the check that the Cassettes on disk still fit."""
    if not COMMITTED.is_dir():
        pytest.skip(NOT_RECORDED)

    code = main(
        [
            "run",
            str(FOUR_PARTY),
            "--replay",
            "--cassettes",
            str(CASSETTES),
            "--out",
            str(tmp_path / "out"),
        ]
    )

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
    run = attempt(
        scenario,
        formateur=scenario.parties[0],
        cassettes=Cassettes(COMMITTED, replay=True),
    )

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


def test_run_prints_the_proposal_the_ballots_and_the_count(
    replay: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """A passed Proposal, end to end through the real command and out of Cassettes."""
    code = main(["run", str(FOUR_PARTY), *replay])

    out = capsys.readouterr().out
    assert code == 0
    assert "The Proposal" in out
    assert "Government:    NP, MI" in out
    assert "economic        +2" in out
    assert "The Vote" in out
    assert "NP votes Yes:" in out
    assert "FF votes No:" in out
    assert "174 seats voted No" in out
    assert "It passes." in out


def test_run_prints_a_defeated_proposal_as_defeated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """175 seats voting No is the only thing that can defeat a Proposal (§5.2)."""
    flags = recorded(tmp_path, bargaining(tabled("NP"), ["Yes", "No", "No", "No"]))

    code = main(["run", str(FOUR_PARTY), *flags])

    out = capsys.readouterr().out
    assert code == 0
    assert "209 seats voted No" in out
    assert "It is defeated." in out
    assert "NP stands down" not in out


def test_run_prints_a_stand_down_as_a_stand_down(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """§5.3: the Attempt ends, the chamber holds no Vote, and the Transcript says so."""
    flags = recorded(tmp_path, bargaining(stood_down("Nobody will pay for a government.")))

    code = main(["run", str(FOUR_PARTY), *flags])

    out = capsys.readouterr().out
    assert code == 0
    assert "NP stands down" in out
    assert "spent none of the four it has" in out
    assert "Nobody will pay for a government." in out
    assert "The Vote" not in out
