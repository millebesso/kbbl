"""`kbbl run <scenario>` — load a Scenario, print the chamber, and hold a Bilateral.

Live is the default and `--replay` opts out (§11.5): a Run that negotiates is a Run that
calls the model, and the free path is the recorded one.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from kbbl.agents import AgentError, bilateral
from kbbl.cassettes import CassetteMiss, Cassettes
from kbbl.models import Party, Run, Scenario
from kbbl.output import render_transcript
from kbbl.referee import render_blocking_groupings, render_seat_table
from kbbl.scenario import ScenarioError, load_scenario

CASSETTES = Path("cassettes")
"""Where recordings live. Each Scenario gets its own drawer under it, so two Scenarios cannot
collide on a request that happens to hash the same."""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kbbl", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="load a Scenario and negotiate")
    run.add_argument("scenario", help="directory of Party mandates")
    run.add_argument(
        "--meet",
        metavar="PARTY",
        help=(
            "which Party the Formateur meets. Defaults to the largest other Party; ticket 04 "
            "gives the Formateur this choice for itself."
        ),
    )
    run.add_argument(
        "--replay",
        action="store_true",
        help="replay from Cassettes, making no API calls",
    )
    run.add_argument(
        "--cassettes",
        type=Path,
        default=CASSETTES,
        metavar="DIR",
        help=(
            "root directory of Cassettes; each Scenario gets its own drawer under it "
            f"(default: {CASSETTES})"
        ),
    )
    arguments = parser.parse_args(argv)

    try:
        scenario = load_scenario(arguments.scenario)
        counterparty = _counterparty(scenario, arguments.meet)
    except ScenarioError as error:
        print(error, file=sys.stderr)
        return 1

    formateur = scenario.parties[0]
    print(f"Scenario: {scenario.name} ({len(scenario.parties)} Parties, {scenario.seats} seats)")
    print()
    print(render_seat_table(scenario))
    print()
    print(render_blocking_groupings(scenario))
    print()

    try:
        met = bilateral(
            scenario,
            formateur=formateur,
            counterparty=counterparty,
            cassettes=Cassettes(
                arguments.cassettes / scenario.name, replay=arguments.replay
            ),
        )
    except (AgentError, CassetteMiss) as error:
        print(error, file=sys.stderr)
        return 1

    record = Run(scenario=scenario.name, formateur=formateur.name, bilaterals=(met,))
    print(render_transcript(record))
    return 0


def _counterparty(scenario: Scenario, named: str | None) -> Party:
    """Whom the Formateur meets. A placeholder for the choice ticket 04 hands the Formateur."""
    formateur, *others = scenario.parties
    if not others:
        raise ScenarioError(
            f"{scenario.name} has only one Party, so there is nobody for {formateur.name} to meet"
        )
    if named is None:
        return others[0]
    if named == formateur.name:
        raise ScenarioError(f"{formateur.name} is the Formateur and cannot meet itself")
    try:
        return scenario.party(named)
    except KeyError:
        known = ", ".join(party.name for party in others)
        raise ScenarioError(f"no Party named {named!r} to meet. Choose one of: {known}") from None
