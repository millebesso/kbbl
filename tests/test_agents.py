"""Persona construction and the Bilateral. Zero API calls: every model here is a stand-in."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from conftest import (
    Model,
    briefing,
    chose,
    mandate,
    platform,
    positions,
    responded,
    said,
    spoken,
    stood_down,
    tabled,
    voted,
    write_scenario,
)
from kbbl.agents import BALLOT, MODEL, AgentError, FormateurAgent, persona
from kbbl.cassettes import Cassettes
from kbbl.loop import attempt
from kbbl.models import (
    Axis,
    Ballot,
    Bilateral,
    Choice,
    Ending,
    Judgement,
    Proposal,
    Scenario,
)
from kbbl.referee import (
    ROUNDS,
    Price,
    exclusion_report,
    gap_report,
    price_report,
    render_exclusion_report,
    render_gap_report,
    render_price_report,
)
from kbbl.scenario import load_scenario


def hold_bilateral(
    scenario: Scenario, model: Model, tmp_path: Path, replay: bool = False
) -> Bilateral:
    """One meeting, held directly: the Formateur is not asked to choose whom it is with."""
    return FormateurAgent(scenario, scenario.parties[0]).meet(
        scenario.parties[1], Cassettes(tmp_path, replay=replay, live=model)
    )


def make_choice(scenario: Scenario, model: Model, tmp_path: Path) -> Choice:
    """The first Round's Choice, without holding the Bilateral it books."""
    return FormateurAgent(scenario, scenario.parties[0]).spend(
        Cassettes(tmp_path, live=model)
    ).choice


# --- the persona is built from the mandate ---------------------------------------------


def test_every_axis_reaches_the_agent_with_its_value_and_what_the_poles_mean(
    four_party: Scenario,
) -> None:
    """A bare `economic: +5` says nothing; the poles have to travel with the number."""
    brief = persona(four_party, four_party.party("NP"))

    assert "free market, low tax" in brief
    assert "climate before growth" in brief
    for axis in ("economic", "environment", "military", "transport", "international"):
        assert axis in brief


def test_both_price_lists_reach_the_agent_and_are_kept_apart(four_party: Scenario) -> None:
    brief = persona(four_party, four_party.party("NP"))

    assert "a binding cap on public spending growth" in brief
    governing, supporting = brief.split("back a government from outside")
    assert "law_and_order" in governing
    assert "law_and_order" not in supporting


def test_willingness_to_re_elect_reaches_the_agent_as_a_disposition_not_a_number(
    tmp_path: Path,
) -> None:
    """§3: persona only. The Referee never reads it and the Agent may lie about it."""
    scenario = load_scenario(
        write_scenario(
            tmp_path,
            mandate("AA", 200, willingness_to_re_elect=0),
            mandate("BB", 149, willingness_to_re_elect=10),
        )
    )

    desperate = persona(scenario, scenario.party("AA"))
    relaxed = persona(scenario, scenario.party("BB"))

    assert desperate != relaxed
    for brief, value in ((desperate, 0), (relaxed, 10)):
        assert "willingness" not in brief.lower()
        assert f"{value}/10" not in brief
        assert "conceal" in brief


def test_the_fixture_sends_four_parties_four_different_dispositions(
    four_party: Scenario,
) -> None:
    """02 §12.1: NP and FF shared a band, so the lever this ticket leans on distinguished
    nothing between the Fixture's two largest Parties. Four Parties, four bands now."""
    sent = {
        party.name: persona(four_party, party)
        .split("ANOTHER ELECTION\n\n")[1]
        .split(" Nobody else knows")[0]
        for party in four_party.parties
    }

    assert len(set(sent.values())) == len(four_party.parties)
    assert sent["NP"] != sent["FF"]


def test_exclusions_reach_the_agent_as_a_preference_carrying_a_price(
    four_party: Scenario,
) -> None:
    """§3: every Exclusion is soft. A hard constraint would remove the bargain from it."""
    brief = persona(four_party, four_party.party("NP"))

    assert "GV" in brief
    assert "not a veto" in brief
    assert "price" in brief


def test_a_party_with_no_exclusions_is_told_nothing_about_exclusions(
    four_party: Scenario,
) -> None:
    assert "not a veto" not in persona(four_party, four_party.party("MI"))


def test_the_chamber_and_the_vote_rule_reach_every_agent(four_party: Scenario) -> None:
    """Seat arithmetic is the Referee's to report (§2), and it decides what a deal is worth."""
    brief = persona(four_party, four_party.party("MI"))

    assert "175" in brief
    assert "349" in brief
    assert "abstention" in brief.lower()


def test_the_persona_does_not_leak_another_partys_mandate(four_party: Scenario) -> None:
    brief = persona(four_party, four_party.party("NP"))

    assert "the rural broadband programme is funded in full" not in brief


# --- the Bilateral ----------------------------------------------------------------------


def test_three_exchanges_each_way_with_the_formateur_opening(
    four_party: Scenario, tmp_path: Path
) -> None:
    met = hold_bilateral(four_party, Model(), tmp_path)

    assert [exchange.speaker for exchange in met.exchanges] == [
        "NP",
        "FF",
        "NP",
        "FF",
        "NP",
        "FF",
    ]
    assert met.ending is Ending.EXHAUSTED
    assert met.closed_by is None


def test_either_side_may_exit_early_by_agreeing(four_party: Scenario, tmp_path: Path) -> None:
    model = Model(spoken("Support us and you get the broadband money."), spoken("Done.", "agreement"))

    met = hold_bilateral(four_party, model, tmp_path)

    assert len(met.exchanges) == 2
    assert met.ending is Ending.AGREEMENT
    assert met.closed_by == "FF"
    assert met.exchanges[-1].message == said("Done.")


def test_either_side_may_exit_early_by_declaring_impasse(
    four_party: Scenario, tmp_path: Path
) -> None:
    model = Model(spoken("There is nothing here for us.", "impasse"))

    met = hold_bilateral(four_party, model, tmp_path)

    assert len(met.exchanges) == 1
    assert met.ending is Ending.IMPASSE
    assert met.closed_by == "NP"


def test_a_bilateral_is_private_to_the_two_parties_in_it(
    four_party: Scenario, tmp_path: Path
) -> None:
    """The Formateur's own briefing and mandate are never shown to whoever it is meeting."""
    model = Model()

    hold_bilateral(four_party, model, tmp_path)

    counterparty_requests = [model.system(index) for index in range(1, len(model.requests), 2)]
    assert counterparty_requests
    for brief in counterparty_requests:
        assert "You are the leader of NP" not in brief
        assert "a binding cap on public spending growth" not in brief


def test_each_side_hears_only_what_the_other_said(
    four_party: Scenario, tmp_path: Path
) -> None:
    model = Model(spoken("Name your price."), spoken("Broadband, funded in full."))

    hold_bilateral(four_party, model, tmp_path)

    formateurs_second = model.requests[2]["messages"]
    assert formateurs_second[-1] == {
        "role": "user",
        "content": said("Broadband, funded in full."),
    }
    assert formateurs_second[-2] == {"role": "assistant", "content": said("Name your price.")}


def test_the_formateur_hears_the_last_word_even_though_it_gets_no_reply(
    four_party: Scenario, tmp_path: Path
) -> None:
    """A Declaration buys the declarer no answer. It does not unsay what it was carried on.

    The Formateur takes this meeting into its next Round, so a meeting carried forward
    without its closing message is a meeting remembered wrong.
    """
    model = Model(spoken("Name your price."), spoken("Nothing you can pay.", "impasse"))
    agent = FormateurAgent(four_party, four_party.parties[0])

    agent.meet(four_party.party("FF"), Cassettes(tmp_path, live=model))
    agent.meet(four_party.party("MI"), Cassettes(tmp_path, live=model))

    carried = "\n".join(model.said_to(len(model.requests) - 1))
    assert said("Nothing you can pay.") in carried


def test_the_side_about_to_speak_last_is_told_so(
    four_party: Scenario, tmp_path: Path
) -> None:
    """Procedure is the Referee's to report. Without it an Agent signs off 'more to follow'."""
    model = Model()

    hold_bilateral(four_party, model, tmp_path)

    last_prompts = [str(model.requests[index]["messages"][-1]["content"]) for index in (4, 5)]
    assert all("last message" in prompt for prompt in last_prompts)
    assert "last message" not in str(model.requests[0]["messages"][-1]["content"])


def test_the_request_names_the_model_and_caches_the_persona_prefix(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§6: `claude-sonnet-5`, with prompt caching on the stable persona prefix."""
    model = Model()

    hold_bilateral(four_party, model, tmp_path)

    request = model.requests[0]
    assert request["model"] == MODEL == "claude-sonnet-5"
    system = request["system"]
    assert system[0]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in system[1]


def test_the_referee_never_parses_prose(four_party: Scenario, tmp_path: Path) -> None:
    """§2: how a Bilateral ends is a tool call, never something read out of the message."""
    model = Model(spoken("I declare impasse, we are done here."))

    met = hold_bilateral(four_party, model, tmp_path)

    assert met.exchanges[0].declares is None
    assert [tool["name"] for tool in model.requests[0]["tools"]] == ["end_meeting"]


def test_a_bilateral_replays_from_cassettes_with_no_live_calls(
    four_party: Scenario, tmp_path: Path
) -> None:
    live = Model(spoken("One."), spoken("Two."), spoken("Three.", "agreement"))
    recorded = hold_bilateral(four_party, live, tmp_path)

    silent = Model(spoken("this reply is never reached"))
    replayed = hold_bilateral(four_party, silent, tmp_path, replay=True)

    assert replayed == recorded
    assert silent.requests == []


def test_a_truncated_reply_fails_loudly(four_party: Scenario, tmp_path: Path) -> None:
    model = Model({"content": [], "stop_reason": "max_tokens"})

    with pytest.raises(AgentError, match="max_tokens"):
        hold_bilateral(four_party, model, tmp_path)


def test_a_reply_with_no_message_in_it_fails_loudly(
    four_party: Scenario, tmp_path: Path
) -> None:
    """A reply that is only a tool call has ended a meeting nobody was told anything in."""
    model = Model({"content": [], "stop_reason": "end_turn"})

    with pytest.raises(AgentError, match="no text block"):
        hold_bilateral(four_party, model, tmp_path)


def test_a_call_to_a_tool_the_agent_does_not_have_fails_loudly(
    four_party: Scenario, tmp_path: Path
) -> None:
    model = Model(responded(said("Done."), called={"name": "meet", "input": {"party": "FF"}}))

    with pytest.raises(AgentError, match="not a tool it has"):
        hold_bilateral(four_party, model, tmp_path)


def test_an_ending_the_referee_does_not_recognise_fails_loudly(
    four_party: Scenario, tmp_path: Path
) -> None:
    model = Model(
        responded(said("Done."), called={"name": "end_meeting", "input": {"ending": "maybe"}})
    )

    with pytest.raises(AgentError, match="maybe"):
        hold_bilateral(four_party, model, tmp_path)


def test_a_formateur_cannot_meet_itself(four_party: Scenario, tmp_path: Path) -> None:
    agent = FormateurAgent(four_party, four_party.parties[0])

    with pytest.raises(ValueError, match="itself"):
        agent.meet(four_party.parties[0], Cassettes(tmp_path, live=Model()))


def test_a_formateur_alone_in_the_chamber_has_nobody_to_meet(tmp_path: Path) -> None:
    scenario = load_scenario(write_scenario(tmp_path, mandate("AA", 349, positions=positions())))

    with pytest.raises(ValueError, match="nobody to meet"):
        FormateurAgent(scenario, scenario.parties[0])


def test_an_empty_message_is_refused_rather_than_shown_as_an_exchange(
    four_party: Scenario, tmp_path: Path
) -> None:
    """A live Agent did exactly this. An Exchange nobody can read is not an Exchange.

    An empty text block and no text block are one thing to whoever was waiting to be spoken
    to, so they are refused with one message.
    """
    model = Model(responded(""))

    with pytest.raises(AgentError, match="no text block"):
        hold_bilateral(four_party, model, tmp_path)


@pytest.mark.parametrize("fragment", ["Let's be clear on what ", ", let me just write.}"])
def test_a_fragment_is_refused_rather_than_answered_as_though_it_were_a_sentence(
    four_party: Scenario, tmp_path: Path, fragment: str
) -> None:
    """Both of these came back from live Agents, and `minLength: 1` admitted both.

    The second is why this fails loudly instead of being skipped over: the other side read
    the fragment as the opening of a sentence and wrote the rest of it, so a malfunction
    became a turn of the negotiation.
    """
    model = Model(responded(fragment))

    with pytest.raises(AgentError, match="fragment"):
        hold_bilateral(four_party, model, tmp_path)


def test_no_prose_is_ever_decoded_inside_a_constrained_field(
    four_party: Scenario, tmp_path: Path
) -> None:
    """Ticket 02's finding, held in place: prose is the reply's own text and nothing else.

    Roughly one live call in eleven came back empty, truncated or carrying a leaked JSON
    character while two or three paragraphs were being decoded inside a schema's string. The
    fields the Referee reads are short and enumerated, and they are the only constrained
    things in a request.

    Walked to the leaves rather than over the top level, because a Proposal's Platform is ten
    values inside an object and its roles are names inside arrays. An object or an array is a
    container and carries no text of its own; a leaf that is not enumerated is a field an
    Agent writes prose into, which is the one shape this repo does not send.
    """
    model = Model()
    hold_vote(four_party, model, tmp_path)

    assert len(model.requests) > ROUNDS
    named = set()
    for request in model.requests:
        assert "output_config" not in request
        for tool in request["tools"]:
            named.add(tool["name"])
            for path, leaf in _leaves(tool["input_schema"]):
                assert "enum" in leaf, f"{tool['name']}.{path}"
    assert named == {"meet", "end_meeting", "table", "stand_down", "ballot"}


def _leaves(schema: dict[str, Any], path: str = "") -> list[tuple[str, dict[str, Any]]]:
    """Every field of a tool schema that an Agent actually writes a value into."""
    kind = schema.get("type")
    if kind == "object":
        return [
            leaf
            for name, field in schema.get("properties", {}).items()
            for leaf in _leaves(field, f"{path}.{name}" if path else name)
        ]
    if kind == "array":
        return _leaves(schema["items"], f"{path}[]")
    return [(path, schema)]


# --- choosing whom to meet ----------------------------------------------------------------


def test_the_formateur_states_its_reasoning_and_books_the_party_it_named(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§5.1's central strategic act: the reasoning is given before the meeting opens."""
    model = Model(chooses=["MI"])

    choice = make_choice(four_party, model, tmp_path)

    assert choice.counterparty == "MI"
    assert "MI is the one worth the round" in choice.reasoning


def test_the_formateur_is_told_the_budget_and_who_is_left_to_meet(
    four_party: Scenario, tmp_path: Path
) -> None:
    """The budget is the Referee's to report (§2) — an Agent counting its own is one that
    can be wrong about it."""
    model = Model()

    make_choice(four_party, model, tmp_path)

    brief = model.system(0) + "\n".join(model.said_to(0))
    assert f"You have {ROUNDS} rounds" in brief
    assert f"ROUND 1 OF {ROUNDS}" in brief
    for other in ("FF", "GV", "MI"):
        assert other in brief
    assert [tool["name"] for tool in model.requests[0]["tools"]] == ["meet"]
    assert model.requests[0]["tools"][0]["input_schema"]["properties"]["party"]["enum"] == [
        "FF",
        "GV",
        "MI",
    ]


def test_the_formateur_cannot_book_a_meeting_with_itself(
    four_party: Scenario, tmp_path: Path
) -> None:
    """NP is not on the list it is given, and a reply naming it anyway is refused."""
    model = Model(chooses=[chose("NP")])

    with pytest.raises(AgentError, match="not a Party it can meet"):
        make_choice(four_party, model, tmp_path)


def test_a_choice_given_only_in_prose_books_nobody_and_fails_loudly(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§2 again: whom to meet is read from the call, never out of the reasoning."""
    model = Model(chooses=[responded("I will meet MI, obviously.")])

    with pytest.raises(AgentError, match="booking"):
        make_choice(four_party, model, tmp_path)


def test_a_formateur_that_books_two_meetings_at_once_fails_loudly(
    four_party: Scenario, tmp_path: Path
) -> None:
    model = Model(
        chooses=[
            {
                "content": [
                    {"type": "text", "text": "Both of them."},
                    {"type": "tool_use", "id": "a", "name": "meet", "input": {"party": "FF"}},
                    {"type": "tool_use", "id": "b", "name": "meet", "input": {"party": "MI"}},
                ],
                "stop_reason": "tool_use",
            }
        ]
    )

    with pytest.raises(AgentError, match="more than one call"):
        make_choice(four_party, model, tmp_path)


def test_the_counterparty_is_never_told_the_formateur_had_a_choice_to_make(
    four_party: Scenario, tmp_path: Path
) -> None:
    """The Formateur's reasoning about whom to court is the most private thing in the Run."""
    model = Model(chooses=["MI"])

    FormateurAgent(four_party, four_party.parties[0]).spend(Cassettes(tmp_path, live=model))

    formateur, *counterparties = range(len(model.requests))
    for index in counterparties:
        if "You are the leader of MI," not in model.system(index):
            continue
        conversation = "\n".join(model.said_to(index)) + model.system(index)
        assert "worth the round" not in conversation
        assert "ROUND 1" not in conversation


# --- tabling a Proposal, or standing down -------------------------------------------------


def run_attempt(scenario: Scenario, model: Model, tmp_path: Path) -> FormateurAgent:
    """A Formateur with its five Rounds behind it, ready to table."""
    agent = FormateurAgent(scenario, scenario.parties[0])
    cassettes = Cassettes(tmp_path, live=model)
    for _ in range(ROUNDS):
        agent.spend(cassettes)
    return agent


def test_the_formateur_tables_a_proposal_as_structured_output(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§2: the Platform, the roles and the Commitments are read from the call, never prose."""
    model = Model(
        tables=tabled(
            "NP",
            "MI",
            support_only=["GV"],
            commitments=["a binding cap on public spending growth"],
            reasoning="NP and MI govern, GV holds its nose from outside.",
            economic=3,
            law_and_order=4,
        ),
        chooses=["MI", "GV", "FF", "MI", "GV"],
    )
    agent = run_attempt(four_party, model, tmp_path)

    proposal, reasoning = agent.table(Cassettes(tmp_path, live=model))

    assert reasoning == "NP and MI govern, GV holds its nose from outside."
    assert proposal is not None
    assert proposal.formateur == "NP"
    assert proposal.government == ("NP", "MI")
    assert proposal.support_only == ("GV",)
    assert proposal.base == ("NP", "MI", "GV")
    assert proposal.platform.on(Axis.ECONOMIC) == 3
    assert proposal.platform.on(Axis.ENVIRONMENT) == 0
    assert proposal.commitments == ("a binding cap on public spending growth",)


def test_a_formateur_may_stand_down_instead_of_tabling(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§5.3: Standing down ends the Attempt and costs the Chamber none of its four Votes."""
    model = Model(tables=stood_down("Nobody here will pay what a government costs."))
    agent = run_attempt(four_party, model, tmp_path)

    proposal, reasoning = agent.table(Cassettes(tmp_path, live=model))

    assert proposal is None
    assert reasoning == "Nobody here will pay what a government costs."


def test_the_formateur_is_offered_both_tabling_and_standing_down(
    four_party: Scenario, tmp_path: Path
) -> None:
    """The choice is the Formateur's, so both are on the table and neither is the default."""
    model = Model()
    agent = run_attempt(four_party, model, tmp_path)

    agent.table(Cassettes(tmp_path, live=model))

    offered = model.requests[-1]
    assert [tool["name"] for tool in offered["tools"]] == ["table", "stand_down"]
    brief = str(offered["messages"][-1]["content"])
    assert "YOUR ROUNDS ARE SPENT." in brief
    assert "stand down" in brief
    assert "spends none of the four it has" in brief


def test_the_formateur_sees_its_spent_rounds_and_how_each_meeting_ended(
    four_party: Scenario, tmp_path: Path
) -> None:
    """Five meetings on from the first, the endings are worth having in front of it again."""
    model = Model(
        spoken("There is nothing here for us.", "impasse"),
        chooses=["MI", "GV", "FF", "MI", "GV"],
    )
    agent = run_attempt(four_party, model, tmp_path)

    agent.table(Cassettes(tmp_path, live=model))

    brief = str(model.requests[-1]["messages"][-1]["content"])
    assert "round 1 on MI — you declared impasse" in brief
    assert "round 5 on GV — you declared impasse" in brief


def test_no_ministries_or_portfolios_appear_anywhere_in_a_proposal(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§4: cabinet portfolios are deliberately out of scope, so there is nothing to promise."""
    model = Model()
    agent = run_attempt(four_party, model, tmp_path)

    proposal, _ = agent.table(Cassettes(tmp_path, live=model))

    assert proposal is not None
    assert not hasattr(proposal, "ministries")
    offered = model.requests[-1]
    tabling = next(tool for tool in offered["tools"] if tool["name"] == "table")
    assert set(tabling["input_schema"]["properties"]) <= {
        "platform",
        "government",
        "support_only",
        "commitments",
    }
    brief = str(offered["messages"][-1]["content"])
    assert "There are no ministries in it." in brief
    for word in ("ministry", "portfolio", "minister of"):
        assert word not in json.dumps(offered).lower()


def test_a_commitment_can_only_be_one_somebody_charged_for(
    four_party: Scenario, tmp_path: Path
) -> None:
    """A Commitment is a free-text Demand that has been granted, so the menu is the Demands.

    Scoped to the Parties the Formateur actually met, plus its own: a Round buys the price
    list, and a Formateur that courted nobody has only its own to write in.
    """
    model = Model(chooses=["MI"])
    agent = run_attempt(four_party, model, tmp_path)

    agent.table(Cassettes(tmp_path, live=model))

    tabling = next(tool for tool in model.requests[-1]["tools"] if tool["name"] == "table")
    assert tabling["input_schema"]["properties"]["commitments"]["items"]["enum"] == [
        "a binding cap on public spending growth",
        "the rural broadband programme is funded in full",
    ]
    assert "no cuts to the pension floor this term" not in json.dumps(model.requests[-1])


def test_a_commitment_nobody_charged_for_fails_loudly(
    four_party: Scenario, tmp_path: Path
) -> None:
    model = Model(tables=tabled("NP", commitments=["the moon on a stick"]))
    agent = run_attempt(four_party, model, tmp_path)

    with pytest.raises(AgentError, match="nobody charged for"):
        agent.table(Cassettes(tmp_path, live=model))


def test_a_proposal_naming_somebody_who_holds_no_seat_fails_loudly(
    four_party: Scenario, tmp_path: Path
) -> None:
    model = Model(tables=tabled("NP", "ZZ"))
    agent = run_attempt(four_party, model, tmp_path)

    with pytest.raises(AgentError, match="not a Party in Scenario"):
        agent.table(Cassettes(tmp_path, live=model))


def test_a_party_in_both_government_and_support_only_fails_loudly(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§4: Support-only is backing from outside cabinet, so the two roles are exclusive."""
    model = Model(tables=tabled("NP", "MI", support_only=["MI"]))
    agent = run_attempt(four_party, model, tmp_path)

    with pytest.raises(AgentError, match="unusable Proposal"):
        agent.table(Cassettes(tmp_path, live=model))


def test_a_formateur_that_neither_tables_nor_stands_down_fails_loudly(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§2 again: which way an Attempt ended is read from the call, not out of the prose."""
    model = Model(tables=responded("I think we table something along these lines."))
    agent = run_attempt(four_party, model, tmp_path)

    with pytest.raises(AgentError, match="neither tabled a Proposal nor stood down"):
        agent.table(Cassettes(tmp_path, live=model))


# --- the Vote ------------------------------------------------------------------------------


def hold_vote(
    scenario: Scenario, model: Model, tmp_path: Path
) -> tuple[FormateurAgent, tuple[Judgement, ...]]:
    """A whole Attempt through to the Ballots, held on the Proposal the stand-in tables."""
    agent = run_attempt(scenario, model, tmp_path)
    cassettes = Cassettes(tmp_path, live=model)
    proposal, _ = agent.table(cassettes)
    assert proposal is not None
    return agent, agent.put_to_the_chamber(proposal, cassettes)


def test_every_party_casts_a_ballot_in_chamber_order(
    four_party: Scenario, tmp_path: Path
) -> None:
    """Including the Formateur, and including the Parties the Proposal never names — it is
    exactly those whose Abstention is the cheapest thing on offer (§5.2)."""
    model = Model(tables=tabled("NP"), ballots=["Yes", "No", "Abstain", "Abstain"])

    _, judgements = hold_vote(four_party, model, tmp_path)

    assert [judgement.party for judgement in judgements] == ["NP", "FF", "GV", "MI"]
    assert [judgement.ballot for judgement in judgements] == [
        Ballot.YES,
        Ballot.NO,
        Ballot.ABSTAIN,
        Ballot.ABSTAIN,
    ]


def test_a_ballot_is_structured_and_its_reasoning_is_prose(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§2: the Referee counts the enumerated field; the sentence is for the Transcript."""
    model = Model(
        tables=tabled("NP"),
        ballots=[voted("No", "Five points from our voters on health. No.")],
    )

    _, judgements = hold_vote(four_party, model, tmp_path)

    assert judgements[0].ballot is Ballot.NO
    assert judgements[0].reasoning == "Five points from our voters on health. No."
    voting = [
        request
        for request in model.requests
        if any(tool["name"] == "ballot" for tool in request["tools"])
    ]
    assert len(voting) == len(four_party.parties)
    for request in voting:
        assert [tool["name"] for tool in request["tools"]] == ["ballot"]


def test_each_party_is_shown_its_own_gap_report_before_it_judges(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§5.4: the only defence this design has against a mushy grand coalition every Run."""
    model = Model(tables=tabled("NP", economic=3, environment=-2))

    hold_vote(four_party, model, tmp_path)

    shown = voting(model)
    assert set(shown) == {"NP", "FF", "GV", "MI"}
    for name, brief in shown.items():
        assert f"{name}: its Positions against this Platform." in brief
        assert "mean Gap:" in brief
        assert "worst Gap:" in brief
    assert (
        render_gap_report(gap_report(four_party.party("GV"), platform(economic=3, environment=-2)))
        in shown["GV"]
    )
    assert "GV: its Positions" not in shown["FF"]


def test_a_party_in_the_base_is_shown_what_the_platform_pays_of_its_own_price(
    four_party: Scenario, tmp_path: Path
) -> None:
    """The first ticket that shows a Demand as persona prose and as a report cell at once."""
    model = Model(tables=tabled("NP", "MI", support_only=["GV"], environment=1))

    hold_vote(four_party, model, tmp_path)
    offered = platform(environment=1)

    shown = voting(model)
    assert "WHAT IT PAYS OF YOUR GOVERNING PRICE" in shown["MI"]
    assert (
        render_price_report(price_report(four_party.party("MI"), offered, Price.GOVERNING))
        in shown["MI"]
    )
    assert "unevaluated  the rural broadband programme is funded in full" in shown["MI"]
    assert "WHAT IT PAYS OF YOUR SUPPORTING PRICE" in shown["GV"]
    assert (
        render_price_report(price_report(four_party.party("GV"), offered, Price.SUPPORTING))
        in shown["GV"]
    )
    assert "unmet  environment >= +2" in shown["GV"]
    assert "Supporting price" not in shown["MI"]


def test_a_party_is_shown_where_the_proposal_puts_the_parties_it_excludes(
    four_party: Scenario, tmp_path: Path
) -> None:
    """§5.4's argument reaching the coalition: KD and L waved through a government holding a
    Party both of them exclude, and nothing at the Vote had put the two facts side by side."""
    model = Model(tables=tabled("NP", support_only=["GV"]))

    hold_vote(four_party, model, tmp_path)
    on_the_table = Proposal(
        formateur="NP", platform=platform(), government=("NP",), support_only=("GV",)
    )
    report = exclusion_report(four_party.party("FF"), on_the_table)
    assert report is not None

    shown = voting(model)
    assert "WHERE IT PUTS THE PARTIES YOU WOULD RATHER NOT DEAL WITH" in shown["FF"]
    assert render_exclusion_report(report) in shown["FF"]
    assert "NP  in the Government" in shown["FF"]
    assert "NP  Support-only" not in shown["FF"]


def test_the_exclusion_report_asks_for_nothing_but_that_the_party_know(
    four_party: Scenario, tmp_path: Path
) -> None:
    """Feedback, never a constraint (§2): an Exclusion is soft and priced, and a Party is
    free to wave through a government built on one."""
    model = Model(tables=tabled("NP", support_only=["GV"]))

    hold_vote(four_party, model, tmp_path)

    shown = voting(model)["FF"]
    assert "preferences with a price" in shown
    assert "you may wave it through" in shown


def test_a_party_that_names_nobody_is_shown_no_exclusion_report(
    four_party: Scenario, tmp_path: Path
) -> None:
    """MI would deal with anybody, so the section is omitted rather than saying "none" —
    the way `_who_you_would_rather_not_deal_with` already omits its own."""
    model = Model(tables=tabled("NP", support_only=["GV"]))

    hold_vote(four_party, model, tmp_path)

    shown = voting(model)
    assert "WOULD RATHER NOT DEAL WITH" not in shown["MI"]
    assert "WOULD RATHER NOT DEAL WITH" in shown["NP"]


def test_a_party_the_proposal_does_not_name_is_told_it_is_asked_nothing(
    four_party: Scenario, tmp_path: Path
) -> None:
    """Its Abstention is the cheapest thing a Formateur can buy, and it is not being sold
    anything — so it is shown its Gap report and no price list for a bargain nobody offered."""
    model = Model(tables=tabled("NP", "MI"))

    hold_vote(four_party, model, tmp_path)

    shown = voting(model)
    assert "It does not name you at all." in shown["FF"]
    assert "WHAT IT PAYS OF YOUR" not in shown["FF"]
    assert "FF: its Positions against this Platform." in shown["FF"]
    assert "It puts you in the cabinet." in shown["MI"]


def test_a_party_votes_in_the_room_it_bargained_in(
    four_party: Scenario, tmp_path: Path
) -> None:
    """The Proposal is judged against the terms it reached, so it has to remember them."""
    model = Model(
        spoken("Environment at +2 and I stay out of your way."),
        chooses=["GV"],
        tables=tabled("NP"),
    )

    hold_vote(four_party, model, tmp_path)

    voting = next(
        request
        for request in model.requests
        if any(tool["name"] == "ballot" for tool in request["tools"])
        and "You are the leader of GV," in briefing(request)
    )
    told = "\n".join(str(message["content"]) for message in voting["messages"])
    assert said("Environment at +2 and I stay out of your way.") in told
    assert "You are now in the room with" not in told


def test_a_party_never_courted_still_votes_and_carries_no_bilateral_into_it(
    four_party: Scenario, tmp_path: Path
) -> None:
    """It holds every seat it was elected with whether or not the Formateur came to see it."""
    model = Model(chooses=["MI"], tables=tabled("NP", "MI"))

    _, judgements = hold_vote(four_party, model, tmp_path)

    assert {judgement.party for judgement in judgements} == {"NP", "FF", "GV", "MI"}
    unmet = next(
        request
        for request in model.requests
        if any(tool["name"] == "ballot" for tool in request["tools"])
        and "You are the leader of FF," in briefing(request)
    )
    assert len(unmet["messages"]) == 1
    assert "It never came to see you." in briefing(unmet)


def test_a_ballot_the_referee_does_not_recognise_fails_loudly(
    four_party: Scenario, tmp_path: Path
) -> None:
    model = Model(
        tables=tabled("NP"),
        ballots=[responded(said("Maybe."), called={"name": "ballot", "input": {"ballot": "Nej"}})],
    )

    with pytest.raises(AgentError, match="not a Ballot"):
        hold_vote(four_party, model, tmp_path)


def test_a_party_that_says_its_piece_without_voting_fails_loudly(
    four_party: Scenario, tmp_path: Path
) -> None:
    model = Model(tables=tabled("NP"), ballots=[responded("We are minded to let it through.")])

    with pytest.raises(AgentError, match="without voting"):
        hold_vote(four_party, model, tmp_path)


def voting(model: Model) -> dict[str, str]:
    """What each Party was shown before it cast its Ballot, keyed by whose it was.

    Read off the requests rather than off the code that built them: what a Party was shown is
    the thing under test, and three tests were each rebuilding this by hand.
    """
    return {
        _leader(model.system(index)): str(request["messages"][-1]["content"])
        for index, request in enumerate(model.requests)
        if any(tool["name"] == BALLOT for tool in request["tools"])
    }


def _leader(system: str) -> str:
    """Whose conversation a request belongs to, read off the persona's first line."""
    return system.split("You are the leader of ", 1)[1].split(",", 1)[0]


def test_a_call_with_no_prose_beside_it_still_answers_the_question_it_was_asked(
    four_party: Scenario, tmp_path: Path
) -> None:
    """A live Attempt aborted on exactly this: `meet` called after a turn of thinking, with
    no sentence beside it. Nobody in the Run reads a reasoning, so nothing was lost but the
    sentence — and re-rolling a paid Attempt over it would have lost the whole Attempt."""
    booked = responded("", called={"name": "meet", "input": {"party": "MI"}})
    del booked["content"][0]

    model = Model(
        chooses=[booked],
        tables=responded("", called={"name": "stand_down", "input": {}}),
    )
    run = attempt(
        four_party,
        formateur=four_party.parties[0],
        cassettes=Cassettes(tmp_path, live=model),
    )

    assert run.rounds[0].counterparty == "MI"
    assert run.rounds[0].choice.reasoning == ""
    assert run.stood_down
    assert run.reasoning == ""


def test_a_ballot_with_no_prose_beside_it_is_still_counted(
    four_party: Scenario, tmp_path: Path
) -> None:
    cast = responded("", called={"name": "ballot", "input": {"ballot": "No"}})
    del cast["content"][0]

    _, judgements = hold_vote(
        four_party, Model(tables=tabled("NP"), ballots=[cast]), tmp_path
    )

    assert all(judgement.ballot is Ballot.NO for judgement in judgements)
    assert all(judgement.reasoning == "" for judgement in judgements)


def test_an_exchange_with_no_prose_beside_it_is_still_refused(
    four_party: Scenario, tmp_path: Path
) -> None:
    """The other side answers an Exchange, so a missing one is a turn that never happened."""
    silent = responded("", called={"name": "end_meeting", "input": {"ending": "agreement"}})
    del silent["content"][0]

    with pytest.raises(AgentError, match="no text block"):
        hold_bilateral(four_party, Model(silent), tmp_path)


def test_a_reply_that_did_not_finish_still_fails_however_little_it_was_asked_for(
    four_party: Scenario, tmp_path: Path
) -> None:
    """Waving a missing aside through must not wave through a truncated or refused reply."""
    model = Model(chooses=[{"content": [], "stop_reason": "max_tokens"}])

    with pytest.raises(AgentError, match="max_tokens"):
        make_choice(four_party, model, tmp_path)


def test_a_platform_that_is_not_ten_axis_values_fails_loudly(
    four_party: Scenario, tmp_path: Path
) -> None:
    model = Model(
        tables=responded(
            "Here it is.",
            called={"name": "table", "input": {"platform": "centrist", "government": ["NP"]}},
        )
    )
    agent = run_attempt(four_party, model, tmp_path)

    with pytest.raises(AgentError, match="tabled a Platform of"):
        agent.table(Cassettes(tmp_path, live=model))


def test_a_government_of_nobody_is_not_a_government(
    four_party: Scenario, tmp_path: Path
) -> None:
    """A Formateur with nobody to put in cabinet has stood down, whatever tool it called.

    Caught on the way back in rather than in the schema. Ticket 02 found the API drops
    `minLength` from a schema and recorded the lesson that a schema carrying a constraint it
    does not enforce is lying; the floor that is certain is the one checked here.
    """
    model = Model(tables=tabled())
    agent = run_attempt(four_party, model, tmp_path)

    with pytest.raises(AgentError, match="nobody in its government"):
        agent.table(Cassettes(tmp_path, live=model))


def test_a_formateur_of_eight_parties_is_told_it_cannot_meet_them_all(
    riksdag_2026: Scenario, tmp_path: Path
) -> None:
    """§5.1: seven other Parties and five Rounds, so some Party goes uncourted.

    The first Scenario where this fires — every Fixture is small enough for the budget to
    reach the whole chamber, and telling a Formateur otherwise would be the Referee reporting
    something false about its own procedure. Read off the request, because what matters is
    what the Agent was actually sent.
    """
    model = Model()
    formateur = riksdag_2026.parties[0]
    assert len(riksdag_2026.parties) - 1 > ROUNDS

    FormateurAgent(riksdag_2026, formateur).spend(Cassettes(tmp_path, live=model))

    assert formateur.name == "S"
    assert "you cannot see them all: some party will go uncourted" in briefing(model.requests[0])
