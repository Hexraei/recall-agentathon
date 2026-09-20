# Pre-event assets

This is not this repo's literal first commit. The rule announced on Day 1 asks
for that; ours could not be, because Phase 1 was built and pushed the day
before the rule was clarified in `docs/ON-THE-DAY.md` (pulled and read this
morning, 19 September). Rather than rewrite public history to fake the order,
this is added now as an honest declaration of everything that predates today,
committed as the next thing after reading the rule. Nothing below was hidden;
it is all in the existing commit history at
[github.com/Hexraei/recall-agentathon](https://github.com/Hexraei/recall-agentathon).

## What we are bringing in

**The starter kit's spine (`slice/`).** Copied from
[rsimhan/agentic-slice-kit](https://github.com/rsimhan/agentic-slice-kit) — the
event's own kit, not outside work. ~1,100 lines: durable append-only storage in
SQLite, typed contracts, the budget fences, human-in-the-loop suspend/resume,
and the state-machine runner. One edit to it: `RunState` shipped with six
states baked in from the kit's own demo domain; we extended the enum with our
ten, additively, and it is called out in the code comment and in an earlier
commit message. Nothing else in `slice/` is touched.

**Our own agent logic (`app/`), written in the two days before the event, not
before it.** Schemas, the state machine handlers, the four prompts, the
citation check, the cross-run history reader, and the demo/test fixtures. This
is new work, not reused — listed here only so the boundary between it and the
kit is explicit.

**Free-tier accounts set up before today.** A Groq account and API key
(console.groq.com), used because the event's own OpenRouter key is shared
across every team and rate-limited under load — measured directly: the same
model took 0.89s on Groq and 15–20s through OpenRouter's shared pool on an
identical prompt. Nothing paid; no credit card. This is infrastructure setup,
not prior code or a dataset.

**Libraries beyond the obvious.** `sqlite-vec` and `fastembed` (from the kit's
own `requirements.txt`) for local, offline retrieval over the course notes — no
vector service, no API key, no network after the embedding model is cached.
`httpx` and `pydantic` are the kit's baseline dependencies.

## What we are not bringing in

No prior hackathon code, no previous course project, no dataset gathered before
today. The corpus (`corpus/ds-notes.md`) and the three demo submissions
(`app/fixtures.py`) were hand-written for this build, not sourced from
anywhere. No prompt or evaluation set predates the two days before the event —
the four prompts in `app/prompts/` were written and then measurably fixed once
already (see the `Fix the compare prompt` commit), which happened yesterday,
not before.
