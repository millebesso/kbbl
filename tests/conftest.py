"""Helpers for building Scenario directories, and for standing in for the model."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from kbbl.agents import MIN_MESSAGE
from kbbl.models import Axis, Scenario
from kbbl.scenario import load_scenario

AXES = tuple(axis.value for axis in Axis)

REPO = Path(__file__).resolve().parents[1]

FOUR_PARTY = REPO / "fixtures" / "four-party"

CASSETTES = REPO / "cassettes"
"""The committed recordings, so the whole suite replays for free."""


@pytest.fixture
def four_party() -> Scenario:
    """The committed four-Party Fixture, loaded through the one and only load path."""
    return load_scenario(FOUR_PARTY)


def positions(**overrides: int) -> dict[str, int]:
    """A neutral Position on every Axis, with named Axes overridden."""
    return {axis: 0 for axis in AXES} | overrides


def mandate(name: str, seats: int, **overrides: Any) -> dict[str, Any]:
    """A minimal valid mandate, with named fields overridden."""
    base: dict[str, Any] = {
        "name": name,
        "seats": seats,
        "positions": positions(),
        "prefer_not": [],
        "to_govern": [],
        "to_support": [],
        "willingness_to_re_elect": 5,
    }
    return base | overrides


def write_scenario(directory: Path, *mandates: dict[str, Any]) -> Path:
    """Write one JSON file per mandate into `directory`, as a Scenario would be laid out."""
    directory.mkdir(parents=True, exist_ok=True)
    for entry in mandates:
        name = entry.get("name", "unnamed")
        (directory / f"{name}.json").write_text(json.dumps(entry), encoding="utf-8")
    return directory


def two_party(directory: Path, **overrides: Any) -> Path:
    """A two-Party Scenario summing to 349, with fields of the first mandate overridden."""
    return write_scenario(directory, mandate("AA", 200) | overrides, mandate("BB", 149))


def responded(text: str) -> dict[str, Any]:
    """A Messages API response carrying one text block, as a Cassette records it."""
    return {"content": [{"type": "text", "text": text}], "stop_reason": "end_turn"}


def spoken(message: str, ending: str = "continue") -> dict[str, Any]:
    """One Exchange as an Agent returns it: prose, plus whether it ends the Bilateral.

    A scripted message is padded up to the floor the live schema enforces, so the stand-in
    obeys the same contract the model does and a test can still say what it means in one
    line. Use `said` to name what a scripted message becomes. Tests about the floor itself
    build their reply with `responded` instead.
    """
    return responded(json.dumps({"message": said(message), "ending": ending}))


def said(message: str) -> str:
    """What `spoken(message)` actually puts in the Agent's mouth, once padded to the floor."""
    if len(message) >= MIN_MESSAGE:
        return message
    padding = " (and here the leader says rather more about the price, at length.)"
    return message + padding * -(-(MIN_MESSAGE - len(message)) // len(padding))


class Model:
    """A stand-in for the live path. Hands back scripted replies and keeps every request.

    The last reply repeats, so a test that only cares about how a Bilateral ends does not
    have to script every Exchange leading up to it.
    """

    def __init__(self, *replies: dict[str, Any]) -> None:
        self.requests: list[dict[str, Any]] = []
        self._replies = list(replies) or [spoken("Nothing in particular.")]

    def __call__(self, request: Mapping[str, Any]) -> dict[str, Any]:
        self.requests.append(dict(request))
        return self._replies[min(len(self.requests) - 1, len(self._replies) - 1)]

    def system(self, index: int) -> str:
        """Everything the Agent behind request `index` was told before the conversation."""
        return "\n".join(block["text"] for block in self.requests[index]["system"])
