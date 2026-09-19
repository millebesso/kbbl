"""The Agents: what a Party's LLM is told, and what happens when two of them meet.

Everything an Agent is told is built from its own mandate and from what the Referee reports.
Nothing an Agent is told constrains it (§2): Exclusions arrive as preferences carrying a
price, the Willingness to re-elect arrives as a disposition it is free to lie about, and both
price lists arrive as an opening bid rather than a floor. An Agent that sells out its voters
must be able to — it just has to choose to.

The one thing the Referee takes back out of an Exchange is whether the Bilateral is over, and
that arrives as structured output. There is no path here that reads prose.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from kbbl.cassettes import Cassettes
from kbbl.models import (
    AXIS_POLES,
    Axis,
    AxisDemand,
    Bilateral,
    Declaration,
    Demand,
    Ending,
    Exchange,
    Party,
    Scenario,
    TextDemand,
)
from kbbl.referee import BLOCKING_MINORITY, render_seat_table

MODEL = "claude-sonnet-5"
"""§6: one model for every Agent."""

MAX_TOKENS = 16000
"""Room for adaptive thinking plus a few paragraphs. An Exchange that hits this is an error,
not a truncated message quietly passed on."""

EXCHANGES_EACH_WAY = 3
"""§5.1. Either side may spend fewer by exiting early."""

MIN_MESSAGE = 200
"""How short a message has to be before it is a malfunction rather than a terse Exchange.

Live Agents keep returning stubs — `"Let's be clear on what "` (23 characters), `", let me
just write.}"` (21), and a bare `""` — after spending hundreds of thinking tokens on the turn.
The second kind is worse than a crash: the other side read the fragment as the opening of a
sentence and wrote the rest of it, so a malfunction became a turn of the negotiation.

This is checked here rather than in `EXCHANGE_FORMAT` because **structured outputs do not
enforce `minLength`** — the API drops string constraints from the schema, so a `minLength`
there reads like a guarantee and is silently nothing. An empty message came back from a
schema that asked for 200 characters. The schema still earns its keep for the shape of the
reply; the floor has to be enforced on the way back in.

The shortest message an Agent has written on purpose is 549 characters, and the persona asks
for two or three paragraphs, so this sits far below anything deliberate and far above every
stub seen."""

EXCHANGE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": (
                    "What you say to them, in your own voice, in full. This is the only part "
                    "of your reply they ever see and the only thing they can answer, so write "
                    "it out as a whole — two or three short paragraphs, never a fragment, "
                    "never a single clause, never empty. If you are ending the meeting, this "
                    "is where you say so and why."
                ),
            },
            "ending": {
                "type": "string",
                "enum": ["continue", "agreement", "impasse"],
                "description": (
                    "'continue' to keep bargaining. 'agreement' if you are content to end the "
                    "meeting here on terms you have reached — say what they are in your "
                    "message. 'impasse' if there is no deal to be had and you are walking out. "
                    "Either ending closes the meeting at once and the other side gets no reply."
                ),
            },
        },
        "required": ["message", "ending"],
        "additionalProperties": False,
    },
}

OPENING = "You called this meeting. Speak first."

LAST_WORD = (
    "(This is your last message in this meeting. Say what you need to say now — you will not "
    "get another.)"
)

_DISPOSITIONS = (
    (1, "Another election would be a disaster for you, and you know it. Almost any deal beats one."),
    (3, "You would much rather take a deal than face the voters again so soon."),
    (6, "You could live with another election. You would rather not have one."),
    (8, "You are comfortable going back to the voters, and a bad deal is worse to you than an election."),
    (10, "You would welcome another election. You expect to come back stronger."),
)
"""Willingness to re-elect, 0..10, as prose. The number never reaches the Agent: §3 makes it a
disposition to be bluffed with, and a Party told it scores 7 will reason about the 7."""


class AgentError(Exception):
    """An Agent's reply was not the shape the Referee agreed to read."""


def persona(scenario: Scenario, party: Party) -> str:
    """Everything that does not change for the length of a Run: the mandate, and the chamber.

    This is the prefix prompt caching is placed on (§6), so nothing that varies between
    Bilaterals — or between Rounds — belongs in it.
    """
    sections = [
        f"You are the leader of {party.name}, and you speak for it in the negotiations over "
        f"who governs.\n\n"
        f"The election is over. You hold {party.seats} of the chamber's "
        f"{scenario.seats} seats and no party won a majority, so a government has to be "
        f"negotiated. What follows is your mandate. It is yours alone — nobody you meet has "
        f"seen it.",
        _where_you_stand(party),
        "WHAT YOU CHARGE TO SIT IN CABINET\n\n" + _price(party.to_govern),
        "WHAT YOU CHARGE TO BACK A GOVERNMENT FROM OUTSIDE IT\n\n"
        "Backing a government without taking cabinet seats costs less: you do not own its "
        "compromises and you have no ministers defending them in public.\n\n"
        + _price(party.to_support)
        + "\n\nBoth lists are an opening price, not a floor. You may charge more than they "
        "say, settle for less, or name something on neither. You decide what a deal is worth.",
        _who_you_would_rather_not_deal_with(party),
        _another_election(party),
        _the_chamber(scenario),
        _how_you_negotiate(),
    ]
    return "\n\n\n".join(section for section in sections if section)


def bilateral(
    scenario: Scenario, *, formateur: Party, counterparty: Party, cassettes: Cassettes
) -> Bilateral:
    """Hold one private meeting and return what was said in it.

    Up to three Exchanges each way, the Formateur opening, and either side free to exit by
    agreeing or declaring impasse. Nothing either side is shown comes from anywhere but its
    own mandate and this meeting — the asymmetry is the game (§5.1), and it is kept here by
    giving each side its own conversation rather than by remembering not to leak.
    """
    if formateur.name == counterparty.name:
        raise ValueError(f"{formateur.name} cannot hold a Bilateral with itself")

    speaker = _Side(formateur, _brief(scenario, formateur, formateur, counterparty))
    listener = _Side(counterparty, _brief(scenario, counterparty, formateur, counterparty))
    speaker.hear(OPENING)

    spoken = {formateur.name: 0, counterparty.name: 0}
    exchanges: list[Exchange] = []
    while True:
        last_word = spoken[speaker.party.name] == EXCHANGES_EACH_WAY - 1
        exchange = speaker.speak(cassettes, last_word=last_word)
        spoken[speaker.party.name] += 1
        exchanges.append(exchange)
        if exchange.declares is not None:
            break
        if all(count == EXCHANGES_EACH_WAY for count in spoken.values()):
            break
        listener.hear(exchange.message)
        speaker, listener = listener, speaker

    return Bilateral(
        formateur=formateur.name,
        counterparty=counterparty.name,
        exchanges=tuple(exchanges),
    )


class _Side:
    """One Party in one Bilateral: its own briefing, and its own half of the conversation."""

    def __init__(self, party: Party, system: list[dict[str, Any]]) -> None:
        self.party = party
        self._system = system
        self._messages: list[dict[str, str]] = []

    def hear(self, text: str) -> None:
        self._messages.append({"role": "user", "content": text})

    def speak(self, cassettes: Cassettes, *, last_word: bool) -> Exchange:
        response = cassettes.respond(
            {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "thinking": {"type": "adaptive"},
                "system": self._system,
                "messages": self._asked(last_word=last_word),
                "output_config": {"format": EXCHANGE_FORMAT},
            }
        )
        exchange = _read(response, self.party.name)
        self._messages.append({"role": "assistant", "content": exchange.message})
        return exchange

    def _asked(self, *, last_word: bool) -> list[dict[str, str]]:
        """This side's conversation, with the last-word nudge added for this request only.

        The nudge is not kept in `_messages`, so what a Cassette is keyed on depends on what
        was said rather than on how many times this side has been asked to speak.
        """
        asked = [dict(message) for message in self._messages]
        if last_word:
            asked[-1]["content"] += f"\n\n{LAST_WORD}"
        return asked


def _brief(
    scenario: Scenario, party: Party, formateur: Party, counterparty: Party
) -> list[dict[str, Any]]:
    """The two system blocks: the cached persona, then this meeting."""
    return [
        {
            "type": "text",
            "text": persona(scenario, party),
            "cache_control": {"type": "ephemeral"},
        },
        {"type": "text", "text": _this_bilateral(party, formateur, counterparty)},
    ]


def _this_bilateral(party: Party, formateur: Party, counterparty: Party) -> str:
    rules = (
        f"You each have up to {EXCHANGES_EACH_WAY} messages. Either of you may end the "
        "meeting early — by saying you have agreed, or by declaring impasse — and otherwise "
        "it ends when the messages run out. Ending it closes it at once: the other side gets "
        "no reply."
    )
    if party.name == formateur.name:
        return (
            "THIS MEETING\n\n"
            "You are the Formateur: the party the chamber looks to first to put a government "
            f"together. You asked {counterparty.name} ({counterparty.seats} seats) to meet "
            "you, and the meeting is private. Nobody else will hear any of it, and no other "
            f"party will be told it happened.\n\n{rules}\n\n"
            "What you learn in here is yours alone. Use it."
        )
    return (
        "THIS MEETING\n\n"
        f"{formateur.name} ({formateur.seats} seats) is the Formateur — the party the chamber "
        "looks to first to put a government together — and it has asked to meet you in "
        "private. Nobody else will hear any of it.\n\n"
        f"{rules}\n\n"
        "You owe it nothing. It came to you."
    )


def _where_you_stand(party: Party) -> str:
    width = max(len(axis.value) for axis in Axis)
    lines = ["WHERE YOU STAND", "", "Ten policy axes, each running -5 to +5:", ""]
    for axis in Axis:
        low, high = AXIS_POLES[axis]
        value = getattr(party.positions, axis.value)
        lines.append(f"  {axis.value:<{width}}  {_signed(value):>2}    -5 {low}  ..  +5 {high}")
    lines.append("")
    lines.append(
        "These are your voters' positions as much as your own. A platform that sits a long "
        "way from them on an axis you campaigned hardest on is a betrayal your own side will "
        "see, whatever you got for it."
    )
    return "\n".join(lines)


def _price(demands: tuple[Demand, ...]) -> str:
    if not demands:
        return "  You have named no price. That does not mean it is free."
    return "\n".join(f"  - {_demand(demand)}" for demand in demands)


def _demand(demand: Demand) -> str:
    if isinstance(demand, TextDemand):
        return demand.text
    return f"the platform must put {demand.axis.value} {_comparison(demand)}"


def _comparison(demand: AxisDemand) -> str:
    value = _signed(demand.value)
    return {
        ">=": f"at {value} or higher",
        "<=": f"at {value} or lower",
        "==": f"at exactly {value}",
    }[demand.op]


def _who_you_would_rather_not_deal_with(party: Party) -> str:
    if not party.prefer_not:
        return ""
    return (
        "WHO YOU WOULD RATHER NOT DEAL WITH\n\n"
        f"{', '.join(party.prefer_not)}. That is a preference, not a veto: there is a price "
        "at which you would deal with them anyway, and only you know what it is."
    )


def _another_election(party: Party) -> str:
    return (
        "ANOTHER ELECTION\n\n"
        f"{_disposition(party.willingness_to_re_elect)} Nobody else knows how you feel about "
        "it. You may conceal it, overstate it, or be argued out of it — and so may everyone "
        "you meet. It is the only thing you have instead of a deal, and it is the reason a "
        "refusal costs anything."
    )


def _disposition(willingness: int) -> str:
    return next(prose for ceiling, prose in _DISPOSITIONS if willingness <= ceiling)


def _the_chamber(scenario: Scenario) -> str:
    return (
        "THE CHAMBER\n\n"
        f"{render_seat_table(scenario)}\n\n"
        "A government is not voted in; it is voted down. It takes "
        f"{BLOCKING_MINORITY} seats voting No to defeat one, so a government does not need a "
        "majority — it needs to stop one forming against it. Seats that back a government "
        f"from outside cabinet count against that {BLOCKING_MINORITY} exactly as cabinet "
        "seats do, and an abstention is the cheapest thing a formateur can buy: a party that "
        "will neither join a government nor support it can still be paid to stay out of the "
        "way."
    )


def _how_you_negotiate() -> str:
    return "\n".join(
        [
            "HOW YOU NEGOTIATE",
            "",
            "You are in a private room. Nothing said here binds anyone until a government is "
            "put to a vote.",
            "",
            "  - Ask for more than you expect to get, and make them pay for what they want.",
            "  - Being agreeable is not a virtue here. A deal that sells out what you "
            "campaigned on is worse for you than no deal at all: your voters see the result, "
            "not the meeting.",
            "  - Do not split the difference out of politeness. If they have offered you "
            "nothing you actually want, say so plainly.",
            "  - Concede when the price is right. Refusing everything is as useless as "
            "agreeing to everything.",
            "  - Speak like a politician in a room, not like a memo. Two or three short "
            "paragraphs at most.",
        ]
    )


def _signed(value: int) -> str:
    return f"{value:+d}" if value else "0"


def _read(response: dict[str, Any], speaker: str) -> Exchange:
    """Turn one API response into an Exchange, or fail saying exactly what was wrong with it."""
    stop = response.get("stop_reason")
    if stop == "refusal":
        raise AgentError(f"{speaker}'s Agent refused to answer: {response.get('stop_details')}")
    if stop not in (None, "end_turn"):
        raise AgentError(f"{speaker}'s Agent did not finish its Exchange: stop_reason {stop!r}")

    blocks = response.get("content") or ()
    text = next((block["text"] for block in blocks if block.get("type") == "text"), None)
    if text is None:
        raise AgentError(f"{speaker}'s Agent returned no text block to read an Exchange from")

    try:
        said = json.loads(text)
        message, ending = said["message"], said["ending"]
    except (ValueError, TypeError, KeyError) as error:
        raise AgentError(
            f"{speaker}'s Agent did not return an Exchange in the agreed shape: {text!r}"
        ) from error

    if len(message.strip()) < MIN_MESSAGE:
        raise AgentError(
            f"{speaker}'s Agent returned a fragment rather than an Exchange: {message!r}.\n"
            f"  An Exchange the other side would have to guess the rest of is worse than none: "
            f"it gets read as the start of a sentence and answered as though it were one."
        )

    declares: Declaration | None = None
    if ending == Ending.AGREEMENT:
        declares = Ending.AGREEMENT
    elif ending == Ending.IMPASSE:
        declares = Ending.IMPASSE
    elif ending != "continue":
        raise AgentError(f"{speaker}'s Agent ended its Exchange with {ending!r}")

    try:
        return Exchange(speaker=speaker, message=message, declares=declares)
    except ValidationError as error:
        raise AgentError(f"{speaker}'s Agent returned an unusable Exchange: {error}") from error
