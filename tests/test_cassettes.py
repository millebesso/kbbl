"""Record and replay. Every test here makes zero API calls — that is the point of the module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import Model, responded as reply
from kbbl.cassettes import CassetteMiss, Cassettes, key


def test_the_key_is_a_hash_of_the_request_not_of_its_key_order() -> None:
    assert key({"model": "m", "max_tokens": 8}) == key({"max_tokens": 8, "model": "m"})
    assert key({"model": "m"}) != key({"model": "n"})


def test_a_live_run_calls_the_model_and_writes_a_cassette(tmp_path: Path) -> None:
    model = Model(reply("hello"))

    response = Cassettes(tmp_path, live=model).respond({"model": "m"})

    assert response == reply("hello")
    assert len(model.requests) == 1
    recorded = json.loads((tmp_path / f"{key({'model': 'm'})}.json").read_text())
    assert recorded["request"] == {"model": "m"}
    assert recorded["response"] == reply("hello")


def test_replay_returns_the_recording_without_reaching_the_model(tmp_path: Path) -> None:
    live = Model(reply("hello"))
    Cassettes(tmp_path, live=live).respond({"model": "m"})

    replayed = Model(reply("never asked for"))
    response = Cassettes(tmp_path, replay=True, live=replayed).respond({"model": "m"})

    assert response == reply("hello")
    assert replayed.requests == []


def test_replay_of_an_unrecorded_request_names_the_key_and_the_directory(
    tmp_path: Path,
) -> None:
    """The usual cause is an edited prompt, so the message has to say more than 'not found'."""
    with pytest.raises(CassetteMiss) as miss:
        Cassettes(tmp_path, replay=True).respond({"model": "m"})

    message = str(miss.value)
    assert key({"model": "m"}) in message
    assert str(tmp_path) in message


def test_a_live_run_is_live_even_where_a_cassette_already_exists(tmp_path: Path) -> None:
    """`--replay` opts out of the model (§11.5); recording is not a cache in front of it."""
    Cassettes(tmp_path, live=Model(reply("first"))).respond({"model": "m"})

    again = Model(reply("second"))
    assert Cassettes(tmp_path, live=again).respond({"model": "m"}) == reply("second")
    assert len(again.requests) == 1


def test_the_directory_is_created_on_the_first_recording(tmp_path: Path) -> None:
    Cassettes(tmp_path / "absent" / "deeper", live=Model()).respond({"model": "m"})

    assert list((tmp_path / "absent" / "deeper").glob("*.json"))


def test_replaying_a_directory_that_does_not_exist_is_a_miss_not_a_crash(
    tmp_path: Path,
) -> None:
    with pytest.raises(CassetteMiss):
        Cassettes(tmp_path / "absent", replay=True).respond({"model": "m"})


def test_a_request_with_non_ascii_text_round_trips(tmp_path: Path) -> None:
    """Party mandates and Transcripts are Swedish-adjacent; hashing must not mangle them."""
    request = {"model": "m", "messages": [{"role": "user", "content": "Miljöpartiet"}]}
    cassettes = Cassettes(tmp_path, live=Model(reply("Vänsterpartiet")))

    cassettes.respond(request)

    assert Cassettes(tmp_path, replay=True).respond(request) == reply("Vänsterpartiet")
