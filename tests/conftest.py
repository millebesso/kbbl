"""Helpers for building Scenario directories, and for standing in for the model."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from kbbl.agents import MIN_MESSAGE
from kbbl.models import Axis, Platform, Run, Scenario
from kbbl.scenario import load_scenario

AXES = tuple(axis.value for axis in Axis)

REPO = Path(__file__).resolve().parents[1]

FIXTURES = REPO / "fixtures"

FOUR_PARTY = FIXTURES / "four-party"

COMMITTED_FIXTURES = sorted(path for path in FIXTURES.iterdir() if path.is_dir())
"""Every Fixture in the repo, found rather than listed: a Fixture added without the
invariants being run over it is the one that would have caught something."""

CASSETTES = REPO / "cassettes"
"""The committed recordings, so the whole suite replays for free."""


@pytest.fixture
def four_party() -> Scenario:
    """The committed four-Party Fixture, loaded through the one and only load path."""
    return load_scenario(FOUR_PARTY)


@pytest.fixture
def landslide() -> Scenario:
    """One Party above the Blocking minority: it governs, and nothing can stop it."""
    return load_scenario(FIXTURES / "landslide")


@pytest.fixture
def knife_edge() -> Scenario:
    """Two blocs and a kingmaker whose Abstention alone decides who governs."""
    return load_scenario(FIXTURES / "knife-edge")


@pytest.fixture
def deadlock() -> Scenario:
    """Three Parties whose prices cannot all be paid by any Platform."""
    return load_scenario(FIXTURES / "deadlock")


def positions(**overrides: int) -> dict[str, int]:
    """A neutral Position on every Axis, with named Axes overridden."""
    return {axis: 0 for axis in AXES} | overrides


def platform(**overrides: int) -> Platform:
    """A Platform at 0 on every Axis, with named Axes overridden."""
    return Platform(**positions(**overrides))


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


def responded(text: str, *, called: dict[str, Any] | None = None) -> dict[str, Any]:
    """A Messages API response, as a Cassette records it: prose, and at most one tool call."""
    content: list[dict[str, Any]] = [{"type": "text", "text": text}]
    if called is not None:
        content.append({"type": "tool_use", "id": "call", **called})
    return {
        "content": content,
        "stop_reason": "tool_use" if called is not None else "end_turn",
    }


def spoken(message: str, ending: str = "continue") -> dict[str, Any]:
    """One Exchange as an Agent returns it: prose, plus whether it ends the Bilateral.

    A scripted message is padded up to the floor the Referee enforces, so the stand-in obeys
    the same contract the model does and a test can still say what it means in one line. Use
    `said` to name what a scripted message becomes. Tests about the floor itself build their
    reply with `responded` instead.
    """
    ends = None if ending == "continue" else {"name": "end_meeting", "input": {"ending": ending}}
    return responded(said(message), called=ends)


def chose(party: str, reasoning: str = "They are the ones worth the round.") -> dict[str, Any]:
    """One Choice as a Formateur returns it: the reasoning in prose, the name in the call."""
    return responded(reasoning, called={"name": "meet", "input": {"party": party}})


def said(message: str) -> str:
    """What `spoken(message)` actually puts in the Agent's mouth, once padded to the floor."""
    if len(message) >= MIN_MESSAGE:
        return message
    padding = " (and here the leader says rather more about the price, at length.)"
    return message + padding * -(-(MIN_MESSAGE - len(message)) // len(padding))


class Model:
    """A stand-in for the live path. Hands back scripted replies and keeps every request.

    Two scripts, because a request asking whom to meet and a request asking what to say want
    different replies, and which one this is can be read off the tools offered. Positional
    replies answer the Exchanges; `chooses` answers the Rounds, as Party names for the usual
    case or whole replies for a test about a malformed one. The last reply of either script
    repeats, so a test that only cares about how a Bilateral ends does not have to script
    every Exchange leading up to it.

    Unscripted Exchanges are numbered rather than identical. A Run in which every Party says
    the same thing cannot show a leak between Bilaterals, and that is a thing tests here have
    to be able to see.
    """

    def __init__(
        self, *replies: dict[str, Any], chooses: Sequence[str | dict[str, Any]] = ()
    ) -> None:
        self.requests: list[dict[str, Any]] = []
        self._replies = list(replies)
        self._chooses = list(chooses)
        self._spoken = 0
        self._chosen = 0

    def __call__(self, request: Mapping[str, Any]) -> dict[str, Any]:
        self.requests.append(dict(request))
        if self._offers(request, "meet"):
            return self._choice(request)
        self._spoken += 1
        if not self._replies:
            return spoken(f"Message {self._spoken}, and nobody has said it before.")
        return self._replies[min(self._spoken - 1, len(self._replies) - 1)]

    def _choice(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """The Round's Choice: a scripted Party name, a whole scripted reply, or the first
        Party the Formateur was offered."""
        self._chosen += 1
        if not self._chooses:
            return self._books(self._can_meet(request)[0])
        scripted = self._chooses[min(self._chosen - 1, len(self._chooses) - 1)]
        return self._books(scripted) if isinstance(scripted, str) else scripted

    def _books(self, party: str) -> dict[str, Any]:
        return chose(party, f"Round {self._chosen}: {party} is the one worth the round.")

    @staticmethod
    def _offers(request: Mapping[str, Any], name: str) -> bool:
        """Requests built by hand in `test_cassettes.py` carry no tools at all, and are
        Exchanges as far as this stand-in is concerned."""
        return any(tool["name"] == name for tool in request.get("tools", ()))

    @staticmethod
    def _can_meet(request: Mapping[str, Any]) -> list[str]:
        tool = next(tool for tool in request["tools"] if tool["name"] == "meet")
        names: list[str] = tool["input_schema"]["properties"]["party"]["enum"]
        return names

    def system(self, index: int) -> str:
        """Everything the Agent behind request `index` was told before the conversation."""
        return briefing(self.requests[index])

    def said_to(self, index: int) -> list[str]:
        """Every message in the conversation behind request `index`, both sides of it."""
        return [str(message["content"]) for message in self.requests[index]["messages"]]


def briefing(request: Mapping[str, Any]) -> str:
    """Everything the Agent behind one request was told before its conversation began."""
    return "\n".join(block["text"] for block in request["system"])


def recorded_requests(directory: Path) -> list[dict[str, Any]]:
    """Every request in a drawer of Cassettes, read back off disk.

    A Cassette is the request that was actually sent, so a drawer of them is the one record
    of a Run that owes nothing to the code that is being checked.
    """
    return [
        json.loads(path.read_text(encoding="utf-8"))["request"]
        for path in sorted(directory.glob("*.json"))
    ]


def leaks(requests: Sequence[Mapping[str, Any]], run: Run) -> list[str]:
    """Everything a Party was shown that was said in a Bilateral it was not in.

    The asymmetry §5.1 calls the game is kept by what a Counterparty is never handed, so the
    only honest check is over what was actually sent: every request the Run made, read back
    against the record of who said what in which Bilateral. Reading the Transcript cannot
    show this, and neither can reading the code that builds the briefings.

    The Formateur's own requests are skipped — accumulating all of it is its half of the
    asymmetry. Anything sent to anyone else is a leak if the record says it was said
    somewhere else, which is what makes stale Cassettes in the drawer harmless here: a
    message belonging to no Bilateral in this Run is not evidence of anything.
    """
    said_in: dict[str, set[str]] = {}
    for spent in run.rounds:
        for exchange in spent.bilateral.exchanges:
            said_in.setdefault(exchange.message, set()).add(spent.counterparty)
    for spent in run.rounds:
        said_in.setdefault(spent.choice.reasoning, set())

    found: list[str] = []
    for request in requests:
        party = _whose(request, run)
        if party is None or party == run.formateur:
            continue
        for message in request["messages"]:
            elsewhere = said_in.get(str(message["content"]))
            if elsewhere is not None and party not in elsewhere:
                found.append(f"{party} was shown: {message['content']!r}")
    return found


def _whose(request: Mapping[str, Any], run: Run) -> str | None:
    """Which Party's conversation a request belongs to, read off its own persona."""
    system = briefing(request)
    names = {spent.counterparty for spent in run.rounds} | {run.formateur}
    return next((name for name in names if f"You are the leader of {name}," in system), None)
