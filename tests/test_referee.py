"""Seat arithmetic and the Blocking minority. Costs nothing to test, so it is tested hard."""

from __future__ import annotations

from pathlib import Path

from conftest import mandate, write_scenario
from kbbl.models import Scenario
from kbbl.referee import (
    BLOCKING_MINORITY,
    blocking_groupings,
    render_blocking_groupings,
    render_seat_table,
)
from kbbl.scenario import load_scenario


def test_the_blocking_minority_is_an_absolute_majority_of_349() -> None:
    assert BLOCKING_MINORITY == 175
    assert BLOCKING_MINORITY * 2 > 349


def test_the_fixtures_groupings_put_every_party_in_at_least_one(
    four_party: Scenario,
) -> None:
    """No Party in this Fixture is a null player — each one is pivotal somewhere."""
    groupings = blocking_groupings(four_party)

    assert [(g.parties, g.seats) for g in groupings] == [
        (("NP", "FF"), 272),
        (("NP", "GV"), 182),
        (("NP", "MI"), 175),
        (("FF", "GV", "MI"), 209),
    ]
    assert {name for g in groupings for name in g.parties} == {"NP", "FF", "GV", "MI"}


def test_only_minimal_groupings_are_reported(four_party: Scenario) -> None:
    """NP+MI+GV clears 175, but NP+MI already does — the third Party is not load-bearing."""
    groupings = blocking_groupings(four_party)

    assert ("NP", "MI", "GV") not in [g.parties for g in groupings]
    for grouping in groupings:
        for name in grouping.parties:
            assert grouping.seats - four_party.party(name).seats < BLOCKING_MINORITY


def test_a_party_above_the_blocking_minority_is_a_grouping_of_one(tmp_path: Path) -> None:
    write_scenario(tmp_path, mandate("AA", 200), mandate("BB", 100), mandate("CC", 49))

    groupings = blocking_groupings(load_scenario(tmp_path))

    assert [g.parties for g in groupings] == [("AA",)]


def test_a_chamber_can_have_no_grouping_short_of_a_pair(tmp_path: Path) -> None:
    """Three near-equal thirds: every pair clears 175, so no single Party does."""
    write_scenario(tmp_path, mandate("AA", 117), mandate("BB", 116), mandate("CC", 116))

    assert [g.parties for g in blocking_groupings(load_scenario(tmp_path))] == [
        ("AA", "BB"),
        ("AA", "CC"),
        ("BB", "CC"),
    ]


def test_the_seat_table_lists_every_party_largest_first(four_party: Scenario) -> None:
    table = render_seat_table(four_party)

    names = [line.split()[0] for line in table.splitlines()]
    assert names == ["Party", "-----", "NP", "FF", "GV", "MI", "-----", "Total"]
    assert table.splitlines()[-1].split() == ["Total", "349", "100.0%"]


def test_the_grouping_report_names_the_blocking_minority(four_party: Scenario) -> None:
    report = render_blocking_groupings(four_party)

    assert "Blocking minority: 175 of 349 seats." in report
    assert "NP + MI" in report
