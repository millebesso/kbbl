"""One Formateur's whole Attempt. Zero API calls: every model here is a stand-in."""

from __future__ import annotations

from pathlib import Path

from conftest import Model, briefing, leaks, said, spoken, stood_down, tabled, voted
from kbbl.cassettes import Cassettes
from kbbl.loop import attempt
from kbbl.models import Ending, Run, Scenario
from kbbl.referee import ROUNDS, count_vote


def spend(scenario: Scenario, model: Model, tmp_path: Path, replay: bool = False) -> Run:
    """A whole Attempt: its Rounds, what it tabled, and how the chamber answered."""
    return attempt(
        scenario,
        formateur=scenario.parties[0],
        cassettes=Cassettes(tmp_path, replay=replay, live=model),
    )


def test_a_formateur_spends_five_rounds_and_no_more(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§5.3: five Rounds per Attempt, and the budget is the Chamber's to enforce."""
    run = spend(four_party, Model(), tmp_path)

    assert ROUNDS == 5
    assert len(run.rounds) == ROUNDS
    assert [spent.number for spent in run.rounds] == [1, 2, 3, 4, 5]


def test_each_round_records_the_party_chosen_and_the_reasoning_given_for_it(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§7: the record carries the choice, not only the Transcript. Ticket 06 serialises it."""
    run = spend(four_party, Model(chooses=["MI", "FF", "GV", "MI", "FF"]), tmp_path)

    assert [spent.counterparty for spent in run.rounds] == ["MI", "FF", "GV", "MI", "FF"]
    for spent in run.rounds:
        assert spent.choice.counterparty == spent.bilateral.counterparty
        assert spent.choice.reasoning.startswith(f"Round {spent.number}:")


def test_a_party_may_be_met_twice_if_the_formateur_spends_two_rounds_on_it(
    four_party: Scenario, tmp_path: Path
) -> None:
    """There are more Parties than Rounds, so a second meeting is a real thing to buy."""
    run = spend(four_party, Model(chooses=["MI"]), tmp_path)

    assert [spent.counterparty for spent in run.rounds] == ["MI"] * ROUNDS
    assert len({spent.bilateral for spent in run.rounds}) == ROUNDS


def test_the_formateur_carries_earlier_bilaterals_into_later_ones(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§5.1: the Formateur accumulates everything it hears. That accumulation is the game."""
    model = Model(chooses=["FF", "MI"])

    run = spend(four_party, model, tmp_path)

    first, second = run.rounds[0], run.rounds[1]
    opening = next(
        index
        for index, request in enumerate(model.requests)
        if str(request["messages"][-1]["content"]).startswith("You are now in the room with MI")
    )
    carried = "\n".join(str(message["content"]) for message in model.requests[opening]["messages"])
    assert "You are the leader of NP," in model.system(opening)
    for exchange in first.bilateral.exchanges:
        assert exchange.message in carried
    assert "The meeting with FF is over" in carried
    assert second.counterparty == "MI"


def test_the_formateur_is_told_how_the_last_meeting_ended_before_it_chooses_again(
    four_party: Scenario, tmp_path: Path
) -> None:
    model = Model(spoken("There is nothing here for us.", "impasse"), chooses=["GV", "FF"])

    run = spend(four_party, model, tmp_path)

    assert run.rounds[0].bilateral.ending is Ending.IMPASSE
    second_choice = next(
        request
        for request in model.requests
        if any(tool["name"] == "meet" for tool in request["tools"])
        and "ROUND 2" in str(request["messages"][-1]["content"])
    )
    told = "\n".join(str(message["content"]) for message in second_choice["messages"])
    assert "The meeting with GV is over: you declared impasse." in told
    assert "Spent so far: round 1 on GV." in told


def test_no_party_but_the_formateur_sees_a_bilateral_it_was_not_in(
    four_party: Scenario, tmp_path: Path
) -> None:
    """The acceptance criterion §5.1 puts on this ticket, checked over what was actually sent.

    Every Exchange in this Run is different from every other, so a message turning up in the
    wrong conversation is visible rather than indistinguishable. `leaks` reads the requests
    back against the record of who said what, which is a check reading the Transcript cannot
    perform and reading the briefing code cannot either.
    """
    model = Model(chooses=["FF", "MI", "GV", "MI", "FF"])

    run = spend(four_party, model, tmp_path)

    messages = {
        exchange.message
        for spent in run.rounds
        for exchange in spent.bilateral.exchanges
    }
    assert len(messages) == sum(len(spent.bilateral.exchanges) for spent in run.rounds)
    assert leaks(model.requests, run) == []


def test_a_leak_between_bilaterals_is_something_the_audit_can_see(
    four_party: Scenario, tmp_path: Path
) -> None:
    """The audit above is only worth having if it fails when there is something to find."""
    model = Model(chooses=["FF", "MI"])
    run = spend(four_party, model, tmp_path)
    from_another_room = run.rounds[0].bilateral.exchanges[0].message

    tampered = [dict(request) for request in model.requests]
    for request in tampered:
        if "You are the leader of MI," in briefing(request):
            request["messages"] = [
                *request["messages"],
                {"role": "user", "content": from_another_room},
            ]

    assert leaks(tampered, run)


def test_five_rounds_replay_from_cassettes_with_no_live_calls(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§8: iterating on anything downstream of the model costs nothing after the first Run."""
    live = Model(spoken("One."), spoken("Two."), spoken("Three.", "agreement"))
    recorded = spend(four_party, live, tmp_path)

    silent = Model(spoken("this reply is never reached"))
    replayed = spend(four_party, silent, tmp_path, replay=True)

    assert replayed == recorded
    assert silent.requests == []
    assert len(recorded.rounds) == ROUNDS
    assert recorded.rounds[0].bilateral.exchanges[-1].message == said("Three.")


def test_every_conversation_alternates_user_and_assistant_throughout(
    four_party: Scenario, tmp_path: Path
) -> None:
    """The Formateur is told a meeting closed and the next Round opened without speaking in
    between, and the API takes conversations whose roles alternate. Two things said to a
    side before it answers have to arrive as one turn."""
    model = Model(spoken("Nothing doing.", "impasse"), chooses=["FF", "MI", "GV", "MI", "FF"])

    spend(four_party, model, tmp_path)

    for request in model.requests:
        roles = [message["role"] for message in request["messages"]]
        assert roles[0] == "user", roles
        assert roles == ["user" if index % 2 == 0 else "assistant" for index in range(len(roles))]


def test_a_party_met_twice_remembers_its_own_first_meeting(
    four_party: Scenario, tmp_path: Path
) -> None:
    """An earlier Bilateral with the same Formateur is a Party's own, and it keeps it.

    Without this the Formateur walks into Round 4 saying "as we agreed" to a Party holding
    no memory of having agreed anything — one side of the negotiation talking past the other.
    """
    model = Model(chooses=["MI", "FF", "MI"])

    run = spend(four_party, model, tmp_path)

    first, again = run.rounds[0], run.rounds[2]
    assert first.counterparty == again.counterparty == "MI"
    reopened = next(
        request
        for request in model.requests
        if "You are the leader of MI," in briefing(request)
        and any(
            exchange.message in str(message["content"])
            for exchange in again.bilateral.exchanges
            for message in request["messages"]
        )
    )
    told = "\n".join(str(message["content"]) for message in reopened["messages"])
    for exchange in first.bilateral.exchanges:
        assert exchange.message in told
    assert "has asked to see you again" in told
    assert leaks(model.requests, run) == []


def test_a_party_met_twice_still_sees_nothing_of_the_meetings_in_between(
    four_party: Scenario, tmp_path: Path
) -> None:
    """Carrying its own meeting forward must not carry anybody else's with it."""
    model = Model(chooses=["MI", "FF", "GV", "MI", "FF"])

    run = spend(four_party, model, tmp_path)

    said_to_others = {
        exchange.message
        for spent_round in run.rounds
        if spent_round.counterparty != "MI"
        for exchange in spent_round.bilateral.exchanges
    }
    for request in model.requests:
        if "You are the leader of MI," not in briefing(request):
            continue
        told = "\n".join(str(message["content"]) for message in request["messages"])
        assert not [message for message in said_to_others if message in told]


# --- what the Rounds led to ----------------------------------------------------------------


def test_an_attempt_ends_in_a_proposal_the_chamber_votes_on(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§5.3: five Rounds and at most one Proposal. The vote is the end of the Attempt."""
    model = Model(
        tables=tabled("NP", "MI", economic=3, law_and_order=4),
        ballots=["Yes", "No", "No", "Yes"],
    )

    run = spend(four_party, model, tmp_path)

    assert run.proposal is not None
    assert run.stood_down is False
    assert run.proposal.government == ("NP", "MI")
    assert [judgement.party for judgement in run.judgements] == ["NP", "FF", "GV", "MI"]

    vote = count_vote(four_party, run.proposal, run.ballots)
    assert vote.no == 174
    assert vote.passed


def test_a_proposal_is_defeated_when_a_blocking_minority_votes_no(
    four_party: Scenario, tmp_path: Path
) -> None:
    """The only thing that defeats a Proposal is 175 seats voting No (§5.2)."""
    model = Model(tables=tabled("NP"), ballots=["Yes", "No", "No", "No"])

    run = spend(four_party, model, tmp_path)

    assert run.proposal is not None
    vote = count_vote(four_party, run.proposal, run.ballots)
    assert vote.no == 209
    assert not vote.passed


def test_a_formateur_that_stands_down_ends_the_attempt_with_no_vote(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§5.3: Standing down costs the Chamber none of its four Votes, so nobody is polled."""
    model = Model(tables=stood_down("There is nothing here anyone will vote for."))

    run = spend(four_party, model, tmp_path)

    assert run.stood_down
    assert run.proposal is None
    assert run.judgements == ()
    assert len(run.rounds) == ROUNDS
    assert not [
        request
        for request in model.requests
        if any(tool["name"] == "ballot" for tool in request["tools"])
    ]


def test_a_whole_attempt_replays_from_cassettes_with_no_live_calls(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§8: the Proposal and every Ballot replay too, or the free path stops at the Rounds."""
    live = Model(tables=tabled("NP", "GV", environment=2), ballots=["Yes", "No", "Yes", "Abstain"])
    recorded = spend(four_party, live, tmp_path)

    silent = Model()
    replayed = spend(four_party, silent, tmp_path, replay=True)

    assert replayed == recorded
    assert silent.requests == []
    assert recorded.proposal is not None
    assert [judgement.ballot.value for judgement in recorded.judgements] == [
        "Yes",
        "No",
        "Yes",
        "Abstain",
    ]


def test_a_stand_down_replays_from_cassettes_with_no_live_calls(
    four_party: Scenario, tmp_path: Path
) -> None:
    live = Model(tables=stood_down("Nobody will pay for a government."))
    recorded = spend(four_party, live, tmp_path)

    silent = Model()
    replayed = spend(four_party, silent, tmp_path, replay=True)

    assert replayed == recorded
    assert silent.requests == []
    assert replayed.stood_down


def test_no_party_sees_another_partys_ballot_or_the_room_it_was_cast_in(
    four_party: Scenario, tmp_path: Path
) -> None:
    """The asymmetry does not lapse because the bargaining is over (§5.1).

    Every Party judges the Proposal in its own room, so what it says casting a Ballot is its
    own. The audit is over what was actually sent, the same way the Rounds are audited.
    """
    model = Model(
        chooses=["FF", "MI", "GV", "MI", "FF"],
        tables=tabled("NP", "MI"),
        ballots=[
            voted("Yes", "It is our platform, near enough."),
            voted("No", "Economic at 0 is not what we were promised."),
            voted("Abstain", "Not worth an election over."),
            voted("Yes", "The broadband money is in it."),
        ],
    )

    run = spend(four_party, model, tmp_path)

    assert len({judgement.reasoning for judgement in run.judgements}) == len(run.judgements)
    assert leaks(model.requests, run) == []


def test_every_conversation_still_alternates_once_the_vote_is_added(
    four_party: Scenario, tmp_path: Path
) -> None:
    """A Party hears its meeting close and the chamber vote open without speaking between."""
    model = Model(spoken("Nothing doing.", "impasse"), chooses=["FF", "MI", "GV", "MI", "FF"])

    spend(four_party, model, tmp_path)

    for request in model.requests:
        roles = [message["role"] for message in request["messages"]]
        assert roles == ["user" if index % 2 == 0 else "assistant" for index in range(len(roles))]


def test_the_record_carries_what_the_formateur_said_ending_its_attempt(
    four_party: Scenario, tmp_path: Path
) -> None:
    """A Stand down leaves no Proposal behind, so the prose is the whole account of it."""
    tabled_it = spend(
        four_party, Model(tables=tabled("NP", reasoning="NP governs alone.")), tmp_path
    )
    stood = spend(four_party, Model(tables=stood_down("FF will not move on economic.")), tmp_path)

    assert tabled_it.reasoning == "NP governs alone."
    assert stood.reasoning == "FF will not move on economic."
