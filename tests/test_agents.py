"""Persona construction and the Bilateral. Zero API calls: every model here is a stand-in."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import Model, chose, mandate, positions, responded, said, spoken, write_scenario
from kbbl.agents import MODEL, AgentError, FormateurAgent, persona
from kbbl.cassettes import Cassettes
from kbbl.models import Bilateral, Choice, Ending, Scenario
from kbbl.referee import ROUNDS
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
    """A live Agent did exactly this. An Exchange nobody can read is not an Exchange."""
    model = Model(responded(""))

    with pytest.raises(AgentError, match="unusable|fragment"):
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
    """
    model = Model()
    FormateurAgent(four_party, four_party.parties[0]).spend(Cassettes(tmp_path, live=model))

    assert len(model.requests) > 1
    for request in model.requests:
        assert "output_config" not in request
        for tool in request["tools"]:
            fields = tool["input_schema"]["properties"].values()
            assert all("enum" in field for field in fields), tool["name"]


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
