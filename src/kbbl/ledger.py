"""The Ledger: the Run record as it is written, one paid-for thing at a time.

Nothing about a Run is assembled at the end. Every Exchange, every Ballot, every report
put in front of a Party and the cost of every request is entered here at the moment it
happens, so that a Run which breaks mid-Bilateral still holds everything it has already
been billed for. §8 pulls Cassettes forward to the first call for the same reason this
exists: paid work that is only written down on the way out is paid work a crash throws away.

The Ledger is the one place that knows a `Run` can be incomplete. Everything downstream is
handed a finished `Run` model, and `finished` on it is what says whether the Attempt reached
an end of its own or merely stopped.
"""

from __future__ import annotations

from kbbl.models import (
    Bilateral,
    Choice,
    ExclusionReport,
    Exchange,
    GapReport,
    Judgement,
    Proposal,
    Round,
    Run,
    Usage,
)


class Ledger:
    """One Run's record, open for writing until the Attempt ends.

    Written to by the Agents as they act and read by whoever is holding it — which is the
    caller of `attempt`, not `attempt` itself, because a Run that raises never returns and
    the artifacts have to be written from outside the call that failed.
    """

    def __init__(self, *, scenario: str, formateur: str) -> None:
        self.scenario = scenario
        self.formateur = formateur
        self._rounds: list[Round] = []
        self._opened = 0
        """How many Rounds have been opened, which is not how many are kept.

        A Round is numbered by when it was spent rather than by its place in the list, so a
        Round that bought nothing leaves a gap rather than renumbering the ones after it. A
        record that called Round 4 "Round 3" would be describing a meeting that never
        happened."""
        self._choice: Choice | None = None
        self._exchanges: list[Exchange] = []
        self._proposal: Proposal | None = None
        self._reasoning = ""
        self._judgements: list[Judgement] = []
        self._gap_reports: list[GapReport] = []
        self._exclusion_reports: list[ExclusionReport] = []
        self._usage: list[Usage] = []
        self._finished = False

    @property
    def run(self) -> Run:
        """The record as it stands, complete or not.

        Built fresh each time rather than kept as a field, because a `Run` is frozen and a
        half-written one is a thing this class has and that class must not be.
        """
        return Run(
            scenario=self.scenario,
            formateur=self.formateur,
            rounds=tuple(self._rounds) + self._open(),
            proposal=self._proposal,
            reasoning=self._reasoning,
            judgements=tuple(self._judgements),
            gap_reports=tuple(self._gap_reports),
            exclusion_reports=tuple(self._exclusion_reports),
            usage=tuple(self._usage),
            finished=self._finished,
        )

    def chose(self, choice: Choice) -> None:
        """Open a Round on the Choice that bought it, closing the one before."""
        self._open_round(choice)

    def met(self, counterparty: str) -> None:
        """A Bilateral is opening. Opens a Round of its own if no Choice bought this one.

        A Bilateral held without a Choice in front of it is not a Round that did not happen
        — it is a Round nobody explained, which is what an empty `Choice.reasoning` already
        means. Recording it that way keeps a meeting in the record; refusing it would
        silently drop the one thing a Run pays most for.

        An open Round is reused only while it is still empty. A Formateur that spends two
        Rounds on the same Party is the normal case (§5.1), and two meetings whose Exchanges
        ran into one list would be a record claiming one meeting of six.
        """
        if (
            self._choice is None
            or self._choice.counterparty != counterparty
            or self._exchanges
        ):
            self._open_round(Choice(counterparty=counterparty))

    def said(self, exchange: Exchange) -> None:
        """One Exchange, entered as it is spoken rather than when its Bilateral closes."""
        self._exchanges.append(exchange)

    def tabled(self, proposal: Proposal | None, reasoning: str) -> None:
        """How the Attempt ended: the Proposal, or the Stand down that tabled none (§5.3)."""
        self._close()
        self._proposal = proposal
        self._reasoning = reasoning

    def shown(self, report: GapReport | ExclusionReport) -> None:
        """A report the Referee put in front of a Party before it voted (§5.4).

        One verb for one act, and the kind of report decides which list it lands in. Two
        methods would have let a caller file a report under the wrong heading, which is the
        only way these can go wrong: a Ledger never reads either one back.
        """
        if isinstance(report, GapReport):
            self._gap_reports.append(report)
        else:
            self._exclusion_reports.append(report)

    def judged(self, judgement: Judgement) -> None:
        """One Party's Ballot, and what it said casting it."""
        self._judgements.append(judgement)

    def paid(self, usage: Usage) -> None:
        """What one request to the model cost, and the Cassette that holds it."""
        self._usage.append(usage)

    def finish(self) -> None:
        """The Attempt reached an end of its own. Anything not marked this way stopped.

        A command rather than a record of something an Agent did, which is why it is the one
        method here in the imperative — and why it is not spelled like the `Run.finished` it
        sets, where a reader could take it for a question.
        """
        self._close()
        self._finished = True

    def _open_round(self, choice: Choice) -> None:
        """Settle the Round in progress and start a new one on this Choice."""
        self._close()
        self._choice = choice
        self._opened += 1

    def _open(self) -> tuple[Round, ...]:
        """The Round in progress, if it has bought anything yet.

        A Round whose Bilateral has no Exchange in it is dropped, because a `Bilateral` is a
        meeting and a meeting nobody spoke in is not one. What it cost is still in `usage`,
        and the Cassette key there leads back to what the Formateur said choosing it — so
        the reasoning is recoverable, which is not the same as being in the record. A Round
        can only be dropped this way by a Run that stopped in the instant between booking a
        meeting and the first word of it.
        """
        if self._choice is None or not self._exchanges:
            return ()
        return (
            Round(
                number=self._opened,
                choice=self._choice,
                bilateral=Bilateral(
                    formateur=self.formateur,
                    counterparty=self._choice.counterparty,
                    exchanges=tuple(self._exchanges),
                ),
            ),
        )

    def _close(self) -> None:
        """Settle the open Round into the record, and start the next one empty."""
        self._rounds.extend(self._open())
        self._choice = None
        self._exchanges = []
