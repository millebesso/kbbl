"""Loading a Scenario from disk.

A Fixture is a Scenario in every respect, so this is the only load path there is. Mandates
are hand-written, so a bad one must fail with a message that names the Party and the
offending field — never a stack trace.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from kbbl.models import Party, Scenario

_DEMAND_TAGS = frozenset({"axis", "text"})
"""The tags of the Demand union. Pydantic reports them inside `loc`; authors never wrote
them, so they are dropped when a field path is shown back to a human."""


class ScenarioError(Exception):
    """A Scenario could not be loaded. Carries a message written for a person."""


def load_scenario(directory: Path | str) -> Scenario:
    """Load every Party mandate in `directory` into a validated Scenario.

    Parties come back in chamber order — largest first, ties broken by name — which is
    also Formateur order.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise ScenarioError(f"no such Scenario directory: {directory}")

    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise ScenarioError(f"no Party mandates (*.json) in {directory}")

    parties = [_load_party(path) for path in paths]
    parties.sort(key=lambda party: (-party.seats, party.name))

    try:
        return Scenario(name=directory.name, parties=tuple(parties))
    except ValidationError as error:
        raise ScenarioError(
            _describe(f"{directory} is not a valid Scenario", error)
        ) from error


def _load_party(path: Path) -> Party:
    raw = path.read_text(encoding="utf-8")
    try:
        return Party.model_validate_json(raw)
    except ValidationError as error:
        raise ScenarioError(
            _describe(f"{_label(path, raw)} is not a valid mandate", error)
        ) from error


def _label(path: Path, raw: str) -> str:
    """Name the Party if the file says who it is, and the file either way."""
    try:
        data = json.loads(raw)
    except ValueError:
        return str(path)
    name = data.get("name") if isinstance(data, dict) else None
    return f"{name} ({path})" if isinstance(name, str) and name else str(path)


def _describe(heading: str, error: ValidationError) -> str:
    lines = [f"{heading}:"]
    for problem in error.errors():
        field = _field_path(problem["loc"])
        message = _message(problem)
        lines.append(f"  {field}: {message}" if field else f"  {message}")
    return "\n".join(lines)


def _field_path(loc: tuple[int | str, ...]) -> str:
    parts: list[str] = []
    for index, segment in enumerate(loc):
        if isinstance(segment, int):
            parts.append(f"[{segment}]")
        elif index and isinstance(loc[index - 1], int) and segment in _DEMAND_TAGS:
            continue
        else:
            parts.append(f".{segment}" if parts else segment)
    return "".join(parts)


def _message(problem: ErrorDetails) -> str:
    if problem["type"] == "union_tag_not_found":
        return (
            "a Demand must be either an Axis constraint "
            '({"axis": ..., "op": ..., "value": ...}) or free text ({"text": ...})'
        )
    message = problem["msg"]
    return message.removeprefix("Value error, ")
