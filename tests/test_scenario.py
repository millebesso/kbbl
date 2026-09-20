"""The boundary: hand-written mandates in, a validated Scenario out — or a useful failure."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import FOUR_PARTY, mandate, positions, two_party, write_scenario
from kbbl.agents import persona
from kbbl.models import (
    TOTAL_SEATS,
    Axis,
    AxisDemand,
    Party,
    Positions,
    Scenario,
    TextDemand,
)
from kbbl.scenario import ScenarioError, load_scenario


def test_the_four_party_fixture_loads(four_party: Scenario) -> None:
    assert four_party.name == "four-party"
    assert [party.name for party in four_party.parties] == ["NP", "FF", "GV", "MI"]
    assert four_party.seats == 349


def test_fixtures_load_through_the_same_path_as_scenarios(
    tmp_path: Path, four_party: Scenario
) -> None:
    """One loader, never two — a Fixture is a Scenario in every respect."""
    scenario = load_scenario(two_party(tmp_path / "scenarios" / "invented"))

    assert scenario.name == "invented"
    assert scenario.seats == four_party.seats


def test_seats_must_sum_to_349(tmp_path: Path) -> None:
    write_scenario(tmp_path, mandate("AA", 200), mandate("BB", 148))

    with pytest.raises(ScenarioError, match="seats sum to 348, not 349"):
        load_scenario(tmp_path)


def test_an_axis_out_of_range_is_rejected(tmp_path: Path) -> None:
    two_party(tmp_path, positions=positions(environment=6))

    with pytest.raises(ScenarioError, match=r"positions\.environment"):
        load_scenario(tmp_path)


def test_a_missing_axis_is_rejected(tmp_path: Path) -> None:
    incomplete = positions()
    del incomplete["transport"]
    two_party(tmp_path, positions=incomplete)

    with pytest.raises(ScenarioError, match=r"positions\.transport"):
        load_scenario(tmp_path)


def test_an_unknown_axis_is_rejected(tmp_path: Path) -> None:
    """A typo must not be silently accepted as a new Axis."""
    two_party(tmp_path, positions=positions() | {"enviroment": 3})

    with pytest.raises(ScenarioError, match=r"positions\.enviroment"):
        load_scenario(tmp_path)


def test_a_malformed_mandate_names_the_party_and_the_field(tmp_path: Path) -> None:
    two_party(tmp_path, willingness_to_re_elect=99)

    with pytest.raises(ScenarioError) as failure:
        load_scenario(tmp_path)

    message = str(failure.value)
    assert "AA" in message
    assert "willingness_to_re_elect" in message
    assert "Traceback" not in message


def test_every_error_in_a_mandate_is_reported_at_once(tmp_path: Path) -> None:
    two_party(tmp_path, seats="two hundred", positions=positions(social=-9))

    with pytest.raises(ScenarioError) as failure:
        load_scenario(tmp_path)

    message = str(failure.value)
    assert "seats" in message
    assert "positions.social" in message


def test_both_price_lists_mix_axis_and_text_demands(tmp_path: Path) -> None:
    two_party(
        tmp_path,
        to_govern=[
            {"axis": "environment", "op": ">=", "value": 3},
            {"text": "no new nuclear this term"},
        ],
        to_support=[
            {"text": "drop the investigation"},
            {"axis": "environment", "op": ">=", "value": 1},
        ],
    )

    party = load_scenario(tmp_path).party("AA")

    assert party.to_govern == (
        AxisDemand(axis=Axis.ENVIRONMENT, op=">=", value=3),
        TextDemand(text="no new nuclear this term"),
    )
    assert party.to_support == (
        TextDemand(text="drop the investigation"),
        AxisDemand(axis=Axis.ENVIRONMENT, op=">=", value=1),
    )


def test_a_demand_that_is_neither_axis_nor_text_is_rejected(tmp_path: Path) -> None:
    two_party(tmp_path, to_govern=[{"axis": "environment", "value": 3}])

    with pytest.raises(ScenarioError, match="to_govern"):
        load_scenario(tmp_path)


def test_exclusions_and_willingness_round_trip(tmp_path: Path) -> None:
    write_scenario(
        tmp_path,
        mandate("AA", 200, prefer_not=["BB"], willingness_to_re_elect=9),
        mandate("BB", 149),
    )

    party = load_scenario(tmp_path).party("AA")

    assert party.prefer_not == ("BB",)
    assert party.willingness_to_re_elect == 9
    assert Party.model_validate_json(party.model_dump_json()) == party


def test_an_exclusion_naming_an_unknown_party_is_rejected(tmp_path: Path) -> None:
    """Exclusions are soft, but a typo in one must not quietly do nothing."""
    two_party(tmp_path, prefer_not=["CC"])

    with pytest.raises(ScenarioError, match="CC"):
        load_scenario(tmp_path)


def test_two_parties_may_not_share_a_name(tmp_path: Path) -> None:
    write_scenario(tmp_path, mandate("AA", 200))
    (tmp_path / "duplicate.json").write_text(
        (tmp_path / "AA.json").read_text(encoding="utf-8").replace("200", "149"),
        encoding="utf-8",
    )

    with pytest.raises(ScenarioError, match="AA"):
        load_scenario(tmp_path)


def test_invalid_json_names_the_file(tmp_path: Path) -> None:
    two_party(tmp_path)
    (tmp_path / "AA.json").write_text("{not json", encoding="utf-8")

    with pytest.raises(ScenarioError, match="AA.json"):
        load_scenario(tmp_path)


def test_a_missing_scenario_directory_is_reported(tmp_path: Path) -> None:
    with pytest.raises(ScenarioError, match="no such Scenario directory"):
        load_scenario(tmp_path / "absent")


def test_a_scenario_directory_without_mandates_is_reported(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()

    with pytest.raises(ScenarioError, match="no Party mandates"):
        load_scenario(tmp_path / "empty")


def test_positions_declare_exactly_the_ten_axes() -> None:
    """The one place the Axis list is stated twice, pinned so they cannot drift apart."""
    assert tuple(Positions.model_fields) == tuple(axis.value for axis in Axis)
    assert len(Axis) == 10


def test_every_mandate_in_the_fixture_survives_a_round_trip(four_party: Scenario) -> None:
    for party in four_party.parties:
        assert Party.model_validate_json(party.model_dump_json()) == party


def test_a_field_path_inside_a_price_list_names_the_demands_own_field(
    tmp_path: Path,
) -> None:
    """Pydantic puts the union tag in `loc`; the author never wrote it, so it is dropped."""
    two_party(
        tmp_path,
        to_govern=[
            {"axis": "environment", "op": ">=", "value": 3},
            {"axis": "social", "value": 1},
        ],
    )

    with pytest.raises(ScenarioError, match=r"to_govern\[1\]\.op: Field required"):
        load_scenario(tmp_path)


# --- the real parliament (§9) ----------------------------------------------------------------


def test_the_2026_riksdag_loads_through_the_one_load_path(riksdag_2026: Scenario) -> None:
    """§9, §11.6: a Fixture is a Scenario, so the real parliament needs no loader of its own.

    The seats are the one part of this Scenario that is fact, and they are checkable — so
    they are checked, against §9's table rather than against whatever the files happen to say.
    """
    assert riksdag_2026.name == "riksdag-2026"
    assert {party.name: party.seats for party in riksdag_2026.parties} == {
        "S": 99,
        "M": 70,
        "SD": 62,
        "V": 30,
        "C": 25,
        "KD": 22,
        "MP": 22,
        "L": 19,
    }
    assert riksdag_2026.seats == TOTAL_SEATS


def test_the_real_scenario_loads_largest_first(riksdag_2026: Scenario) -> None:
    """The loader's sort, which `load_scenario` says is also Formateur order.

    §9 states the order it produces here — S → M → SD → V — and nothing in this module
    reaches the Formateur: what is pinned is that the boundary hands the chamber back in the
    order §5.3 reads the Formateur off. Not a cap of four, either; Standing down spends no
    Vote, so all eight can have an Attempt.
    """
    assert [party.name for party in riksdag_2026.parties] == [
        "S",
        "M",
        "SD",
        "V",
        "C",
        "KD",
        "MP",
        "L",
    ]


def test_every_exclusion_reaches_its_agent_as_a_preference(riksdag_2026: Scenario) -> None:
    """§3, decision 7: every Exclusion is soft and has a price.

    Nothing is checked here about the names being real — `Scenario` refuses a dangling
    Exclusion before a Run can start, and `test_an_exclusion_naming_an_unknown_party_is_
    rejected` above is where that is pinned. What can go wrong and is not covered elsewhere
    is the softness: there is no field a Mandate could use to encode a veto, so the only
    thing holding this open is the prose each Agent is actually shown.
    """
    excluded = {
        (party.name, other)
        for party in riksdag_2026.parties
        for other in party.prefer_not
    }

    assert len(excluded) == 10, "every one of the eight Parties names somebody"
    assert ("C", "SD") in excluded
    for name, _ in excluded:
        assert "preference, not a veto" in persona(riksdag_2026, riksdag_2026.party(name))


def test_every_mandate_in_the_real_scenario_survives_a_round_trip(
    riksdag_2026: Scenario,
) -> None:
    assert len(riksdag_2026.parties) == 8
    for party in riksdag_2026.parties:
        assert Party.model_validate_json(party.model_dump_json()) == party
