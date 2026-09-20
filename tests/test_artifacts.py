"""What a Run leaves behind: `transcript.md`, `run.json` and `result.json` (§7).

Nothing here calls the model. An Attempt is recorded against a scripted stand-in and then
replayed through the real command, so every test runs the whole wiring for free.

The bar §7 sets on `run.json` is that aggregating a batch of Runs later be a loop and a
`Counter` rather than a re-instrumentation, and that is the one claim a reading of the code
cannot check. So it is checked the only way it can be: by writing a batch of Runs and
counting them, using nothing but the artifacts.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from conftest import (
    FOUR_PARTY,
    Model,
    platform,
    responded,
    spoken,
    stood_down,
    tabled,
    voted,
)
from kbbl.agents import AgentError
from kbbl.cassettes import Cassettes
from kbbl.cli import main
from kbbl.ledger import Ledger
from kbbl.loop import attempt
from kbbl.models import (
    Axis,
    Ballot,
    Choice,
    Exchange,
    Judgement,
    Proposal,
    Scenario,
    Usage,
)
from kbbl.output import RECORD, RESULT, TRANSCRIPT, render_transcript, write_run
from kbbl.referee import ROUNDS
from kbbl.scenario import load_scenario

STAMPED = re.compile(r"^run-\d{8}-\d{6}(-\d+)?$")
"""`run-<timestamp>/`, with a suffix only when a second Run landed in the same second."""


def bargaining(**scripted: Any) -> Model:
    """Five Rounds of a negotiation that goes nowhere, and whatever this Run does with them."""
    return Model(
        spoken("Abstain and the broadband money is yours."),
        spoken("Not for that price."),
        spoken("Then we are done here.", "impasse"),
        chooses=["FF", "MI", "GV", "MI", "FF"],
        **scripted,
    )


def played(tmp_path: Path, model: Model, out: Path, drawer: str = "cassettes") -> int:
    """Record an Attempt off the stand-in, then replay it through the real command.

    Each Run gets a Cassette drawer of its own: two Runs scripted differently answer the
    same request two ways, and one drawer cannot hold both.

    An Attempt that breaks while recording is recorded up to the point it broke, which is
    what the replay is then asked to reproduce. The exit code every test reads is the
    command's, not this pass's.
    """
    recorded = tmp_path / drawer
    scenario = load_scenario(FOUR_PARTY)
    try:
        attempt(
            scenario,
            formateur=scenario.parties[0],
            cassettes=Cassettes(recorded / scenario.name, live=model),
        )
    except AgentError:
        pass
    return main(
        [
            "run",
            str(FOUR_PARTY),
            "--replay",
            "--cassettes",
            str(recorded),
            "--out",
            str(out),
        ]
    )


def written(out: Path) -> Path:
    """The one directory a Run wrote, and proof that it wrote exactly one."""
    made = sorted(path for path in out.iterdir() if path.is_dir())
    assert len(made) == 1, made
    return made[0]


def read(directory: Path, name: str) -> Any:
    return json.loads((directory / name).read_text(encoding="utf-8"))


@pytest.fixture
def out(tmp_path: Path) -> Path:
    return tmp_path / "out"


@pytest.fixture
def formed(tmp_path: Path, out: Path) -> Path:
    """A Run whose Proposal the chamber lets through: 174 seats vote No, and 175 defeats."""
    assert played(
        tmp_path,
        bargaining(
            tables=tabled("NP", "MI", economic=2, law_and_order=3),
            ballots=["Yes", "No", "No", "Yes"],
        ),
        out,
    ) == 0
    return written(out)


# --- the three files -----------------------------------------------------------------------


def test_a_run_writes_a_transcript_a_record_and_a_result(formed: Path) -> None:
    """§7: one timestamped directory per Run, holding all three."""
    assert STAMPED.match(formed.name), formed.name
    assert sorted(path.name for path in formed.iterdir()) == [RESULT, RECORD, TRANSCRIPT]


def test_the_transcript_reads_start_to_finish(formed: Path) -> None:
    """Every Bilateral, the Proposal, the Vote — the same Transcript the command prints."""
    transcript = (formed / TRANSCRIPT).read_text(encoding="utf-8")

    assert "Formateur: NP" in transcript
    for number, counterparty in enumerate(("FF", "MI", "GV", "MI", "FF"), start=1):
        assert f"Round {number} of {ROUNDS} — NP meets {counterparty}" in transcript
        assert f"Why NP chose {counterparty}" in transcript
    assert "Abstain and the broadband money is yours." in transcript
    assert "Ended: NP declared impasse" in transcript
    assert "The Proposal" in transcript
    assert "Government:    NP, MI" in transcript
    assert "The Vote" in transcript
    assert "174 seats voted No" in transcript
    assert "It passes." in transcript
    assert transcript.endswith("\n")


def test_out_controls_where_the_artifacts_go(tmp_path: Path) -> None:
    """§11.5: `--out` and nowhere else. The default is a directory in the repo."""
    elsewhere = tmp_path / "somewhere" / "deeper"

    assert played(tmp_path, bargaining(tables=stood_down()), elsewhere) == 0

    assert (written(elsewhere) / RECORD).is_file()
    assert not (tmp_path / "out").exists()


def test_a_second_run_never_writes_over_the_first(tmp_path: Path, out: Path) -> None:
    """Two Runs a fraction of a second apart still cost a dollar and a half each (§6)."""
    assert played(tmp_path, bargaining(tables=stood_down()), out, "once") == 0
    assert played(tmp_path, bargaining(tables=stood_down("Enough.")), out, "twice") == 0

    made = sorted(path for path in out.iterdir() if path.is_dir())
    assert len(made) == 2
    assert all(STAMPED.match(path.name) for path in made), made
    assert "Enough." in (made[1] / TRANSCRIPT).read_text(encoding="utf-8")


# --- what the record carries -----------------------------------------------------------------


def test_the_record_carries_every_exchange_under_the_name_of_who_said_it(
    formed: Path,
) -> None:
    record = read(formed, RECORD)

    rounds = record["run"]["rounds"]
    assert [spent["number"] for spent in rounds] == [1, 2, 3, 4, 5]
    assert [spent["bilateral"]["counterparty"] for spent in rounds] == [
        "FF",
        "MI",
        "GV",
        "MI",
        "FF",
    ]
    spoken_in_first = rounds[0]["bilateral"]["exchanges"]
    assert [exchange["speaker"] for exchange in spoken_in_first] == ["NP", "FF", "NP"]
    assert "Abstain and the broadband money is yours." in spoken_in_first[0]["message"]
    assert spoken_in_first[-1]["declares"] == "impasse"


def test_the_record_says_which_party_the_formateur_chose_each_round_and_why(
    formed: Path,
) -> None:
    """The reasoning was given before the meeting, and the record keeps it that way."""
    rounds = read(formed, RECORD)["run"]["rounds"]

    for spent in rounds:
        assert spent["choice"]["counterparty"] == spent["bilateral"]["counterparty"]
        assert spent["choice"]["reasoning"].startswith(f"Round {spent['number']}:")


def test_the_record_carries_the_proposal_that_was_tabled(formed: Path) -> None:
    proposal = read(formed, RECORD)["run"]["proposal"]

    assert proposal["formateur"] == "NP"
    assert proposal["government"] == ["NP", "MI"]
    assert proposal["support_only"] == []
    assert proposal["platform"]["economic"] == 2
    assert proposal["platform"]["law_and_order"] == 3
    assert set(proposal["platform"]) == {axis.value for axis in Axis}


def test_the_record_carries_every_ballot_with_the_reasoning_it_was_cast_in(
    tmp_path: Path, out: Path
) -> None:
    """§8: Ballots are read closely. A Ballot without its sentence cannot be read."""
    assert played(
        tmp_path,
        bargaining(
            tables=tabled("NP", "MI"),
            ballots=[
                voted("Yes", "It is our platform, near enough."),
                voted("No", "Economic at 0 is not what we were promised."),
                voted("Abstain", "Not worth an election over."),
                voted("Yes", "The broadband money is in it."),
            ],
        ),
        out,
    ) == 0

    judgements = read(written(out), RECORD)["run"]["judgements"]
    assert [judgement["party"] for judgement in judgements] == ["NP", "FF", "GV", "MI"]
    assert [judgement["ballot"] for judgement in judgements] == [
        "Yes",
        "No",
        "Abstain",
        "Yes",
    ]
    assert judgements[1]["reasoning"] == "Economic at 0 is not what we were promised."


def test_the_record_carries_every_gap_report_that_was_shown(formed: Path) -> None:
    """§5.4 is the only defence against a mushy grand coalition, so it is what a batch of
    Runs gets read for — and it cannot be, unless the reports survive the Run."""
    reports = read(formed, RECORD)["run"]["gap_reports"]

    assert [report["party"] for report in reports] == ["NP", "FF", "GV", "MI"]
    for report in reports:
        assert [gap["axis"] for gap in report["gaps"]] == [axis.value for axis in Axis]
        assert report["worst_gap"] == max(gap["gap"] for gap in report["gaps"])
        assert report["mean_gap"] == sum(gap["gap"] for gap in report["gaps"]) / len(
            report["gaps"]
        )

    # GV's own Positions against the Platform that was tabled: economic +2, the rest at 0.
    gv = next(report for report in reports if report["party"] == "GV")
    economic = next(gap for gap in gv["gaps"] if gap["axis"] == "economic")
    assert economic["platform"] == 2
    assert economic["position"] == load_scenario(FOUR_PARTY).party("GV").positions.economic
    assert economic["gap"] == abs(economic["position"] - economic["platform"])


def test_the_record_carries_token_and_cache_usage_and_a_cassette_key_per_request(
    formed: Path,
) -> None:
    """§7 asks for aggregation to be a `Counter`, and cost is the first thing counted.

    The Cassette key is the handle on what was actually sent: no artifact repeats a Persona
    in full, and the request behind the key holds every word the Agent was shown.
    """
    record = read(formed, RECORD)

    spoken_in_all = sum(
        len(spent["bilateral"]["exchanges"]) for spent in record["run"]["rounds"]
    )
    asked = (
        ROUNDS  # one Choice per Round
        + spoken_in_all  # one request per Exchange, whoever spoke it
        + 1  # the tabling
        + len(record["run"]["judgements"])  # one Ballot per Party
    )

    usage = record["run"]["usage"]
    assert len(usage) == asked
    assert {entry["party"] for entry in usage} == {"NP", "FF", "GV", "MI"}
    assert all(re.fullmatch(r"[0-9a-f]{64}", entry["cassette"]) for entry in usage)
    assert all(
        {"input_tokens", "output_tokens", "cache_write_tokens", "cache_read_tokens"}
        <= set(entry)
        for entry in usage
    )


def test_the_record_stands_alone_without_the_scenario_beside_it(formed: Path) -> None:
    """§7: an aggregation that had to re-load a Scenario to read a Run is the
    re-instrumentation this file exists to prevent."""
    record = read(formed, RECORD)

    assert record["scenario"] == "four-party"
    assert record["chamber"] == {"NP": 140, "FF": 132, "GV": 42, "MI": 35}
    assert sum(record["chamber"].values()) == 349
    assert record["count"] == {
        "yes": 175,
        "abstain": 0,
        "no": 174,
        "base_seats": 175,
        "passed": True,
    }
    assert record["outcome"] == "formed"


# --- the result ------------------------------------------------------------------------------


def test_the_result_carries_the_outcome_and_a_timestamp(formed: Path) -> None:
    """§9: KBBL predicts an open question, so comparing it later is a lookup and a date."""
    before = datetime.now(UTC)
    result = read(formed, RESULT)

    assert result["outcome"] == "formed"
    assert result["scenario"] == "four-party"
    assert result["formateur"] == "NP"
    assert result["government"] == ["NP", "MI"]
    assert result["count"]["no"] == 174
    assert datetime.fromisoformat(result["at"]) <= before


def test_a_defeated_proposal_is_rejected_and_a_stand_down_is_neither(
    tmp_path: Path, out: Path
) -> None:
    """§5.3: both end an Attempt, and only one of them spends a Chamber Vote."""
    assert played(
        tmp_path,
        bargaining(tables=tabled("NP"), ballots=["Yes", "No", "No", "No"]),
        out / "voted",
    ) == 0
    assert played(
        tmp_path,
        bargaining(tables=stood_down("Nobody will pay for a government.")),
        out / "conceded",
        "second",
    ) == 0

    rejected = read(written(out / "voted"), RESULT)
    stood = read(written(out / "conceded"), RESULT)

    assert rejected["outcome"] == "rejected"
    assert rejected["count"]["no"] == 209
    assert rejected["count"]["passed"] is False

    assert stood["outcome"] == "stood down"
    assert stood["government"] == []
    assert stood["count"] is None


# --- what a batch of Runs is for ---------------------------------------------------------------


def test_counting_outcomes_across_runs_is_a_loop_and_a_counter(
    tmp_path: Path, out: Path
) -> None:
    """The acceptance criterion §7 puts on this ticket, demonstrated rather than asserted.

    Four Runs, three outcomes, and the aggregation below is the whole of it: open each
    `run.json`, read one key, count. No Scenario is loaded, no Vote is re-counted and no
    Transcript is parsed — which is what "not a re-instrumentation" has to mean if it means
    anything.
    """
    batch = {
        "formed": bargaining(
            tables=tabled("NP", "MI"), ballots=["Yes", "No", "No", "Yes"]
        ),
        "formed-again": bargaining(tables=tabled("NP"), ballots=["Yes", "No", "No", "Abstain"]),
        "rejected": bargaining(tables=tabled("NP"), ballots=["Yes", "No", "No", "No"]),
        "stood-down": bargaining(tables=stood_down()),
    }
    for name, model in batch.items():
        assert played(tmp_path, model, out, name) == 0

    counted = Counter(
        json.loads(path.read_text(encoding="utf-8"))["outcome"]
        for path in sorted(out.glob(f"run-*/{RECORD}"))
    )

    assert counted == Counter({"formed": 2, "rejected": 1, "stood down": 1})
    assert sum(counted.values()) == len(batch)


def test_the_artifacts_are_identical_under_replay(tmp_path: Path, out: Path) -> None:
    """The Run that called the model, and the same Run replayed off its Cassettes.

    Everything but the timestamp, which is the one thing a replay is honestly entitled to
    write differently (§9) — and the reason it is in `result.json` alone rather than in the
    record beside it.
    """
    model = bargaining(tables=tabled("NP", "MI"), ballots=["Yes", "No", "No", "Yes"])
    recorded = tmp_path / "cassettes"
    scenario = load_scenario(FOUR_PARTY)
    ledger = Ledger(scenario=scenario.name, formateur=scenario.parties[0].name)
    attempt(
        scenario,
        formateur=scenario.parties[0],
        cassettes=Cassettes(recorded / scenario.name, live=model),
        ledger=ledger,
    )
    live = write_run(out, scenario, ledger.run)

    assert (
        main(
            [
                "run",
                str(FOUR_PARTY),
                "--replay",
                "--cassettes",
                str(recorded),
                "--out",
                str(out),
            ]
        )
        == 0
    )

    replayed = next(path for path in sorted(out.iterdir()) if path.is_dir() and path != live)
    assert (live / TRANSCRIPT).read_bytes() == (replayed / TRANSCRIPT).read_bytes()
    assert (live / RECORD).read_bytes() == (replayed / RECORD).read_bytes()

    first, second = read(live, RESULT), read(replayed, RESULT)
    assert first.pop("at") != second.pop("at")
    assert first == second


# --- a Run that stops rather than finishing ------------------------------------------------


def test_a_run_that_breaks_mid_bilateral_keeps_every_exchange_it_paid_for(
    tmp_path: Path,
) -> None:
    """Ticket 02's debt: an Exchange that has been billed is an Exchange that is kept.

    The record is written as the Run happens rather than assembled at the end, so an Agent
    returning a stub in the third Exchange loses that Exchange and nothing before it.
    """
    broken = Model(
        spoken("Abstain and the broadband money is yours."),
        spoken("Not for that price."),
        responded("tiny"),
        chooses=["FF"],
    )
    recorded = tmp_path / "cassettes"
    scenario = load_scenario(FOUR_PARTY)
    ledger = Ledger(scenario=scenario.name, formateur="NP")
    with pytest.raises(AgentError, match="fragment"):
        attempt(
            scenario,
            formateur=scenario.parties[0],
            cassettes=Cassettes(recorded / scenario.name, live=broken),
            ledger=ledger,
        )

    kept = ledger.run
    assert kept.finished is False
    assert kept.stood_down is False
    assert len(kept.rounds) == 1
    assert kept.rounds[0].counterparty == "FF"
    assert [exchange.speaker for exchange in kept.rounds[0].bilateral.exchanges] == [
        "NP",
        "FF",
    ]
    assert len(kept.usage) == 4, "the failed request was paid for too"


def test_a_run_that_breaks_still_writes_its_artifacts(
    tmp_path: Path, out: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The command exits non-zero and says why, and the Exchanges are on disk all the same."""
    broken = Model(
        spoken("Abstain and the broadband money is yours."),
        spoken("Not for that price."),
        responded("tiny"),
        chooses=["FF"],
    )

    code = played(tmp_path, broken, out)

    captured = capsys.readouterr()
    assert code != 0
    assert "fragment" in captured.err
    assert "Traceback" not in captured.err

    record = read(written(out), RECORD)
    assert record["outcome"] == "unfinished"
    assert record["count"] is None
    assert record["run"]["finished"] is False
    assert len(record["run"]["rounds"]) == 1
    assert read(written(out), RESULT)["outcome"] == "unfinished"
    assert "NP's Attempt stopped" in (written(out) / TRANSCRIPT).read_text(encoding="utf-8")


def test_a_run_that_stops_in_the_vote_still_shows_what_it_tabled(
    four_party: Scenario, tmp_path: Path
) -> None:
    """The Transcript and the record cannot disagree about what a Run reached.

    A Run that breaks between tabling and the end of the Vote holds a Proposal and some of
    the Ballots on it. `run.json` carries both, so a Transcript saying nothing was tabled
    would be the one place a reader is told something the record contradicts.
    """
    ledger = Ledger(scenario=four_party.name, formateur="NP")
    ledger.chose(Choice(counterparty="MI", reasoning="MI is the cheapest abstention."))
    ledger.said(Exchange(speaker="NP", message="Name your price, and be brief about it."))
    ledger.tabled(
        Proposal(
            formateur="NP",
            platform=platform(economic=2),
            government=("NP", "MI"),
        ),
        "This is the government the chamber can live with.",
    )
    ledger.judged(Judgement(party="NP", ballot=Ballot.YES, reasoning="Ours."))

    stopped = ledger.run
    transcript = render_transcript(four_party, stopped)

    assert "The Proposal" in transcript
    assert "Government:    NP, MI" in transcript
    assert "NP votes Yes:" in transcript
    assert "NP's Attempt stopped" in transcript
    assert "1 Party had cast a Ballot and the Vote was never counted." in transcript
    assert "no Proposal was tabled" not in transcript
    assert "stands down" not in transcript

    # And the record the Transcript is rendered from says the same.
    written = write_run(tmp_path / "out", four_party, stopped)
    recorded = read(written, RECORD)
    assert recorded["outcome"] == "unfinished"
    assert recorded["run"]["proposal"]["government"] == ["NP", "MI"]
    assert len(recorded["run"]["judgements"]) == 1
    assert recorded["count"] is None


def test_a_dropped_round_does_not_renumber_the_rounds_after_it(
    four_party: Scenario,
) -> None:
    """A Round is numbered by when it was spent, not by its place in the list.

    A Round whose meeting produced no Exchange is not kept, and numbering the survivors
    1..n would relabel the Round after it — a record describing a meeting that never
    happened.
    """
    ledger = Ledger(scenario=four_party.name, formateur="NP")
    ledger.chose(Choice(counterparty="FF", reasoning="First."))
    ledger.said(Exchange(speaker="NP", message="The first meeting, and what we want of it."))
    ledger.chose(Choice(counterparty="GV", reasoning="Second, and nobody spoke."))
    ledger.chose(Choice(counterparty="MI", reasoning="Third."))
    ledger.said(Exchange(speaker="NP", message="The third meeting, and what we want of it."))
    ledger.finish()

    kept = ledger.run
    assert [spent.number for spent in kept.rounds] == [1, 3]
    assert [spent.counterparty for spent in kept.rounds] == ["FF", "MI"]


# --- the Ledger itself ---------------------------------------------------------------------


def test_two_meetings_with_the_same_party_stay_two_meetings() -> None:
    """A Formateur may spend two Rounds on one Party (§5.1), and they are two Bilaterals.

    The Ledger reuses an open Round only while it is still empty. Running the second
    meeting's Exchanges into the first one's list would give the record one meeting of six
    where the Run held two of three — and the Transcript would read as a conversation that
    never happened.
    """
    ledger = Ledger(scenario="four-party", formateur="NP")
    for meeting in ("first", "second"):
        ledger.met("MI")
        ledger.said(
            Exchange(speaker="NP", message=f"This is the {meeting} meeting, and here is why.")
        )
    ledger.finish()

    kept = ledger.run
    assert [spent.number for spent in kept.rounds] == [1, 2]
    assert [spent.counterparty for spent in kept.rounds] == ["MI", "MI"]
    assert all(len(spent.bilateral.exchanges) == 1 for spent in kept.rounds)


def test_a_round_nobody_spoke_in_is_not_a_round() -> None:
    """A Bilateral is a meeting, and a meeting with no Exchange in it is not one.

    What the Choice cost is still in `usage`, where the cost of a request belongs whether or
    not it produced a message — and the Cassette key there leads back to what was said.
    """
    ledger = Ledger(scenario="four-party", formateur="NP")
    ledger.chose(Choice(counterparty="MI", reasoning="MI is the cheapest abstention."))
    ledger.paid(Usage(party="NP", cassette="0" * 64, input_tokens=500, output_tokens=40))

    kept = ledger.run
    assert kept.rounds == ()
    assert len(kept.usage) == 1
    assert kept.finished is False


def test_a_run_that_stopped_does_not_read_as_a_stand_down(
    tmp_path: Path, out: Path
) -> None:
    """Both hold no Proposal, and only one of them is a decision somebody made (§5.3)."""
    broken = Model(responded("tiny"), chooses=["FF"])

    assert played(tmp_path, broken, out) != 0

    transcript = (written(out) / TRANSCRIPT).read_text(encoding="utf-8")
    assert "stands down" not in transcript
    assert "did not reach an end of its own" in transcript
