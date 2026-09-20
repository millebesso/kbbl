"""The Agents: what a Party's LLM is told, and what happens when two of them meet.

Everything an Agent is told is built from its own mandate and from what the Referee reports.
Nothing an Agent is told constrains it (§2): Exclusions arrive as preferences carrying a
price, the Willingness to re-elect arrives as a disposition it is free to lie about, and both
price lists arrive as an opening bid rather than a floor. An Agent that sells out its voters
must be able to — it just has to choose to.

What the Referee takes back out of an Agent is whom the Formateur will spend a Round on,
whether a Bilateral is over, what a Proposal says, and how each Party votes on it. Every one
of them arrives as a tool call whose every field is enumerated, with the prose beside it in
the reply's own text. There is no path here that reads prose.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from kbbl.cassettes import Cassettes, Request, Response, key
from kbbl.ledger import Ledger
from kbbl.models import (
    AXIS_POLES,
    Axis,
    AxisDemand,
    Ballot,
    Bilateral,
    Choice,
    Declaration,
    Demand,
    Ending,
    Exchange,
    ExclusionReport,
    GapReport,
    Judgement,
    Party,
    Platform,
    Proposal,
    Role,
    Round,
    Scenario,
    TextDemand,
    Usage,
    signed,
)
from kbbl.referee import (
    BLOCKING_MINORITY,
    ROUNDS,
    Price,
    exclusion_report,
    gap_report,
    price_report,
    render_exclusion_report,
    render_gap_report,
    render_price_report,
    render_proposal,
    render_seat_table,
)

MODEL = "claude-sonnet-5"
"""§6: one model for every Agent."""

MAX_TOKENS = 16000
"""Room for adaptive thinking plus a few paragraphs. An Exchange that hits this is an error,
not a truncated message quietly passed on."""

EXCHANGES_EACH_WAY = 3
"""§5.1. Either side may spend fewer by exiting early."""

WORDS = 40
"""About how long one Exchange should be, said to an Agent as a number of words.

Asked for "two or three short paragraphs", live Agents wrote a median of 80 words a message
and a Transcript nobody wants to read closely — which is the one thing §8 asks of a
Transcript. Asked for "three or four sentences" they wrote the same 80 words in longer
sentences, because a sentence has no length. A word count is the only version of this
instruction that has ever changed the output.

It is guidance, not a ceiling: nothing rejects a message for running over, because an Exchange
a few words long is the negotiation and an aborted Run over a word count would not be."""

MIN_MESSAGE = 60
"""How short a message has to be before it is a malfunction rather than a terse Exchange.

Live Agents kept returning stubs — `"Let's be clear on what "` (23 characters), `", let me
just write.}"` (21), and a bare `""` — after spending hundreds of thinking tokens on the turn.
The second kind is worse than a crash: the other side read the fragment as the opening of a
sentence and wrote the rest of it, so a malfunction became a turn of the negotiation.

**This is a stub-catcher, not a length policy.** It sat at 200 while the persona asked for two
or three paragraphs, which made it look like one. The persona now asks for three or four
sentences, and a leader who says "Not at +1. Make it +3 and we can talk, or we are done" has
said something deliberate and complete in 60-odd characters — a floor anywhere near prose
length would reject exactly the terseness the negotiation wants.

So it sits just above the stubs instead: nearly three times the longest one ever seen, and
below anything a Party might say on purpose.

Every stub came back while the message was being decoded *inside a JSON string*, the shape
ticket 02 recorded as unsafe and ticket 04 removed. The floor stays anyway. It costs nothing,
the failure it catches is silent rather than loud, and a run of clean Exchanges is not evidence
that a decoder cannot slip again."""

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

TABLE = "table"
"""The tool a Formateur tables its Proposal with."""

STAND_DOWN = "stand_down"
"""The tool a Formateur ends its Attempt with instead of tabling (§5.3)."""

BALLOT = "ballot"
"""The tool a Party casts its Ballot in the Vote with."""

STAND_DOWN_TOOL: dict[str, Any] = {
    "name": STAND_DOWN,
    "description": (
        "End your attempt without putting anything to the chamber. Call it in the same reply "
        "as the message that says why. There is no vote, and the government you did not "
        "form is somebody else's problem now. Call this instead of `table`, never as well."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "strict": True,
}
"""Standing down takes no argument, because it is the absence of a Proposal rather than a
kind of one. The reasons are prose in the same reply, and the Transcript is where they go."""

BALLOT_TOOL: dict[str, Any] = {
    "name": BALLOT,
    "description": (
        "Cast your party's vote on the proposal before the chamber. Call it once, in the "
        "same reply as what you say about it. 'Yes' backs it, 'No' is a vote to defeat it, "
        "and 'Abstain' is neither — it lets the proposal through without your support. Your "
        "seats all go the way you call it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"ballot": {"type": "string", "enum": [option.value for option in Ballot]}},
        "required": ["ballot"],
        "additionalProperties": False,
    },
    "strict": True,
}

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
    """The Formateur's Agent for the length of an Attempt: it chooses, meets, remembers, and
    at the end of its Rounds either tables a Proposal or Stands down.

    It also holds the Vote, which is the Chamber's decision rather than the Formateur's, and
    that is worth defending rather than glossing. What a Party votes on is the Proposal set
    against the meeting it had, so every Party has to answer in the room it bargained in — and
    the rooms are here, because privacy is kept by their never being anywhere else. Handing
    them to a second object would mean handing out the one thing §5.1 says must not travel.
    So the Vote is run from here and `put_to_the_chamber` says whose act each part of it is.

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

    def __init__(
        self, scenario: Scenario, party: Party, ledger: Ledger | None = None
    ) -> None:
        self.scenario = scenario
        self.party = party
        self.others = tuple(other for other in scenario.parties if other.name != party.name)
        if not self.others:
            raise ValueError(
                f"{party.name} is the only Party in Scenario {scenario.name!r}, so it has "
                f"nobody to meet"
            )
        # Taken from the caller when there is one, because the artifacts of a Run that
        # breaks are written by whoever is still standing after it, and that is never this
        # object. It is the only place a default Ledger is built.
        self.ledger = (
            ledger
            if ledger is not None
            else Ledger(scenario=scenario.name, formateur=party.name)
        )
        self._side = _Side(
            party, _brief(persona(scenario, party), _your_attempt(self.others)), self.ledger
        )
        self._spent: list[str] = []
        self._met: list[Bilateral] = []
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
        self.ledger.met(counterparty.name)
        self._side.hear(_in_the_room(counterparty, len(self._spent) + 1, self._spent))

        speaker, listener = self._side, other
        spoken = {self.party.name: 0, counterparty.name: 0}
        exchanges: list[Exchange] = []
        while True:
            last_word = spoken[speaker.party.name] == EXCHANGES_EACH_WAY - 1
            exchange = speaker.exchange(cassettes, last_word=last_word)
            spoken[speaker.party.name] += 1
            exchanges.append(exchange)
            self.ledger.said(exchange)
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
        self._met.append(met)
        self._side.hear(_that_meeting_is_over(met))
        return met

    def table(self, cassettes: Cassettes) -> tuple[Proposal | None, str]:
        """What the Rounds were for: a Proposal, or the Formateur Standing down (§5.3).

        Comes back with what the Formateur said doing it. A Stand down leaves no Proposal to
        read, so the prose is the whole record of why an Attempt ended — throwing it away
        would leave the Transcript with nothing to say about the outcome §5.3 exists for.

        Both outcomes end the Attempt, and they are not the same outcome. A Proposal voted
        down spends one of the Chamber's four Votes; Standing down spends none, which is the
        whole reason a Formateur that has found no government worth tabling is offered the
        choice rather than pushed into a doomed Proposal.

        Nothing here decides which. The Referee lays out both tools and reads whichever was
        called — a Formateur tabling a Proposal every Party it met has refused is making a
        judgement the Referee is not allowed to make for it (§2).
        """
        menu = self._commitments()
        self._side.hear(_time_to_table(self._met, menu))
        response = self._side.reply(
            cassettes, tools=[_table_tool(self.scenario, menu), STAND_DOWN_TOOL]
        )
        proposal, reasoning = _read_proposal(response, self.party.name, self.scenario, menu)
        self._side.spoke(reasoning)
        self.ledger.tabled(proposal, reasoning)
        return proposal, reasoning

    def put_to_the_chamber(
        self, proposal: Proposal, cassettes: Cassettes
    ) -> tuple[Judgement, ...]:
        """Every Party's Ballot on this Proposal, in chamber order, with what it said.

        Every Party votes, including the Formateur and including the Parties the Proposal
        never names — it is exactly those whose Abstention is the cheapest thing on offer
        (§5.2), so a Vote that only polled the Base would be counting the wrong chamber.

        **A Party votes in the room it bargained in.** Its own Bilateral is the thing it is
        being asked to judge the Proposal against, and a Party handed a fresh conversation
        would be deciding whether terms it has no memory of reaching were honoured. The
        asymmetry is untouched by that: what a Party carries into the Vote is still only its
        own meeting, and a Party the Formateur never courted arrives with none.
        """
        return tuple(self._judge(party, proposal, cassettes) for party in self.scenario.parties)

    def _judge(self, party: Party, proposal: Proposal, cassettes: Cassettes) -> Judgement:
        """One Party's Ballot, cast after it has been shown its own two reports (§5.4).

        Each report is computed once and both shown and recorded, so that what `run.json`
        says a Party was looking at is the very table it was handed rather than a second
        reckoning that happens to agree.

        A Party that would deal with anybody has no Exclusion report at all, and is handed
        None rather than an empty one — the section is then left out, the way its Persona
        leaves out the section it has nothing to put in.
        """
        side = self._side if party.name == self.party.name else self._voting_room(party)
        shown = gap_report(party, proposal.platform)
        self.ledger.shown(shown)
        standing = exclusion_report(party, proposal)
        if standing is not None:
            self.ledger.shown(standing)
        side.hear(_the_vote(self.scenario, proposal, party, shown, standing))
        response = side.reply(cassettes, tools=[BALLOT_TOOL])
        judgement = _read_judgement(response, party.name)
        side.spoke(judgement.reasoning)
        self.ledger.judged(judgement)
        return judgement

    def _voting_room(self, party: Party) -> _Side:
        """The conversation this Party votes in: its own Bilateral, or none at all.

        Not cached back into `_rooms`. A Party that votes has not been met, and a room put
        there would be reopened by `_room` as though it had been.
        """
        met = self._rooms.get(party.name)
        if met is not None:
            return met
        return _Side(
            party,
            _brief(persona(self.scenario, party), _never_courted(self.party)),
            self.ledger,
        )

    def _commitments(self) -> tuple[str, ...]:
        """The free-text Demands this Formateur may grant, in the order it came across them.

        A Commitment is a free-text Demand that has been granted (`CONTEXT.md`), so the ones
        a Proposal can carry are the ones somebody charges for — its own, and those of the
        Parties it spent a Round on. That the Referee reports another Party's price list here
        is the Referee reporting, which is its half of §2; scoping it to the Parties actually
        met is what keeps it tied to the budget, so a Formateur that courted nobody has
        nothing but its own to grant.

        The alternative was a free-text field, and that is the one thing ticket 02 measured
        and ticket 04 removed: a Commitment arriving as prose decoded inside a schema string
        can come back truncated, and a half-written side deal is a binding term nobody wrote.
        """
        courted = (self.scenario.party(name) for name in dict.fromkeys(self._spent))
        named: dict[str, None] = {}
        for party in (self.party, *courted):
            for demand in (*party.to_govern, *party.to_support):
                if isinstance(demand, TextDemand):
                    named[demand.text] = None
        return tuple(named)

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
            self.ledger,
        )
        self._rooms[counterparty.name] = other
        return other

    def _choose(self, cassettes: Cassettes) -> Choice:
        """Which Party to spend this Round on, and the reasoning given before the meeting."""
        self._side.hear(_which_round(self._spent, self.others))
        response = self._side.reply(cassettes, tools=[_meet_tool(self.others)])
        choice = _read_choice(response, self.party.name, self.others)
        self._side.spoke(choice.reasoning)
        self.ledger.chose(choice)
        return choice


class _Side:
    """One Party in one conversation: its own briefing, and its own half of what was said."""

    def __init__(self, party: Party, system: list[dict[str, Any]], ledger: Ledger) -> None:
        self.party = party
        self._system = system
        self._ledger = ledger
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
        request: Request = {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "thinking": {"type": "adaptive"},
            "system": self._system,
            "messages": asked,
            "tools": tools,
        }
        response = cassettes.respond(request)
        self._ledger.paid(_usage(response, party=self.party.name, cassette=key(request)))
        return response


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


def _table_tool(scenario: Scenario, commitments: tuple[str, ...]) -> dict[str, Any]:
    """Tabling a Proposal: ten enumerated Axis values, and Parties named from the chamber.

    Every leaf in here is an enum — the Axis values because they run -5..+5 and nothing else,
    the Party names because a Proposal naming somebody who holds no seat is a Proposal the
    Referee would have to guess at, and the Commitments because a free-text field is the one
    shape ticket 02 recorded as unsafe. The Formateur's reasons for all of it are prose in
    the same reply, where prose is safe (§2).

    `commitments` is left out entirely when nobody has named a free-text Demand, because an
    empty enum is a field with no value that satisfies it.
    """
    names = [party.name for party in scenario.parties]
    properties: dict[str, Any] = {
        "platform": {
            "type": "object",
            "description": "One agreed value on every axis, -5 to +5.",
            "properties": {
                axis.value: {"type": "integer", "enum": list(range(-5, 6))} for axis in Axis
            },
            "required": [axis.value for axis in Axis],
            "additionalProperties": False,
        },
        "government": {
            "type": "array",
            "description": "The parties taking cabinet seats. Name yourself if you govern.",
            "items": {"type": "string", "enum": names},
        },
        "support_only": {
            "type": "array",
            "description": (
                "The parties backing it from outside cabinet. Their seats count behind it "
                "exactly as cabinet seats do. Empty if there are none."
            ),
            "items": {"type": "string", "enum": names},
        },
    }
    if commitments:
        properties["commitments"] = {
            "type": "array",
            "description": (
                "The free-text terms the programme carries. Empty if it carries none."
            ),
            "items": {"type": "string", "enum": list(commitments)},
        }
    return {
        "name": TABLE,
        "description": (
            "Put your proposal to the chamber. Call it once, in the same reply as what you "
            "say about it. This ends your attempt: there is one proposal and the chamber "
            "votes on it. Call this or `stand_down`, never both."
        ),
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        },
        "strict": True,
    }


def _time_to_table(met: list[Bilateral], commitments: tuple[str, ...]) -> str:
    """What the Formateur is told when its budget runs out: table something, or stand down."""
    sections = [
        "YOUR ROUNDS ARE SPENT.\n\n"
        "This is what the budget bought:\n\n" + _rounds_in_full(met),
        "Now you either put a proposal to the chamber or stand down. Either one ends your "
        "attempt, and there is no second proposal.",
        "WHAT A PROPOSAL IS\n\n"
        "  - a platform: one agreed value on every one of the ten axes, -5 to +5;\n"
        "  - a government: the parties taking cabinet seats;\n"
        "  - support-only: the parties backing it from outside cabinet, whose seats count "
        "behind it exactly as cabinet seats do;\n"
        "  - commitments: the free-text terms the programme carries.\n\n"
        "There are no ministries in it. Who gets which department is no part of this "
        "negotiation and not yours to promise.",
        _commitments_on_offer(commitments),
        "NOBODY HAS AGREED TO ANYTHING\n\n"
        "Naming a party is your claim about who governs, not a promise it made you. A party "
        "you put in the government may vote the proposal down, and a party you leave out "
        "entirely may let it through — which is the cheapest thing you can be given, and you "
        "do not have to name anyone to be given it. The chamber rejects a proposal only if "
        f"{BLOCKING_MINORITY} seats vote No against it.",
        "OR YOU STAND DOWN\n\n"
        "If there is no government here worth putting to the chamber, stand down instead. "
        "Your attempt ends with no vote, and the chamber spends none of the four it has. "
        "That is a real option, not a forfeit — tabling something you expect to lose costs "
        "the chamber a vote and buys nobody anything.",
        f"Which is it, and why? About {2 * WORDS} words in your own words — this is one "
        f"message and it accounts for a whole government — then call `{TABLE}` or "
        f"`{STAND_DOWN}` in the same reply.",
    ]
    return "\n\n".join(section for section in sections if section)


def _rounds_in_full(met: list[Bilateral]) -> str:
    """Every Round spent and how its meeting finished, five meetings on from the first."""
    if not met:
        return "  nothing — you met nobody."
    return "\n".join(
        f"  round {number} on {bilateral.counterparty} — "
        f"{bilateral.ended_by(bilateral.formateur)}"
        for number, bilateral in enumerate(met, start=1)
    )


def _commitments_on_offer(commitments: tuple[str, ...]) -> str:
    """The free-text terms this Proposal could carry, named before the Formateur chooses."""
    if not commitments:
        return ""
    named = "\n".join(f"  - {commitment}" for commitment in commitments)
    return (
        "FREE-TEXT COMMITMENTS YOU CAN WRITE IN\n\n"
        f"{named}\n\n"
        "These are the free-text terms charged for by you and by the parties you met. "
        "Writing one in puts it in the government's programme; you are free to write in none "
        "of them. A demand on an axis is not here, because a platform pays that by itself."
    )


def _never_courted(formateur: Party) -> str:
    """The second system block of a Party the Formateur never met, shown at the Vote.

    It has no Bilateral to carry in, and that is the truth about it rather than an omission:
    it was not courted, and it still holds every seat it was elected with.
    """
    return (
        "THIS VOTE\n\n"
        f"{formateur.name} ({formateur.seats} seats) is the Formateur — the party the chamber "
        "looked to first to put a government together. It never came to see you. Whatever it "
        "agreed with anybody, it agreed without you in the room.\n\n"
        "You owe it nothing, and it has asked you for nothing."
    )


def _the_vote(
    scenario: Scenario,
    proposal: Proposal,
    party: Party,
    shown: GapReport,
    standing: ExclusionReport | None,
) -> str:
    """What one Party is shown before it votes: the Proposal, and its own reports.

    The Gap report is §5.4's whole defence and it goes in front of every Party, named or not.
    An Agent asked abstractly to hold its ground drifts; the same Agent shown the number it
    is abandoning on the Axis it campaigned hardest on does not — or does, knowingly, which
    is the most this design ever asks for.

    The Exclusion report beside it is the same argument about the other half of a Proposal.
    A Party whose Persona says it would rather not deal with V, voting on a Proposal that
    names V in its Government, had those two facts in front of it in two places and never in
    one sentence — and waved the government through. Nothing here stops it doing so again
    (§2); what it can no longer be is inattentive.

    Both arrive already computed because `run.json` keeps a copy of each (§7), and a report
    computed twice is two reports that could differ.
    """
    sections = [
        "THE VOTE\n\n"
        f"The bargaining is over. {proposal.formateur} has put a government to the chamber, "
        "and the chamber now decides whether to reject it.",
        render_proposal(scenario, proposal),
        "WHAT IT ASKS OF YOU\n\n" + _what_it_asks_of_you(proposal, party),
        "WHERE THIS PLATFORM LEAVES YOUR VOTERS\n\n"
        + render_gap_report(shown)
        + "\n\n  That is arithmetic, not advice. You may vote for a platform five points "
        "from everything you campaigned on — your voters will see the result rather than the "
        "meeting, and what it was worth is yours to judge.",
        _who_it_puts_you_beside(standing),
        _what_it_pays_of_your_price(proposal, party),
        _how_the_vote_works(party),
    ]
    return "\n\n".join(section for section in sections if section)


def _who_it_puts_you_beside(standing: ExclusionReport | None) -> str:
    """Where this Proposal puts the Parties this one would rather not deal with.

    Empty for a Party that named nobody, so the section drops out of the briefing entirely
    rather than announcing that there is nothing to say — the same silence
    `_who_you_would_rather_not_deal_with` keeps in the Persona.
    """
    if standing is None:
        return ""
    return (
        "WHERE IT PUTS THE PARTIES YOU WOULD RATHER NOT DEAL WITH\n\n"
        + render_exclusion_report(standing)
        + "\n\n  That is who would be in it, not advice. Those are preferences with a "
        "price, never vetoes: there is a figure at which you would sit beside any of them, "
        "and you may wave it through for nothing at all. Only you know whether this is it."
    )


_WHAT_EACH_ROLE_ASKS = {
    Role.GOVERNMENT: (
        "It puts you in the cabinet. You would own this platform in public, and your "
        "ministers would be the ones defending it."
    ),
    Role.SUPPORT_ONLY: (
        "It names you as backing the government from outside the cabinet. No seats at "
        "that table, and your seats counted behind it all the same."
    ),
    Role.UNNAMED: (
        "It does not name you at all. It asks you for nothing — not a cabinet seat, not your "
        "support — only that you are not among the seats that vote it down."
    ),
}
"""What each of a Proposal's three roles asks of the Party it is given to."""


def _what_it_asks_of_you(proposal: Proposal, party: Party) -> str:
    """The role the Proposal assigns this Party — including the role of not being named."""
    return _WHAT_EACH_ROLE_ASKS[proposal.role_of(party.name)]


def _what_it_pays_of_your_price(proposal: Proposal, party: Party) -> str:
    """The Price report for the list the Proposal's own role puts this Party on.

    A Party the Proposal does not name is charging nothing, because it is being asked for
    nothing: showing it a price list for a bargain nobody offered would be the Referee
    reporting on a question that was not put.
    """
    price = _price_asked_of(proposal, party)
    if price is None:
        return ""
    return (
        f"WHAT IT PAYS OF YOUR {price.value.upper()}\n\n"
        + render_price_report(price_report(party, proposal.platform, price))
        + "\n\n  A report, not a verdict. You may waive a price you named yourself, and you "
        "may walk away over one the referee has just called met."
    )


_WHAT_EACH_ROLE_CHARGES = {
    Role.GOVERNMENT: Price.GOVERNING,
    Role.SUPPORT_ONLY: Price.SUPPORTING,
    Role.UNNAMED: None,
}
"""Which price list each role puts a Party on. None is not a missing entry: a Party the
Proposal never names is charging nothing, because it is being asked for nothing."""


def _price_asked_of(proposal: Proposal, party: Party) -> Price | None:
    """Which of a Party's two price lists this Proposal is asking it to charge on."""
    return _WHAT_EACH_ROLE_CHARGES[proposal.role_of(party.name)]


def _how_the_vote_works(party: Party) -> str:
    """Negative parliamentarism, said once to each Party in the terms of its own seats."""
    return (
        "HOW THE VOTE WORKS\n\n"
        "The chamber does not vote a government in. It votes on whether to reject one, and "
        f"this proposal passes unless {BLOCKING_MINORITY} seats or more vote No. All "
        f"{party.seats} of your seats go whichever way you do; they are never split.\n\n"
        "  - Yes      — you are for it.\n"
        "  - Abstain  — you neither back it nor block it, and it passes over you.\n"
        "  - No       — you are one of the seats trying to bring it down.\n\n"
        "Yes and Abstain do the same thing to the arithmetic. Only No can defeat it, and "
        f"only if enough others vote No beside you to reach {BLOCKING_MINORITY}.\n\n"
        "Nothing binds you. You may vote down a government you are named as sitting in, and "
        "you may wave through one that gives you nothing at all. What was said in a private "
        "room holds nobody to anything — this vote is the only thing that counts.\n\n"
        f"How do you vote, and why? About {WORDS} words in your own words, then call "
        f"`{BALLOT}` in the same reply to cast it."
    )


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
            f"Who do you meet, and why? About {WORDS // 2} words in your own words, then "
            "call `meet` in the same reply to book the room.",
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
        f"reply, in your own voice, and keep it to about {WORDS} words. Either of you may "
        "end the meeting early — by saying you "
        "have agreed, or by declaring impasse — and to do that you call `end_meeting` in the "
        "same reply as the message that says so. Ending it closes it at once: the other side "
        "gets no reply. Otherwise it ends when the messages run out."
    )


def _that_meeting_is_over(met: Bilateral) -> str:
    """What the Formateur is told once a Bilateral closes, before it chooses again."""
    return f"The meeting with {met.counterparty} is over: {met.ended_by(met.formateur)}."


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
            f"  - Be short: about {WORDS} words, one paragraph, never more. Name what you "
            "want, say what you will pay for it, and stop. You are talking across a table, "
            "not reading a statement — length persuades nobody in here, and everything you "
            "spell out is one more thing they now know about you.",
        ]
    )


def _read_exchange(response: Response, speaker: str) -> Exchange:
    """Turn one API response into an Exchange, or fail saying what was wrong with it.

    The one place an Agent's prose is *required*. The other side reads an Exchange and answers
    it, so a missing one is a turn of the negotiation that never happened — everything else an
    Agent says is an aside nobody answers, and `_aside` lets that be absent.
    """
    message = _aside(response, speaker)
    if not message:
        raise AgentError(f"{speaker}'s Agent returned no text block to read an Exchange from")
    if len(message.strip()) < MIN_MESSAGE:
        raise AgentError(
            f"{speaker}'s Agent returned a fragment rather than an Exchange: {message!r}.\n"
            f"  An Exchange the other side would have to guess the rest of is worse than none: "
            f"it gets read as the start of a sentence and answered as though it were one."
        )

    given = _tool_call(response, speaker, expected=(str(END_MEETING["name"]),))
    declares = None if given is None else _declaration(given[1].get("ending"), speaker)

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

    No floor on the reasoning, and no requirement that there be one. The fragment
    `MIN_MESSAGE` exists for is a fragment somebody *answers* — a reasoning is read by nobody
    in the Run, so a short one is terse and a missing one is a Round the record says nothing
    about, rather than a Round that did not happen.
    """
    reasoning = _aside(response, speaker)
    given = _tool_call(response, speaker, expected=(MEET,))
    if given is None:
        raise AgentError(
            f"{speaker}'s Agent gave its reasoning without booking a meeting: {reasoning!r}.\n"
            f"  Whom to meet is read from the `{MEET}` call and nowhere else, so a Round that "
            f"names a Party only in prose has chosen nobody."
        )

    chosen = given[1].get("party")
    if chosen not in [party.name for party in others]:
        raise AgentError(
            f"{speaker}'s Agent chose to meet {chosen!r}, which is not a Party it can meet"
        )

    try:
        return Choice(counterparty=chosen, reasoning=reasoning)
    except ValidationError as error:
        raise AgentError(f"{speaker}'s Agent returned an unusable Choice: {error}") from error


def _read_proposal(
    response: Response, formateur: str, scenario: Scenario, commitments: tuple[str, ...]
) -> tuple[Proposal | None, str]:
    """A tabled Proposal or a Stand down, and the prose the Formateur gave either way.

    None is Standing down, and it is a real answer rather than a failure to give one — a
    Formateur that called neither tool has not stood down, it has said nothing, and that is
    the error below.
    """
    reasoning = _aside(response, formateur)
    given = _tool_call(response, formateur, expected=(TABLE, STAND_DOWN))
    if given is None:
        raise AgentError(
            f"{formateur}'s Agent neither tabled a Proposal nor stood down: {reasoning!r}.\n"
            f"  An Attempt ends one way or the other, and which one is read from the "
            f"`{TABLE}` or `{STAND_DOWN}` call rather than out of the prose."
        )

    called, arguments = given
    if called == STAND_DOWN:
        return None, reasoning

    government = _listed(arguments, "government", formateur)
    support_only = _listed(arguments, "support_only", formateur)
    granted = _listed(arguments, "commitments", formateur)

    chamber = {party.name for party in scenario.parties}
    for name in (*government, *support_only):
        if name not in chamber:
            raise AgentError(
                f"{formateur}'s Agent named {name!r} in its Proposal, which is not a Party "
                f"in Scenario {scenario.name!r}"
            )
    for commitment in granted:
        if commitment not in commitments:
            raise AgentError(
                f"{formateur}'s Agent granted a Commitment nobody charged for: {commitment!r}"
            )

    if not government:
        raise AgentError(
            f"{formateur}'s Agent tabled a Proposal with nobody in its government.\n"
            f"  A government of nobody is not a government, and a Formateur with nobody to "
            f"put in cabinet has stood down — which is `{STAND_DOWN}`, not an empty `{TABLE}`."
        )

    platform = arguments.get("platform")
    if not isinstance(platform, dict):
        raise AgentError(f"{formateur}'s Agent tabled a Platform of {platform!r}")

    try:
        return (
            Proposal(
                formateur=formateur,
                platform=Platform(**platform),
                government=tuple(government),
                support_only=tuple(support_only),
                commitments=tuple(granted),
            ),
            reasoning,
        )
    except ValidationError as error:
        raise AgentError(f"{formateur}'s Agent tabled an unusable Proposal: {error}") from error


def _listed(arguments: dict[str, Any], field: str, formateur: str) -> list[str]:
    """One list-of-names field of a tabled Proposal. Absent means empty, and so does empty.

    Absent is a real case: `commitments` is left off the tool entirely when no Party in the
    Scenario has named a free-text Demand, because an empty enum is a field nothing satisfies.
    """
    given = arguments.get(field, [])
    if not isinstance(given, list) or not all(isinstance(name, str) for name in given):
        raise AgentError(f"{formateur}'s Agent gave {field} as {given!r}")
    return list(given)


def _read_judgement(response: Response, party: str) -> Judgement:
    """One Party's Ballot, and what it said casting it.

    The Ballot is the enumerated argument and the reasoning is the reply's own text, which is
    the whole of §2 at the one moment it matters most: this is the number the Referee counts,
    and a Vote read out of prose would be a Vote nobody could check.
    """
    reasoning = _aside(response, party)
    given = _tool_call(response, party, expected=(BALLOT,))
    if given is None:
        raise AgentError(
            f"{party}'s Agent said its piece without voting: {reasoning!r}.\n"
            f"  Every Party casts a Ballot, and it is read from the `{BALLOT}` call and "
            f"nowhere else."
        )

    cast = given[1].get("ballot")
    if cast not in [option.value for option in Ballot]:
        raise AgentError(f"{party}'s Agent voted {cast!r}, which is not a Ballot")

    try:
        return Judgement(party=party, ballot=Ballot(cast), reasoning=reasoning)
    except ValidationError as error:
        raise AgentError(f"{party}'s Agent returned an unusable Ballot: {error}") from error


def _aside(response: Response, speaker: str) -> str:
    """The reply's ordinary text — the only place any prose in KBBL comes from — or "".

    Ticket 02 recorded what happens when prose is decoded inside a constrained field instead:
    empty strings, truncated stubs and leaked JSON, in roughly one live call in eleven. So the
    message is the reply's own text and every field the Referee reads is an enumerated tool
    argument beside it (§2).

    Empty is a real answer here, because what comes through this for everything but an
    Exchange is an aside nobody in the Run answers.

    A Round's reasoning, a Formateur's account of what it tabled, a Party's line on its own
    Ballot: each is for the Transcript, and none of them is a turn of the negotiation. Live
    Agents do spend a turn's thinking and hand back the call alone — a whole recorded Attempt
    aborted on the first live run of this ticket for want of one sentence — and killing a paid
    Attempt over a missing aside is failing loudly about the wrong thing. The question the
    Referee asked was answered, in the enumerated field it agreed to read. `_read_exchange` is
    the one caller that insists, and it says why.

    What is *not* waved through is a reply that did not finish. A refusal, a `max_tokens` cut
    or any other stop reason is a reply nobody should read a tool call out of either, so it
    is checked here rather than beside the prose it happens to be missing.
    """
    stop = response.get("stop_reason")
    if stop == "refusal":
        raise AgentError(f"{speaker}'s Agent refused to answer: {response.get('stop_details')}")
    if stop not in (None, "end_turn", "tool_use"):
        raise AgentError(f"{speaker}'s Agent did not finish speaking: stop_reason {stop!r}")

    blocks = response.get("content") or ()
    text = next((block["text"] for block in blocks if block.get("type") == "text"), None)
    return "" if text is None else str(text)


def _usage(response: Response, *, party: str, cassette: str) -> Usage:
    """What one request cost, read off the reply it got back.

    Read here rather than counted anywhere else because the reply is the only place the
    numbers exist: §6's whole cost model — prompt caching on the Persona prefix, a batched
    half-price path — is a claim about `cache_read_input_tokens` against `input_tokens`, and
    a Run whose record does not carry them cannot be asked whether the caching worked.

    A missing count is zero rather than an error. A Cassette recorded before this ticket and
    a stand-in that never billed anything both hand back a reply with no `usage` in it, and
    losing a whole Attempt over the accounting for it would be losing the thing for the
    account of the thing.
    """
    counted = response.get("usage") or {}
    return Usage(
        party=party,
        cassette=cassette,
        input_tokens=_tokens(counted, "input_tokens"),
        output_tokens=_tokens(counted, "output_tokens"),
        cache_write_tokens=_tokens(counted, "cache_creation_input_tokens"),
        cache_read_tokens=_tokens(counted, "cache_read_input_tokens"),
    )


def _tokens(counted: Mapping[str, Any], field: str) -> int:
    """One token count, or 0 where the reply gave none. Never a guess at a missing one."""
    value = counted.get(field)
    return value if isinstance(value, int) else 0


def _tool_call(
    response: Response, speaker: str, *, expected: tuple[str, ...]
) -> tuple[str, dict[str, Any]] | None:
    """Which of `expected` a reply called and what with, or None if it called nothing.

    An Agent is never offered a tool it cannot use, so anything else in a reply is a reply
    nobody agreed to read: two calls at once, or a call by a name that was never on offer.
    The name comes back beside the arguments because tabling and Standing down are two tools
    answering one question, and which was called *is* the answer.
    """
    blocks = response.get("content") or ()
    calls = [block for block in blocks if block.get("type") == "tool_use"]
    if not calls:
        return None
    if len(calls) > 1:
        names = ", ".join(str(call.get("name")) for call in calls)
        raise AgentError(f"{speaker}'s Agent made more than one call in one reply: {names}")

    call = calls[0]
    name = call.get("name")
    if name not in expected:
        raise AgentError(f"{speaker}'s Agent called {name!r}, which is not a tool it has")
    given = call.get("input")
    if not isinstance(given, dict):
        raise AgentError(f"{speaker}'s Agent called {name!r} with {given!r}")
    return str(name), given
