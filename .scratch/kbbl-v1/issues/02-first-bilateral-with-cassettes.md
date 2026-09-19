# 02 — First Bilateral against a live model, recorded to Cassettes

**What to build:** One Formateur meets one Party privately and they bargain. Up to three
Exchanges each way, with either side free to exit early by agreeing or declaring impasse. The
conversation prints as a readable Transcript. Every request and response is written to a
Cassette keyed by a hash of the request, so `--replay` reruns the meeting for free.

**This is the ~$0.02 test the rest of v1 is built outward from** (§10). The riskiest assumption
in the project is not the arithmetic — it is whether LLM Party agents produce a negotiation
worth reading, or agree in round one. This ticket answers that, and the answer should be
written down before ticket 04 builds more machinery on top of it.

Cassettes land here rather than later because §8 is explicit: retrofitting record/replay means
re-plumbing every call site, so it goes in with the first call that is ever made.

**Blocked by:** 01.

**Status:** ready-for-agent

- [ ] A Formateur and one other Party hold a private Bilateral of up to three Exchanges each way
- [ ] Either side may exit early by agreeing or declaring impasse, and the Transcript shows which happened
- [ ] Persona is built from the mandate: Positions, Governing price, Supporting price, Exclusions, Willingness to re-elect
- [ ] Willingness to re-elect reaches the Agent as a disposition it may conceal or overstate — never as a number the Referee reads (§3)
- [ ] Exclusions reach the Agent as soft preferences carrying a price, never as hard constraints (§3)
- [ ] Every request/response is written to a Cassette keyed by a hash of the request
- [ ] `--replay` reruns the Bilateral from Cassettes with zero API calls and an identical Transcript
- [ ] Live is the default; `--replay` opts out (§11.5)
- [ ] Model is `claude-sonnet-5`, with prompt caching on the stable persona prefix (§6)
- [ ] Exchanges accumulate into an in-memory run record for ticket 06 to serialise — not printed and discarded
- [ ] **Read the Transcript closely and record the judgement in this file's Comments: do the parties bargain, or fold immediately?** This is the deliverable, not a formality (§12.1)
