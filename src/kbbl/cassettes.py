"""Record and replay: every request a Run makes, and the response it got back.

A Cassette is keyed by a hash of the request, so an unchanged request replays for free and a
changed one misses loudly. §8 pulls this forward to the first call that is ever made, because
retrofitting record/replay means re-plumbing every call site.

Live is the default and `--replay` opts out (§11.5). Live always calls: a recording is a
record of what happened, not a cache sitting in front of the model.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from functools import cache
from pathlib import Path
from typing import Any

import anthropic

Request = Mapping[str, Any]
"""The keyword arguments of one Messages API call — the thing that gets hashed."""

Response = dict[str, Any]
"""One response, as plain JSON. Replay and live hand back the same shape, so nothing
downstream can tell which path it came from."""

Live = Callable[[Request], Response]
"""How to reach the model when the Run is live."""


class CassetteMiss(Exception):
    """`--replay` was asked for a request that was never recorded."""


def key(request: Request) -> str:
    """A Cassette's name: a hash of the request, canonically serialised.

    Canonical means key order cannot change the name — two spellings of the same request are
    the same request. Everything else about it can, and should: editing a prompt is supposed
    to miss rather than quietly replay the old one.
    """
    canonical = json.dumps(request, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class Cassettes:
    """The recordings on disk, and the only way a Run reaches the model."""

    def __init__(
        self, directory: Path | str, *, replay: bool = False, live: Live | None = None
    ) -> None:
        self.directory = Path(directory)
        self.replay = replay
        self._live = live if live is not None else call_the_model

    def respond(self, request: Request) -> Response:
        """The response to `request` — replayed if recorded, called and recorded if not."""
        name = key(request)
        if self.replay:
            return self._read(name) or _miss(name, self.directory)
        response = self._live(request)
        self._write(name, request, response)
        return response

    def _path(self, name: str) -> Path:
        return self.directory / f"{name}.json"

    def _read(self, name: str) -> Response | None:
        path = self._path(name)
        if not path.is_file():
            return None
        recorded = json.loads(path.read_text(encoding="utf-8"))
        response: Response = recorded["response"]
        return response

    def _write(self, name: str, request: Request, response: Response) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        self._path(name).write_text(
            json.dumps(
                {"key": name, "request": request, "response": response},
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )


def _miss(name: str, directory: Path) -> Response:
    raise CassetteMiss(
        f"no Cassette {name} in {directory}.\n"
        f"  --replay only replays requests that were recorded exactly as they are now, so "
        f"an edited persona, briefing or model is a miss.\n"
        f"  Drop --replay to record this request live."
    )


@cache
def _client() -> anthropic.Anthropic:
    """Built on first use, so a replayed Run needs no credentials at all."""
    return anthropic.Anthropic()


def call_the_model(request: Request) -> Response:
    """The live path: one call to the Messages API."""
    message = _client().messages.create(**request)
    return message.to_dict()
