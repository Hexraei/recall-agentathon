# Evidence

What we tested, what broke, why it broke, and why we fixed it the way we did.

This directory exists because a working demo does not show whether a system was
*engineered*. Anything can be made to work once on a laptop. What distinguishes a
system you can trust is whether the people who built it went looking for the places it
fails, understood them, and can say why the fix is the right one rather than the
convenient one.

Each entry below is a real failure found on this project, with the measurement that found
it. None of them were planted for the writeup.

## Defects found and fixed

| # | Defect | Found by | Why it is worth reading |
|---|---|---|---|
| [01](bug-01-report-truncation.md) | The report agent crashed on the lowest-scoring student | Running the full cohort, not one happy path | The failure scaled with how much a student was struggling — it would have worked in every spot check and failed live on whoever did worst |
| [02](bug-02-composing-timeouts.md) | Three correctly-set timeouts composed into a 39-minute hang | An accidental network outage mid-run | Every individual component was correct. Bounded × bounded ≠ usefully bounded |
| [03](bug-03-biased-compare-prompt.md) | The comparison step was wrong 9 times in 10 | Measuring a fixed input 10× instead of assuming model flakiness | The bias was in a prompt **we wrote**. An instruction that states a preference rather than a procedure gets followed to its limit |
| [04](bug-04-checker-hallucinated-contradictions.md) | The checker rejected true sentences, citing the numbers that proved them | Measuring the whole cohort and reading every rejection reason | A model handed the right numbers still failed to compare them — and explained the error using the correct figures |
| [05](bug-05-empty-structured-fields.md) | 59% of real reports leave a real strength or gap out of the structured fields entirely | Reviewing 22 real students' reports against the counts, not spot-checking a few | A new *kind* of bug for this system: not a false claim, an omission. Every check built so far catches "is this true," none catch "is something missing" |

## The through-line

Five defects, five different causes, one shared method: **in each case the first
plausible explanation was wrong, and measuring beat assuming.**

- Bug 03's first explanation was "the model is unreliable." Measuring showed the model was
  reliably following a bad instruction we had written ourselves. Swapping models would
  have hidden it.
- Bug 01's first explanation was "the token limit is too low." Raising it would have moved
  the failure rather than removed it, and would have cost tokens on every call to guard a
  rare one.
- Bug 02's first explanation was "a timeout is misconfigured." None of them were. The
  fences we already had were each measuring the right thing for a different failure.

The other pattern worth naming: **more than one of these fixes made the product better on
the merits, not just more robust.** Bounding the report schema (01) produced a page a student
will actually read instead of a ten-item scoreboard. Replacing a prompt's disposition with
a decision procedure (03) made the system's teaching judgement explicit enough to argue
with. A constraint that forces a better design was worth having.

## What we have not tested

Stated plainly, because an evidence directory that only lists wins is not evidence:

- **Degraded network behaviour is untested by design.** We found bug 02 by accident. Every
  timeout in the system is still only verified against a working connection. The test
  worth writing is fault injection at the `httpx` boundary.
- **The extraction step's run-to-run consistency has never been measured.** Only the
  comparison step's has (bug 03). The original instability was traced upstream to
  extraction variance, and comparison being stable now does not prove extraction is.
- **The checker enforces its rules on structured verdicts but not on free-text prose.** A
  headline calling 3/5 "strong" was accepted while the `verdict` fields were all correct.
  Noted at the end of bug 01. The numbers a teacher acts on are right; the wording can
  overstate.
- **Bug 05 is confirmed, not fixed.** We found it reviewing real students' reports and
  wrote it up before touching the code, on purpose — writing the fix first tends to
  produce a tidier story than what actually happened. Whatever fix lands should be
  re-measured against the same real batch, the same way bugs 01, 03 and 04 were, before it
  gets called done.
