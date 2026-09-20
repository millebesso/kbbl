"""The Transcript. Rendered from the run record, so the two can never disagree."""

from __future__ import annotations

from conftest import platform
from kbbl.models import (
    Ballot,
    Bilateral,
    Choice,
    Ending,
    Exchange,
    Judgement,
    Proposal,
    Round,
    Run,
    Scenario,
)
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


def test_a_run_reads_as_five_distinct_private_meetings(four_party: Scenario) -> None:
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

    transcript = render_transcript(four_party, run)

    assert "Run: four-party" in transcript
    assert "Formateur: NP" in transcript
    for number, counterparty in enumerate(("MI", "GV", "FF", "MI", "GV"), start=1):
        assert f"Round {number} of 5 — NP meets {counterparty}" in transcript
        assert f"Meeting {number}." in transcript
        assert f"Reason {number}." in transcript
    assert transcript.index("Round 1 of 5") < transcript.index("Round 5 of 5")


# --- how an Attempt ends -------------------------------------------------------------------


def attempted(
    four_party: Scenario,
    proposal: Proposal | None,
    *judgements: Judgement,
    reasoning: str = "This is where the five rounds left us.",
) -> str:
    """A one-Round Run that ends the way this test is about."""
    return render_transcript(
        four_party,
        Run(
            scenario=four_party.name,
            formateur="NP",
            rounds=(spent(1, Exchange(speaker="NP", message="Name your price.")),),
            proposal=proposal,
            reasoning=reasoning,
            judgements=judgements,
        ),
    )


def governing(*government: str, support_only: tuple[str, ...] = (), **axes: int) -> Proposal:
    return Proposal(
        formateur="NP",
        platform=platform(**axes),
        government=government,
        support_only=support_only,
    )


def test_the_transcript_shows_the_proposal_that_was_tabled(four_party: Scenario) -> None:
    transcript = attempted(
        four_party,
        Proposal(
            formateur="NP",
            platform=platform(economic=3, environment=-2),
            government=("NP", "MI"),
            support_only=("GV",),
            commitments=("a binding cap on public spending growth",),
        ),
        Judgement(party="NP", ballot=Ballot.YES, reasoning="Ours."),
        Judgement(party="FF", ballot=Ballot.NO, reasoning="Not at economic +3."),
        Judgement(party="GV", ballot=Ballot.YES, reasoning="We hold our nose."),
        Judgement(party="MI", ballot=Ballot.YES, reasoning="The broadband money is in it."),
    )

    assert "The Proposal" in transcript
    assert transcript.index("This is where the five rounds left us.") < transcript.index(
        "NP's Proposal."
    )
    assert "economic        +3" in transcript
    assert "Government:    NP, MI" in transcript
    assert "Support-only:  GV" in transcript
    assert "a binding cap on public spending growth" in transcript


def test_every_ballot_is_printed_with_the_reasoning_it_was_cast_in(
    four_party: Scenario,
) -> None:
    """§8: a full Run is read closely, and a Ballot without its sentence cannot be read."""
    transcript = attempted(
        four_party,
        governing("NP"),
        Judgement(party="NP", ballot=Ballot.YES, reasoning="Ours."),
        Judgement(party="FF", ballot=Ballot.NO, reasoning="Not at economic +3."),
        Judgement(party="GV", ballot=Ballot.ABSTAIN, reasoning="Not worth an election."),
        Judgement(party="MI", ballot=Ballot.NO, reasoning="Nothing in it for us."),
    )

    assert "NP votes Yes:" in transcript
    assert "FF votes No:" in transcript
    assert "GV votes Abstain:" in transcript
    assert "Not worth an election." in transcript
    assert transcript.index("NP votes Yes:") < transcript.index("MI votes No:")


def test_the_transcript_counts_the_vote_and_says_which_way_it_went(
    four_party: Scenario,
) -> None:
    """The count is the Referee's, and the Transcript reports the one it computed (§2)."""
    defeated = attempted(
        four_party,
        governing("NP"),
        Judgement(party="NP", ballot=Ballot.YES, reasoning="Ours."),
        Judgement(party="FF", ballot=Ballot.NO, reasoning="No."),
        Judgement(party="GV", ballot=Ballot.NO, reasoning="No."),
        Judgement(party="MI", ballot=Ballot.NO, reasoning="No."),
    )
    passed = attempted(
        four_party,
        governing("NP"),
        Judgement(party="NP", ballot=Ballot.YES, reasoning="Ours."),
        Judgement(party="FF", ballot=Ballot.NO, reasoning="No."),
        Judgement(party="GV", ballot=Ballot.NO, reasoning="No."),
        Judgement(party="MI", ballot=Ballot.ABSTAIN, reasoning="We stay out of the way."),
    )

    assert "209 seats voted No" in defeated
    assert "It is defeated." in defeated
    assert "174 seats voted No" in passed
    assert "It passes." in passed


def test_a_stand_down_reads_differently_from_a_proposal_voted_down(
    four_party: Scenario,
) -> None:
    """§5.3: both end an Attempt, and only one of them spends a Chamber Vote."""
    stood = attempted(four_party, None)
    defeated = attempted(
        four_party,
        governing("NP"),
        Judgement(party="NP", ballot=Ballot.YES, reasoning="Ours."),
        Judgement(party="FF", ballot=Ballot.NO, reasoning="No."),
        Judgement(party="GV", ballot=Ballot.NO, reasoning="No."),
        Judgement(party="MI", ballot=Ballot.NO, reasoning="No."),
    )

    assert "NP stands down" in stood
    assert "This is where the five rounds left us." in stood
    assert "tabled no Proposal" in stood
    assert "spent none of the four it has" in stood
    assert "The Vote" not in stood
    assert "votes" not in stood

    assert "NP stands down" not in defeated
    assert "The Vote" in defeated
    assert "It is defeated." in defeated


def test_a_round_nobody_explained_says_so_rather_than_printing_a_blank(
    four_party: Scenario,
) -> None:
    """An Agent may give the call and no sentence. A silent gap reads as a rendering bug."""
    transcript = render_round(
        spent(1, Exchange(speaker="NP", message="Name your price."), reasoning="")
    )

    assert "Why NP chose MI" in transcript
    assert "(Nothing said.)" in transcript
