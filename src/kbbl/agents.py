"""The Agents: what a Party's LLM is told, and what happens when two of them meet.

Everything an Agent is told is built from its own mandate and from what the Referee reports.
Nothing an Agent is told constrains it (§2): Exclusions arrive as preferences carrying a
price, the Willingness to re-elect arrives as a disposition it is free to lie about, and both
price lists arrive as an opening bid rather than a floor. An Agent that sells out its voters
must be able to — it just has to choose to.

The two things the Referee takes back out of an Agent are whom the Formateur will spend a
Round on, and whether a Bilateral is over. Both arrive as tool calls carrying one enumerated
field. There is no path here that reads prose.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from kbbl.cassettes import Cassettes, Response
from kbbl.models import (
    AXIS_POLES,
    Axis,
    AxisDemand,
    Bilateral,
    Choice,
    Declaration,
    Demand,
    Ending,
    Exchange,
    Party,
    Round,
    Scenario,
    TextDemand,
    signed,
)
from kbbl.referee import BLOCKING_MINORITY, ROUNDS, render_seat_table

MODEL = "claude-sonnet-5"
"""§6: one model for every Agent."""

MAX_TOKENS = 16000
"""Room for adaptive thinking plus a few paragraphs. An Exchange that hits this is an error,
not a truncated message quietly passed on."""

EXCHANGES_EACH_WAY = 3
"""§5.1. Either side may spend fewer by exiting early."""

MIN_MESSAGE = 200
"""How short a message has to be before it is a malfunction rather than a terse Exchange.

Live Agents kept returning stubs — `"Let's be clear on what "` (23 characters), `", let me
just write.}"` (21), and a bare `""` — after spending hundreds of thinking tokens on the turn.
The second kind is worse than a crash: the other side read the fragment as the opening of a
sentence and wrote the rest of it, so a malfunction became a turn of the negotiation.

Every one of those came back while the message was being decoded *inside a JSON string*, which
is the shape ticket 02 recorded as unsafe and this ticket removed: prose is now the reply's
ordinary text and only the enumerated fields go through a tool call. The floor stays anyway.
It costs nothing, the failure it catches is silent rather than loud, and a run of clean
Exchanges is not evidence that the decoder cannot slip again.

The shortest message an Agent has written on purpose is 549 characters, and the persona asks
for two or three paragraphs, so this sits far below anything deliberate and far above every
stub seen."""

MEET = "meet"
"""The tool a Formateur books a Round's Bilateral with.

Named once because `_read_choice` has to recognise exactly what `_meet_tool` emitted, and a
tool name spelled twice is a tool name that can be spelled two ways."""

END_MEETING: dict[str, Any] = {
    "name": "end_meeting",
    "description": (
        "End this meeting now. Call it in the same reply as the message that says so, and "
        "say in that message why. 'agreement' if you are content to stop here on terms you "
        "have reached; 'impasse' if there is no deal to be had and you are walking out. "
        "Either one closes the meeting at once and the other side gets no reply, so do not "
        "call it while you still want to bargain."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ending": {"type": "string", "enum": [Ending.AGREEMENT.value, Ending.IMPASSE.value]}
        },
        "required": ["ending"],
        "additionalProperties": False,
    },
    "strict": True,
}
"""How a side ends a Bilateral early.

Optional on every Exchange: a side that says nothing here is still bargaining. What the tool
buys is that the Ending is read from an enumerated field rather than out of the message —
`_read_exchange` never looks at the prose, so an Agent that writes "we are done here" and
means to keep talking has not accidentally ended anything (§2).
"""

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


class FormateurAgent:
    """The Formateur's Agent for the length of an Attempt: it chooses, it meets, it remembers.

    Named for the Agent rather than the Party, because `CONTEXT.md` gives *Formateur* to the
    Party itself — this is the LLM instance negotiating on its behalf, which is what that
    glossary calls an Agent.

    One conversation runs the whole Attempt, so what it heard in Round 1 is still in front of
    it in Round 5. That accumulation is half of §5.1's asymmetry, and it is had by never
    starting the Formateur a second conversation rather than by summarising anything back to
    it: what it carries forward is what was actually said.

    The other half is kept by every Counterparty getting a conversation of its own, built from
    its own mandate and this meeting alone. A Counterparty is not told the other Bilaterals
    happened, which is a thing it is never *given* rather than a thing it is told — the leak
    to guard against is a line of code handing it one, not a sentence forgetting to.
    """

    def __init__(self, scenario: Scenario, party: Party) -> None:
        self.scenario = scenario
        self.party = party
        self.others = tuple(other for other in scenario.parties if other.name != party.name)
        if not self.others:
            raise ValueError(
                f"{party.name} is the only Party in Scenario {scenario.name!r}, so it has "
                f"nobody to meet"
            )
        self._side = _Side(party, _brief(persona(scenario, party), _your_attempt(self.others)))
        self._spent: list[str] = []
        self._rooms: dict[str, _Side] = {}

    def spend(self, cassettes: Cassettes) -> Round:
        """Spend one Round: choose a Party, say why, and hold the Bilateral that buys."""
        number = len(self._spent) + 1
        choice = self._choose(cassettes)
        met = self.meet(self.scenario.party(choice.counterparty), cassettes)
        return Round(number=number, choice=choice, bilateral=met)

    def meet(self, counterparty: Party, cassettes: Cassettes) -> Bilateral:
        """Hold one private meeting and return what was said in it.

        Up to three Exchanges each way, the Formateur opening, and either side free to exit by
        agreeing or declaring impasse.
        """
        if counterparty.name == self.party.name:
            raise ValueError(f"{self.party.name} cannot hold a Bilateral with itself")

        other = self._room(counterparty)
        self._side.hear(_in_the_room(counterparty, len(self._spent) + 1, self._spent))

        speaker, listener = self._side, other
        spoken = {self.party.name: 0, counterparty.name: 0}
        exchanges: list[Exchange] = []
        while True:
            last_word = spoken[speaker.party.name] == EXCHANGES_EACH_WAY - 1
            exchange = speaker.exchange(cassettes, last_word=last_word)
            spoken[speaker.party.name] += 1
            exchanges.append(exchange)
            # Including the closing one. A side that declares gets no *reply*, which is not
            # the same as the other side never having been told: the Formateur carries this
            # meeting into its next Round, and one missing its last word is carried wrong.
            listener.hear(exchange.message)
            if exchange.declares is not None:
                break
            if all(count == EXCHANGES_EACH_WAY for count in spoken.values()):
                break
            speaker, listener = listener, speaker

        met = Bilateral(
            formateur=self.party.name,
            counterparty=counterparty.name,
            exchanges=tuple(exchanges),
        )
        self._spent.append(counterparty.name)
        self._side.hear(_that_meeting_is_over(met))
        return met

    def _room(self, counterparty: Party) -> _Side:
        """The conversation this Party is in — the one it was already in, if it has been met.

        A Party met twice is owed its own first meeting. `CONTEXT.md` gives a Counterparty
        "only what happened in its own", and an earlier Bilateral with this same Formateur is
        its own: a Formateur that says "as we agreed last time" to a Party holding no memory
        of last time is talking to somebody who cannot answer it. What stays out of this room
        is every meeting with somebody else.
        """
        other = self._rooms.get(counterparty.name)
        if other is not None:
            other.hear(_meeting_again(self.party))
            return other
        other = _Side(
            counterparty,
            _brief(
                persona(self.scenario, counterparty),
                _their_bilateral(self.party, counterparty),
            ),
        )
        self._rooms[counterparty.name] = other
        return other

    def _choose(self, cassettes: Cassettes) -> Choice:
        """Which Party to spend this Round on, and the reasoning given before the meeting."""
        self._side.hear(_which_round(self._spent, self.others))
        response = self._side.reply(cassettes, tools=[_meet_tool(self.others)])
        choice = _read_choice(response, self.party.name, self.others)
        self._side.spoke(choice.reasoning)
        return choice


class _Side:
    """One Party in one conversation: its own briefing, and its own half of what was said."""

    def __init__(self, party: Party, system: list[dict[str, Any]]) -> None:
        self.party = party
        self._system = system
        self._messages: list[dict[str, str]] = []

    def hear(self, text: str) -> None:
        """Add to what this side has been told since it last spoke.

        Two things said to a side before it answers are one turn, not two — the Formateur
        hears a meeting close and the next Round open without speaking in between, and a
        conversation whose roles stop alternating is one the API will not take.
        """
        if self._messages and self._messages[-1]["role"] == "user":
            self._messages[-1]["content"] += f"\n\n{text}"
        else:
            self._messages.append({"role": "user", "content": text})

    def spoke(self, text: str) -> None:
        self._messages.append({"role": "assistant", "content": text})

    def exchange(self, cassettes: Cassettes, *, last_word: bool) -> Exchange:
        """One message in a Bilateral, and whether it closes the meeting."""
        response = self.reply(
            cassettes, tools=[END_MEETING], nudge=LAST_WORD if last_word else None
        )
        exchange = _read_exchange(response, self.party.name)
        self.spoke(exchange.message)
        return exchange

    def reply(
        self, cassettes: Cassettes, *, tools: list[dict[str, Any]], nudge: str | None = None
    ) -> Response:
        """Ask this side to speak. `nudge` is added to this request only.

        Keeping the nudge out of `_messages` is what makes a Cassette's key depend on what was
        said rather than on how many times this side has been asked to speak.
        """
        asked = [dict(message) for message in self._messages]
        if nudge is not None:
            asked[-1]["content"] += f"\n\n{nudge}"
        return cassettes.respond(
            {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "thinking": {"type": "adaptive"},
                "system": self._system,
                "messages": asked,
                "tools": tools,
            }
        )


def _brief(persona_text: str, second: str) -> list[dict[str, Any]]:
    """The two system blocks: the cached persona, then what this Agent is doing.

    The cache breakpoint sits between them (§6), so the second block is where anything that
    changes belongs. For a Counterparty that is the meeting it has been called to; for the
    Formateur it is the Attempt, which is stable for the whole of it — what the Formateur has
    learned accumulates in the conversation instead, and so costs the cached prefix nothing.
    """
    return [
        {"type": "text", "text": persona_text, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": second},
    ]


def _meet_tool(others: tuple[Party, ...]) -> dict[str, Any]:
    """Booking a Round's Bilateral: one Party, named from the ones there are.

    The enum is the Referee reporting procedure, not constraining judgement (§2) — whom to
    court is entirely the Formateur's, but it has to be somebody in this chamber, and a name
    the Referee has to guess at is a name it would be parsing out of prose.
    """
    return {
        "name": MEET,
        "description": (
            "Book this round's meeting with one party. Call it once, in the same reply as "
            "the reasoning you give for choosing them. The reasoning is for the record; this "
            "call is what books the room."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "party": {"type": "string", "enum": [party.name for party in others]}
            },
            "required": ["party"],
            "additionalProperties": False,
        },
        "strict": True,
    }


def _your_attempt(others: tuple[Party, ...]) -> str:
    """The Formateur's standing brief: the budget, and what spending it badly costs."""
    return (
        "YOUR ATTEMPT\n\n"
        "You are the Formateur: the party the chamber looks to first to put a government "
        f"together. You have {ROUNDS} rounds, and each one buys you a single private meeting "
        f"with a single party. {_what_the_budget_buys(len(others))} Deciding whom to court, "
        "whom to court twice, and whom to leave out entirely is the most consequential thing "
        "you do here — a formateur who spends the budget badly does not get a government.\n\n"
        "You may spend two rounds on the same party if a second conversation with them is "
        "worth more to you than a first with somebody else; they will remember the first "
        "one.\n\n"
        "Every meeting is private and each one is separate. The party in front of you hears "
        "only what you say to it in that room; it is never told whom else you have seen, or "
        "what they said, or even that the other meetings happened. You are the only one who "
        "sees all of it. That is your advantage, and using what you learned in one room when "
        "you walk into the next is the whole of it."
    )


def _what_the_budget_buys(others: int) -> str:
    """Whether the budget stretches to the whole chamber, said truthfully of this one.

    §5.1 has eight Parties and five Rounds, where the budget plainly does not reach. The
    Fixtures are smaller and it plainly does, and telling a Formateur it cannot see everybody
    when it can is the Referee reporting something false about its own procedure (§2).
    """
    if others > ROUNDS:
        return (
            f"There are {others} other parties in the chamber and only {ROUNDS} rounds, so "
            f"you cannot see them all: some party will go uncourted."
        )
    return (
        f"There are {others} other parties in the chamber, so you could see each of them "
        f"once and have rounds to spare — which makes how you spend the spare ones, and "
        f"whether anyone is worth none at all, the thing to decide."
    )


def _which_round(spent: list[str], others: tuple[Party, ...]) -> str:
    """The prompt that opens a Round: the budget so far, and the choice to make."""
    number = len(spent) + 1
    width = max(len(party.name) for party in others)
    chamber = "\n".join(
        f"  {party.name:<{width}}  {party.seats:>3} seats" for party in others
    )
    left = ROUNDS - number
    lines = [
        f"ROUND {number} OF {ROUNDS}.",
        "",
        "Parties you can meet:",
        "",
        chamber,
        "",
    ]
    if spent:
        lines.append(f"Spent so far: {_so_far(spent)}.")
    lines.append(_what_is_left(left))
    lines.extend(
        [
            "",
            "Who do you meet, and why? Say it in your own words — a short paragraph is "
            "enough — and call `meet` in the same reply to book the room.",
        ]
    )
    return "\n".join(lines)


def _what_is_left(left: int) -> str:
    """How much budget remains after this Round. The Referee's to report, and it changes
    what a Round is worth spending on."""
    if not left:
        return "This is your last round."
    if left == 1:
        return "One round is left after this one."
    return f"{left} rounds are left after this one."


def _so_far(spent: list[str]) -> str:
    """The Rounds already spent, named one by one. A Formateur that has met a Party twice
    should be able to see that it did without counting back through the conversation."""
    return ", ".join(f"round {number} on {name}" for number, name in enumerate(spent, start=1))


def _in_the_room(counterparty: Party, number: int, spent: list[str]) -> str:
    """What the Formateur is told as a meeting opens. Its side of the asymmetry, stated."""
    before = [
        str(round_number)
        for round_number, name in enumerate(spent, start=1)
        if name == counterparty.name
    ]
    again = (
        f" You have met it before, in round {' and '.join(before)}, and it remembers that "
        f"meeting as well as you do."
        if before
        else ""
    )
    return (
        f"You are now in the room with {counterparty.name} ({counterparty.seats} seats). "
        f"This is round {number}.{again}\n\n"
        f"{counterparty.name} has heard none of your other meetings and will not be told this "
        f"one is one of several. What it knows is what you have told it in this room.\n\n"
        f"{_the_rules()}\n\nSpeak first."
    )


def _meeting_again(formateur: Party) -> str:
    """What a Counterparty is told when the Formateur spends a second Round on it."""
    return (
        f"That meeting ended there. Time has passed, and {formateur.name} has asked to see "
        f"you again. You know what was said between the two of you last time and nothing "
        f"else — who else it has seen since, and what they said, it has not told you."
    )


def _their_bilateral(formateur: Party, counterparty: Party) -> str:
    """A Counterparty's second system block: this meeting, and nothing outside it."""
    return (
        "THIS MEETING\n\n"
        f"{formateur.name} ({formateur.seats} seats) is the Formateur — the party the chamber "
        "looks to first to put a government together — and it has asked to meet you in "
        f"private. Nobody else will hear any of it.\n\n{_the_rules()}\n\n"
        "You owe it nothing. It came to you."
    )


def _the_rules() -> str:
    """What both sides are told about how a Bilateral runs. Identical prose for each of them:
    the asymmetry is in what they know, never in what they are told the rules are."""
    return (
        f"You each have up to {EXCHANGES_EACH_WAY} messages. Write yours as an ordinary "
        "reply, in your own voice. Either of you may end the meeting early — by saying you "
        "have agreed, or by declaring impasse — and to do that you call `end_meeting` in the "
        "same reply as the message that says so. Ending it closes it at once: the other side "
        "gets no reply. Otherwise it ends when the messages run out."
    )


def _that_meeting_is_over(met: Bilateral) -> str:
    """What the Formateur is told once a Bilateral closes, before it chooses again."""
    if met.ending is Ending.EXHAUSTED:
        how = "the messages ran out with neither of you agreeing or declaring impasse"
    else:
        who = "you" if met.closed_by == met.formateur else met.counterparty
        verb = "agreed" if met.ending is Ending.AGREEMENT else "declared impasse"
        how = f"{who} {verb}"
    return f"The meeting with {met.counterparty} is over: {how}."


def _where_you_stand(party: Party) -> str:
    width = max(len(axis.value) for axis in Axis)
    lines = ["WHERE YOU STAND", "", "Ten policy axes, each running -5 to +5:", ""]
    for axis in Axis:
        low, high = AXIS_POLES[axis]
        value = party.positions.on(axis)
        lines.append(f"  {axis.value:<{width}}  {signed(value):>2}    -5 {low}  ..  +5 {high}")
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
    value = signed(demand.value)
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


def _read_exchange(response: Response, speaker: str) -> Exchange:
    """Turn one API response into an Exchange, or fail saying what was wrong with it."""
    message = _prose(response, speaker, "an Exchange")
    if len(message.strip()) < MIN_MESSAGE:
        raise AgentError(
            f"{speaker}'s Agent returned a fragment rather than an Exchange: {message!r}.\n"
            f"  An Exchange the other side would have to guess the rest of is worse than none: "
            f"it gets read as the start of a sentence and answered as though it were one."
        )

    given = _tool_call(response, speaker, expected=END_MEETING["name"])
    declares = None if given is None else _declaration(given.get("ending"), speaker)

    try:
        return Exchange(speaker=speaker, message=message, declares=declares)
    except ValidationError as error:
        raise AgentError(f"{speaker}'s Agent returned an unusable Exchange: {error}") from error


def _declaration(ending: Any, speaker: str) -> Declaration:
    """Which Ending a side declared. Exhaustion is never declared, so it is never one of
    these: it is what is left when nobody declares anything."""
    if ending == Ending.AGREEMENT:
        return Ending.AGREEMENT
    if ending == Ending.IMPASSE:
        return Ending.IMPASSE
    raise AgentError(f"{speaker}'s Agent ended the Bilateral with {ending!r}")


def _read_choice(response: Response, speaker: str, others: tuple[Party, ...]) -> Choice:
    """Turn one API response into a Choice: the booked Party, and the reasoning beside it.

    No floor on the reasoning. The fragment `MIN_MESSAGE` exists for is a fragment somebody
    *answers* — a reasoning is read by nobody in the Run, so a short one is terse rather than
    dangerous, and an empty one is already refused by `Choice`.
    """
    reasoning = _prose(response, speaker, "its reasoning")
    given = _tool_call(response, speaker, expected=MEET)
    if given is None:
        raise AgentError(
            f"{speaker}'s Agent gave its reasoning without booking a meeting: {reasoning!r}.\n"
            f"  Whom to meet is read from the `{MEET}` call and nowhere else, so a Round that "
            f"names a Party only in prose has chosen nobody."
        )

    chosen = given.get("party")
    if chosen not in [party.name for party in others]:
        raise AgentError(
            f"{speaker}'s Agent chose to meet {chosen!r}, which is not a Party it can meet"
        )

    try:
        return Choice(counterparty=chosen, reasoning=reasoning)
    except ValidationError as error:
        raise AgentError(f"{speaker}'s Agent returned an unusable Choice: {error}") from error


def _prose(response: Response, speaker: str, wanted: str) -> str:
    """The reply's ordinary text — the only place any prose in KBBL comes from.

    Ticket 02 recorded what happens when prose is decoded inside a constrained field instead:
    empty strings, truncated stubs and leaked JSON, in roughly one live call in eleven.
    """
    stop = response.get("stop_reason")
    if stop == "refusal":
        raise AgentError(f"{speaker}'s Agent refused to answer: {response.get('stop_details')}")
    if stop not in (None, "end_turn", "tool_use"):
        raise AgentError(f"{speaker}'s Agent did not finish speaking: stop_reason {stop!r}")

    blocks = response.get("content") or ()
    text = next((block["text"] for block in blocks if block.get("type") == "text"), None)
    if text is None:
        raise AgentError(f"{speaker}'s Agent returned no text block to read {wanted} from")
    return str(text)


def _tool_call(response: Response, speaker: str, *, expected: str) -> dict[str, Any] | None:
    """What a reply called `expected` with, or None if it called nothing.

    An Agent is offered exactly one tool at a time, so anything else in a reply is a reply
    nobody agreed to read: two calls, or a call by a name that was never on offer.
    """
    blocks = response.get("content") or ()
    calls = [block for block in blocks if block.get("type") == "tool_use"]
    if not calls:
        return None
    if len(calls) > 1:
        names = ", ".join(str(call.get("name")) for call in calls)
        raise AgentError(f"{speaker}'s Agent made more than one call in one reply: {names}")

    call = calls[0]
    if call.get("name") != expected:
        raise AgentError(
            f"{speaker}'s Agent called {call.get('name')!r}, which is not a tool it has"
        )
    given = call.get("input")
    if not isinstance(given, dict):
        raise AgentError(f"{speaker}'s Agent called {expected!r} with {given!r}")
    return given
