"""Persona construction and the Bilateral. Zero API calls: every model here is a stand-in."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import Model, mandate, positions, responded, said, spoken, write_scenario
from kbbl.agents import MODEL, AgentError, bilateral, persona
from kbbl.cassettes import Cassettes
from kbbl.models import Bilateral, Ending, Scenario
from kbbl.scenario import load_scenario


def hold_bilateral(
    scenario: Scenario, model: Model, tmp_path: Path, replay: bool = False
) -> Bilateral:
    return bilateral(
        scenario,
        formateur=scenario.parties[0],
        counterparty=scenario.parties[1],
        cassettes=Cassettes(tmp_path, replay=replay, live=model),
    )


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
    """§2: how a Bilateral ends is structured output, not something read out of the message."""
    model = Model(spoken("I declare impasse, we are done here."))

    met = hold_bilateral(four_party, model, tmp_path)

    assert met.exchanges[0].declares is None
    assert model.requests[0]["output_config"]["format"]["type"] == "json_schema"


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


def test_a_reply_that_is_not_the_agreed_shape_fails_loudly(
    four_party: Scenario, tmp_path: Path
) -> None:
    model = Model(responded("sure, sounds good to me"))

    with pytest.raises(AgentError):
        hold_bilateral(four_party, model, tmp_path)


def test_a_formateur_cannot_meet_itself(tmp_path: Path) -> None:
    scenario = load_scenario(write_scenario(tmp_path, mandate("AA", 349, positions=positions())))

    with pytest.raises(ValueError, match="itself"):
        bilateral(
            scenario,
            formateur=scenario.parties[0],
            counterparty=scenario.parties[0],
            cassettes=Cassettes(tmp_path, live=Model()),
        )


def test_an_empty_message_is_refused_rather_than_shown_as_an_exchange(
    four_party: Scenario, tmp_path: Path
) -> None:
    """A live Agent did exactly this. An Exchange nobody can read is not an Exchange."""
    model = Model(responded(json.dumps({"message": "", "ending": "continue"})))

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
    model = Model(responded(json.dumps({"message": fragment, "ending": "continue"})))

    with pytest.raises(AgentError, match="fragment"):
        hold_bilateral(four_party, model, tmp_path)


def test_the_schema_does_not_claim_to_enforce_the_message_floor(four_party: Scenario) -> None:
    """Structured outputs drop `minLength`, so a floor written there is a silent no-op.

    An empty message came back from a schema asking for 200 characters. The schema must not
    carry a constraint that reads like a guarantee and is not one.
    """
    from kbbl.agents import EXCHANGE_FORMAT

    assert "minLength" not in EXCHANGE_FORMAT["schema"]["properties"]["message"]
