"""The Transcript. Rendered from the run record, so the two can never disagree."""

from __future__ import annotations

from kbbl.models import Bilateral, Ending, Exchange, Run
from kbbl.output import render_bilateral, render_transcript


def met(*exchanges: Exchange) -> Bilateral:
    return Bilateral(formateur="NP", counterparty="MI", exchanges=exchanges)


def test_every_exchange_appears_in_order_under_the_name_of_who_said_it() -> None:
    transcript = render_bilateral(
        met(
            Exchange(speaker="NP", message="Name your price."),
            Exchange(speaker="MI", message="Broadband, funded in full."),
        )
    )

    assert "Bilateral: NP meets MI" in transcript
    assert transcript.index("NP:") < transcript.index("MI:")
    assert "Name your price." in transcript
    assert "Broadband, funded in full." in transcript


def test_the_transcript_says_which_way_the_bilateral_ended() -> None:
    """Agreement, impasse and running out of Exchanges have to be told apart by eye."""
    agreed = render_bilateral(
        met(Exchange(speaker="NP", message="Deal.", declares=Ending.AGREEMENT))
    )
    broke = render_bilateral(
        met(Exchange(speaker="NP", message="No.", declares=Ending.IMPASSE))
    )
    ran_out = render_bilateral(
        met(*[Exchange(speaker="NP", message=f"{index}") for index in range(6)])
    )

    assert "NP agreed" in agreed
    assert "NP declared impasse" in broke
    assert "neither side agreed or declared impasse" in ran_out


def test_a_long_message_is_wrapped_and_keeps_its_paragraphs() -> None:
    message = "word " * 60 + "\n\nAnd a second paragraph."

    transcript = render_bilateral(met(Exchange(speaker="NP", message=message)))

    body = [line for line in transcript.splitlines() if line.startswith("    ")]
    assert len(body) > 1
    assert all(len(line) <= 88 for line in transcript.splitlines())
    assert "    And a second paragraph." in body


def test_a_run_renders_every_bilateral_it_holds() -> None:
    run = Run(
        scenario="four-party",
        formateur="NP",
        bilaterals=(
            met(Exchange(speaker="NP", message="First meeting.")),
            Bilateral(
                formateur="NP",
                counterparty="GV",
                exchanges=(Exchange(speaker="NP", message="Second meeting."),),
            ),
        ),
    )

    transcript = render_transcript(run)

    assert "Run: four-party" in transcript
    assert "Formateur: NP" in transcript
    assert "First meeting." in transcript
    assert "Second meeting." in transcript
