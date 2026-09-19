"""The Referee's seat arithmetic: who sits in the chamber, and who can block.

The Referee computes and reports. Nothing here constrains an Agent's choice.
"""

from __future__ import annotations

from itertools import combinations
from typing import NamedTuple

from kbbl.models import TOTAL_SEATS, Scenario

BLOCKING_MINORITY = 175
"""The seats that must vote No to defeat a Proposal — an absolute majority of 349."""


class Grouping(NamedTuple):
    """A set of Parties and the seats they hold between them."""

    parties: tuple[str, ...]
    seats: int


def blocking_groupings(scenario: Scenario) -> list[Grouping]:
    """Every *minimal* grouping that reaches the Blocking minority.

    Minimal means no member can be dropped and still reach it. Listing every grouping
    instead would bury the interesting ones under their own supersets; listing the minimal
    ones names each kingmaker exactly once.
    """
    by_seats = {party.name: party.seats for party in scenario.parties}
    found: list[Grouping] = []
    for size in range(1, len(by_seats) + 1):
        for names in combinations(by_seats, size):
            seats = sum(by_seats[name] for name in names)
            if seats < BLOCKING_MINORITY:
                continue
            if any(seats - by_seats[name] >= BLOCKING_MINORITY for name in names):
                continue
            found.append(Grouping(names, seats))
    found.sort(key=lambda grouping: (len(grouping.parties), -grouping.seats, grouping.parties))
    return found


def render_seat_table(scenario: Scenario) -> str:
    """The chamber, largest Party first."""
    width = max(5, *(len(party.name) for party in scenario.parties))
    rule = f"{'-' * width}  -----  ------"
    lines = [f"{'Party':<{width}}  Seats   Share", rule]
    for party in scenario.parties:
        share = 100 * party.seats / scenario.seats
        lines.append(f"{party.name:<{width}}  {party.seats:>5}  {share:>5.1f}%")
    lines.append(rule)
    lines.append(f"{'Total':<{width}}  {scenario.seats:>5}  {100.0:>5.1f}%")
    return "\n".join(lines)


def render_blocking_groupings(scenario: Scenario) -> str:
    """Which groupings clear the Blocking minority, and by how much."""
    groupings = blocking_groupings(scenario)
    lines = [
        f"Blocking minority: {BLOCKING_MINORITY} of {TOTAL_SEATS} seats.",
        "Minimal groupings that reach it:",
    ]
    if not groupings:
        lines.append("  none")
        return "\n".join(lines)

    labels = [" + ".join(grouping.parties) for grouping in groupings]
    width = max(len(label) for label in labels)
    for label, grouping in zip(labels, groupings, strict=True):
        margin = grouping.seats - BLOCKING_MINORITY
        lines.append(f"  {label:<{width}}  {grouping.seats:>3}  (+{margin})")
    return "\n".join(lines)
