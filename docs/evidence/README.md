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
| [04](bug-04-empty-structured-fields.md) | 59% of real reports leave a real strength or gap out of the structured fields entirely | Reviewing 22 real students' reports against the counts, not spot-checking a few | A new *kind* of bug for this system: not a false claim, an omission. Every check built so far catches "is this true," none catch "is something missing" |
| [05](bug-05-checker-hallucinated-contradictions.md) | The checker rejected true sentences, citing the numbers that proved them | Measuring the whole cohort and reading every rejection reason | A model handed the right numbers still failed to compare them — and explained the error using the correct figures |
| [06](bug-06-evidence-that-said-nothing.md) | Two thirds of reports repeated themselves, and half the sentences said nothing | Measuring report *quality*, not just pass/fail, over 30 real students | A report can pass every correctness check and still waste the reader's time — accuracy and usefulness are different things to verify |
| [07](bug-07-silent-degradation.md) | The fast provider was gone for the day and nothing said so | Noticing a cohort run took 411s when an earlier one took a fraction of that | A silent fallback is a second outage waiting to happen — if nothing on screen says which provider answered, a slowdown looks like a mystery instead of a known, handled case |
| [08](bug-08-mislabelled-negative-control.md) | The demo's "no pattern here" control had a real pattern in it — twice | Running the real pipeline against it and reading the citation instead of trusting the label | Not a defect in the code but in how we judged it. The comfortable conclusion was "the model over-claimed"; the evidence said the model was right and our test was wrong |

## The through-line

Eight defects, eight different causes, one shared method: **in each case the first
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
- **Bug 04's headline number (59%) was re-measured after later fixes and dropped to 0%
  reports missing a weak concept.** Recorded here rather than silently updated in the
  original writeup, because the honest version of "we fixed it" includes the number that
  proves it, not just the claim.
