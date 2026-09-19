"""The Transcript. Rendered from the run record, so the two can never disagree."""

from __future__ import annotations

from kbbl.models import Bilateral, Choice, Ending, Exchange, Round, Run
from kbbl.output import render_round, render_transcript


def met(*exchanges: Exchange, counterparty: str = "MI") -> Bilateral:
    return Bilateral(formateur="NP", counterparty=counterparty, exchanges=exchanges)


def spent(
    number: int = 1,
    *exchanges: Exchange,
    counterparty: str = "MI",
    reasoning: str = "They are the cheapest abstention in the chamber.",
) -> Round:
    return Round(
        number=number,
        choice=Choice(counterparty=counterparty, reasoning=reasoning),
        bilateral=met(*exchanges, counterparty=counterparty),
    )


def test_every_exchange_appears_in_order_under_the_name_of_who_said_it() -> None:
    transcript = render_round(
        spent(
            1,
            Exchange(speaker="NP", message="Name your price."),
            Exchange(speaker="MI", message="Broadband, funded in full."),
        )
    )

    assert "NP meets MI" in transcript
    assert transcript.index("NP:") < transcript.index("MI:")
    assert "Name your price." in transcript
    assert "Broadband, funded in full." in transcript


def test_a_round_says_which_one_it_is_and_why_the_formateur_spent_it_there() -> None:
    """§5.1: the reasoning was given before the meeting, so it is read before the meeting."""
    transcript = render_round(
        spent(3, Exchange(speaker="NP", message="Name your price."))
    )

    assert "Round 3 of 5 — NP meets MI" in transcript
    assert "Why NP chose MI" in transcript
    assert transcript.index("cheapest abstention") < transcript.index("Name your price.")


def test_the_transcript_says_which_way_the_bilateral_ended() -> None:
    """Agreement, impasse and running out of Exchanges have to be told apart by eye."""
    agreed = render_round(
        spent(1, Exchange(speaker="NP", message="Deal.", declares=Ending.AGREEMENT))
    )
    broke = render_round(
        spent(1, Exchange(speaker="NP", message="No.", declares=Ending.IMPASSE))
    )
    ran_out = render_round(
        spent(1, *[Exchange(speaker="NP", message=f"{index}") for index in range(6)])
    )

    assert "NP agreed" in agreed
    assert "NP declared impasse" in broke
    assert "neither side agreed or declared impasse" in ran_out


def test_a_long_message_is_wrapped_and_keeps_its_paragraphs() -> None:
    message = "word " * 60 + "\n\nAnd a second paragraph."

    transcript = render_round(spent(1, Exchange(speaker="NP", message=message)))

    body = [line for line in transcript.splitlines() if line.startswith("    ")]
    assert len(body) > 1
    assert all(len(line) <= 88 for line in transcript.splitlines())
    assert "    And a second paragraph." in body


def test_a_run_reads_as_five_distinct_private_meetings() -> None:
    """§5.1: five Rounds, each one its own room, in the order they were spent."""
    run = Run(
        scenario="four-party",
        formateur="NP",
        rounds=tuple(
            spent(
                number,
                Exchange(speaker="NP", message=f"Meeting {number}."),
                counterparty=counterparty,
                reasoning=f"Reason {number}.",
            )
            for number, counterparty in enumerate(("MI", "GV", "FF", "MI", "GV"), start=1)
        ),
    )

    transcript = render_transcript(run)

    assert "Run: four-party" in transcript
    assert "Formateur: NP" in transcript
    for number, counterparty in enumerate(("MI", "GV", "FF", "MI", "GV"), start=1):
        assert f"Round {number} of 5 — NP meets {counterparty}" in transcript
        assert f"Meeting {number}." in transcript
        assert f"Reason {number}." in transcript
    assert transcript.index("Round 1 of 5") < transcript.index("Round 5 of 5")
