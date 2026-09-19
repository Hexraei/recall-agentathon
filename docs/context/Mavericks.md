# AgentSpec: Persistent Learning Companion

## 1. The setting

A teacher runs a course over an entire term. Students complete repeated
formative activities such as quizzes, short answers, explanations,
reflections, projects, and homework.

The course may be in **any subject**: science, history, mathematics,
language, social studies, or a vocational subject. The teacher wants to
understand not only how a student performs today, but also whether a
difficulty has appeared before, whether it is improving, and whether it
is recurring across different assignments.

The teacher may have forty to sixty students. Each student produces many
pieces of work during the term. The teacher cannot reliably remember
every misconception, unanswered question, or unresolved learning gap
across all those encounters.

The proposed agent is a persistent learning companion. It works
alongside the teacher and student, maintaining a longitudinal record of
learning evidence across assignments.

------------------------------------------------------------------------

## 2. The problem this solves

Most classroom AI tools respond to one moment:

-   a student submits an answer;
-   the system grades or explains that answer;
-   the interaction ends.

The next time the student submits work, the system often starts from
scratch. A quiz today has no memory of a quiz three weeks ago. A
misconception from week 2 can resurface in week 6 without anyone
noticing that it is recurring.

This creates three problems:

1.  **Repeated difficulties remain disconnected.**\
    Similar errors or gaps may appear in several assignments, but each
    assignment is treated as an isolated event.

2.  **Teachers must carry too much history in their heads.**\
    A teacher is expected to remember what dozens of students struggled
    with over an entire term.

3.  **Feedback is not longitudinal.**\
    The student may receive useful feedback on each individual task, but
    not an explanation of how their understanding has changed over time.

The agent should help with the memory and comparison work while
preserving the teacher's judgment.

It should not declare that a student has a fixed ability, diagnose a
condition, or replace the teacher. It should identify **evidence-backed
candidate learning gaps** and make the history visible.

------------------------------------------------------------------------

## 3. What you are building

You are building a persistent, evidence-based learning companion that:

1.  receives a student's new piece of work;
2.  identifies the concepts, skills, or learning objectives relevant to
    that work;
3.  extracts evidence from the student's response;
4.  compares the new evidence with the student's previous learning
    history;
5.  identifies possible recurring, improving, or newly appearing
    difficulties;
6.  checks whether each finding is supported by the available evidence;
7.  asks a human for clarification or confirmation when the evidence is
    ambiguous;
8.  updates the student's longitudinal learning record;
9.  produces a concise teacher-facing summary and, where appropriate, a
    student-facing next step.

The key differentiator is **memory across encounters**.

The agent does not merely answer, "What is wrong with this response?" It
also asks, "Have we seen evidence related to this skill before, and what
changed since then?"

------------------------------------------------------------------------

## 4. A complete walkthrough

### The first encounter

A teacher uploads a new student submission.

For the worked example, the subject is history, but the workflow is
intended to work across subjects.

The assignment asks the student to explain why a historical event had
several causes and to support the explanation with evidence from class
materials.

The student, Mira, submits a short response. Her answer identifies one
immediate cause correctly but treats the event as if it had only one
cause. She also makes a claim that is not supported by the supplied
class material.

The agent performs the following work:

1.  **Read the assignment context.**\
    It identifies the relevant learning goals: distinguishing causes,
    connecting evidence to claims, and explaining relationships between
    events.

2.  **Read the student response.**\
    It extracts specific passages that show what Mira did correctly and
    where her explanation is incomplete.

3.  **Look at prior history.**\
    There is no earlier record for the relevant learning goal, so the
    agent does not claim that the difficulty is recurring.

4.  **Create a provisional finding.**\
    The agent records that Mira may need support distinguishing a single
    cause from a set of interacting causes.

5.  **Check the finding.**\
    The checker verifies that the finding is grounded in the current
    response and assignment criteria.

6.  **Update the record.**\
    The system stores the attempt, the evidence, the provisional
    finding, and the confidence level.

7.  **Prepare the output.**\
    The teacher receives a short summary:

    > Mira correctly identified one immediate cause. In this response,
    > she did not yet explain how multiple causes interacted. This is a
    > first recorded signal for this learning goal; recurrence has not
    > been established.

The system does not label Mira permanently. It records a bounded
observation tied to one piece of work.

### The second encounter

Two weeks later, Mira submits a new assignment. This time she must
explain a different historical event and compare several contributing
factors.

The agent reads the new submission and then retrieves Mira's previous
learning history.

The new response again identifies one factor accurately but does not
connect the factors into a broader explanation. The agent compares the
new evidence with the earlier record.

It now has evidence from two separate assignments:

-   in the first assignment, Mira treated a complex event as having one
    main cause;
-   in the second assignment, Mira again listed one factor but did not
    explain the interaction among several factors.

The agent does not automatically conclude that Mira "does not understand
causation." Instead, it produces a more careful finding:

> A possible recurring difficulty has appeared in explaining how
> multiple causes interact. Similar evidence was observed in two
> assignments. The pattern is supported by the cited response passages,
> but teacher review is recommended before planning a targeted
> intervention.

The teacher reviews the evidence and confirms that the pattern is
meaningful. The agent then updates the record to show:

-   the learning goal involved;
-   the two supporting attempts;
-   the teacher's confirmation;
-   the recommended next step.

The next step might be a short activity requiring Mira to arrange causes
into categories, explain relationships between them, and justify which
causes were most influential.

### What changes because of persistence

Without persistent memory, the second encounter might produce only
ordinary feedback on the second assignment.

With persistence, the system can say:

-   this issue has appeared before;
-   it appeared in a different task;
-   the evidence is similar but not identical;
-   the teacher has or has not confirmed the pattern;
-   the student may benefit from a targeted follow-up.

That is the core value of the project.

------------------------------------------------------------------------

## 5. Who is doing the thinking

The agent and the human should have different responsibilities.

  -----------------------------------------------------------------------
  Work              Agent does it     Human does it     What the human
                                                        loses if the
                                                        agent does it
                                                        alone
  ----------------- ----------------- ----------------- -----------------
  Find relevant     Yes               Optional review   Little; this is
  passages in a                                         mainly search and
  submission                                            extraction

  Compare current   Yes               Review important  The teacher may
  work with prior                     comparisons       miss the context
  attempts                                              behind a
                                                        similarity

  Notice a possible Yes               Judge whether it  Professional
  recurring pattern                   matters           judgment and
                                                        knowledge of the
                                                        student

  Check whether a   Yes, mechanically Review edge cases Trust if
  claim is                                              unsupported
  supported by                                          findings reach
  evidence                                              the student

  Decide whether a  No final decision Yes               Nuance, fairness,
  student has a                                         and
  meaningful                                            responsibility
  learning gap                                          

  Choose an         Suggest options   Decide and adapt  Knowledge of
  intervention                                          classroom context
                                                        and student needs

  Explain the       Draft             Approve or adapt  The teacher's
  result to the                                         relationship and
  student                                               tone

  Update the        Yes               Correct or        Oversight if the
  longitudinal                        confirm           record becomes
  record                                                inaccurate
  -----------------------------------------------------------------------

The agent is best used for searching, cross-referencing, formatting,
noticing contradictions, and maintaining continuity.

The human should retain responsibility for framing the learning problem,
interpreting ambiguous evidence, deciding what matters instructionally,
and choosing consequential interventions.

------------------------------------------------------------------------

## 6. The state machine

The system moves through a small number of explicit states.

### States

1.  **New attempt received**\
    A new student submission and its assignment context have arrived.

2.  **Extracting evidence**\
    The agent identifies relevant learning goals, extracts response
    passages, and records observable signals.

3.  **Comparing with history**\
    The agent retrieves prior attempts and checks whether similar
    evidence has appeared before.

4.  **Draft finding created**\
    The agent creates a provisional summary of what the evidence may
    indicate.

5.  **Evidence check**\
    A separate checker verifies that the draft finding is supported by
    the submission and prior records.

6.  **Needs human review**\
    The evidence is ambiguous, the pattern is consequential, or the
    checker cannot establish support.

7.  **Record updated**\
    The attempt, evidence, finding, and any human decision are appended
    to the student's history.

8.  **Recommendation ready**\
    A teacher-facing summary and optional student-facing next step are
    prepared.

9.  **Finished**\
    The run is complete, with a durable record of what happened.

### Transitions

-   `New attempt received` → `Extracting evidence`
-   `Extracting evidence` → `Comparing with history`
-   `Comparing with history` → `Draft finding created`
-   `Draft finding created` → `Evidence check`
-   `Evidence check` → `Record updated` if supported
-   `Evidence check` → `Needs human review` if ambiguous or unsupported
-   `Needs human review` → `Record updated` after teacher clarification
    or confirmation
-   `Record updated` → `Recommendation ready`
-   `Recommendation ready` → `Finished`

If the evidence checker rejects a finding because it contains an
unsupported claim, the system sends the work back to evidence extraction
or comparison rather than allowing the unsupported statement to pass.

### Human waiting state

The `Needs human review` state is important. The agent must be able to
pause instead of inventing certainty.

Examples of reasons to wait:

-   two responses appear similar, but the similarity may be superficial;
-   the assignment changed its learning objective;
-   the student's response is too short to interpret;
-   the agent cannot identify a reliable source passage;
-   the finding could materially affect how the student is treated.

------------------------------------------------------------------------

## 7. The data model

The system should store a chronological learning history rather than
overwrite a single profile.

Each attempt should contain:

-   student identifier;
-   assignment identifier;
-   date;
-   subject or course context;
-   assignment prompt or learning objectives;
-   the student's submitted work;
-   extracted evidence passages;
-   concepts or skills involved;
-   provisional findings;
-   confidence and uncertainty;
-   source references supporting each claim;
-   checker result;
-   teacher review, if any;
-   recommended next step.

A learning signal should be phrased as an observation, not as a
permanent identity statement.

Prefer:

> In two recent explanations, the student listed individual factors but
> did not explain how the factors interacted.

Avoid:

> The student is bad at causal reasoning.

The history should preserve:

-   what the agent observed;
-   which submissions support the observation;
-   what remains uncertain;
-   what the teacher confirmed;
-   what changed in later work.

Records should be appended or versioned. A later correction should not
silently erase the earlier record.

------------------------------------------------------------------------

## 8. Step-by-step contracts

### Contract 1: Ingest an attempt

**Input**

-   student submission;
-   assignment context;
-   learning objectives or rubric;
-   student history identifier.

**Output**

-   normalized attempt record;
-   source references for the submission and assignment context.

**Failure cases**

-   missing assignment context;
-   unreadable submission;
-   unknown student identifier;
-   duplicate attempt.

### Contract 2: Extract evidence

**Input**

-   normalized attempt;
-   assignment objectives;
-   rubric or teacher-provided concept map.

**Output**

-   relevant skills or concepts;
-   evidence passages from the student response;
-   observed strengths;
-   observed difficulties;
-   uncertainty notes.

**Rule**

Every important observation must point to a specific passage or source
record.

### Contract 3: Compare with history

**Input**

-   current evidence;
-   prior attempts for the same student;
-   relevant learning objectives.

**Output**

-   related earlier evidence;
-   evidence of improvement;
-   evidence of recurrence;
-   evidence that cannot be compared reliably;
-   explanation of the comparison.

**Rule**

The agent must distinguish between "similar," "recurring," and "not
enough evidence."

### Contract 4: Draft a finding

**Input**

-   current evidence;
-   historical comparison;
-   assignment context.

**Output**

-   concise finding;
-   supporting evidence;
-   confidence level;
-   uncertainty;
-   proposed next step.

**Rule**

The finding must describe a bounded learning signal, not a permanent
judgment about the student.

### Contract 5: Check the finding

**Input**

-   draft finding;
-   source passages;
-   prior attempt records;
-   assignment objectives.

**Output**

-   accepted;
-   rejected;
-   needs human review.

**Checks**

-   Are the cited sources real?
-   Do the cited passages support the claim?
-   Is the finding stronger than the evidence permits?
-   Is the agent confusing one observation with a recurring pattern?
-   Is the comparison valid across the two assignments?

### Contract 6: Human review

**Input**

-   finding;
-   evidence;
-   uncertainty;
-   reason for review.

**Output**

-   confirm;
-   revise;
-   reject;
-   request more evidence;
-   provide an instructional note.

### Contract 7: Update history

**Input**

-   attempt;
-   evidence;
-   checked finding;
-   human decision, if available.

**Output**

-   appended longitudinal record;
-   updated summary of the relevant learning goal;
-   audit trail of changes.

------------------------------------------------------------------------

## 9. The second encounter

The second encounter is essential to the demonstration.

The first encounter creates a record but cannot establish recurrence.
The second encounter reads that record and changes the result.

### First encounter result

> The student may need support explaining how multiple causes interact.
> This is the first recorded signal for this learning goal.

### Second encounter result

> A similar difficulty appeared in a second assignment. The student
> again identified an individual factor but did not explain the
> relationship among several factors. The pattern is now a candidate
> recurring learning gap, pending teacher confirmation.

The second result is not simply a repeat of the first result. It is
different because the agent has access to:

-   the earlier attempt;
-   the earlier evidence;
-   the earlier uncertainty;
-   the new attempt;
-   the new evidence.

The demonstration should make this contrast visible.

------------------------------------------------------------------------

## 10. Files and responsibilities

A minimal implementation could be organized as follows:

-   `models.py`\
    Defines the structures for attempts, evidence, findings, review
    requests, and history records.

-   `ingest.py`\
    Normalizes a new submission and its assignment context.

-   `extract.py`\
    Identifies learning objectives and extracts evidence from the
    response.

-   `history.py`\
    Stores and retrieves student records. It must preserve chronology
    and avoid silent overwrites.

-   `compare.py`\
    Compares current evidence with relevant earlier evidence.

-   `finding.py`\
    Drafts a bounded, evidence-backed learning finding.

-   `checker.py`\
    Independently checks source support, claim strength, and comparison
    validity.

-   `review.py`\
    Handles the human waiting state and records teacher decisions.

-   `recommend.py`\
    Produces a teacher-facing summary and optional next-step activity.

-   `run.py`\
    Coordinates the state machine and supports resuming a paused run.

-   `demo.py`\
    Runs the first encounter and second encounter with a visible
    before-and-after result.

The first version can use a simple local store or file-based history.
The important feature is not the database technology; it is that the
second encounter genuinely reads the first encounter's record.

------------------------------------------------------------------------

## 11. What this deliberately does not do

This project does not:

-   autonomously make high-stakes grading decisions;
-   diagnose disabilities, disorders, or fixed ability levels;
-   label students as intelligent, weak, lazy, or incapable;
-   replace a teacher's professional judgment;
-   infer sensitive personal characteristics;
-   monitor students outside the learning materials provided for the
    course;
-   invent evidence that is not present in the student's work;
-   treat a single mistake as a recurring misconception;
-   automatically prescribe an intervention without appropriate human
    review;
-   assume that one concept taxonomy works perfectly for every subject;
-   claim that a model's confidence is the same as educational
    certainty.

The agent is a memory and evidence assistant, not an autonomous teacher.

------------------------------------------------------------------------

## 12. Build order

### Phase 1: Make the workflow visible

Build a fake but complete first-encounter and second-encounter demo.

Use fixed sample submissions and show:

-   the first attempt;
-   the extracted evidence;
-   the empty or limited history;
-   the first finding;
-   the second attempt;
-   the retrieved earlier evidence;
-   the changed finding.

### Phase 2: Add structured records

Implement the attempt, evidence, finding, history, and review
structures.

Make sure every finding can point back to source material.

### Phase 3: Add real extraction and comparison

Replace hard-coded outputs with model-assisted extraction and
comparison.

Keep the output constrained and inspectable.

### Phase 4: Add the independent checker

Create a separate checking step that can reject an unsupported finding
or send it back for revision.

### Phase 5: Add persistence and resumption

Persist state between runs. Support the human waiting state and resume
after teacher input.

### Phase 6: Add teacher-facing presentation

Show a compact history view with:

-   current evidence;
-   related earlier evidence;
-   what changed;
-   what is still uncertain;
-   what the teacher needs to decide.

### Phase 7: Test across subjects

Use examples from more than one subject to test whether the design is
genuinely general rather than secretly specialized to history or
mathematics.

------------------------------------------------------------------------

## 13. The demo

The demo should tell one clear story.

### Demo setup

A student has two assignments in the same course.

-   Assignment 1: explain the causes of a historical event.
-   Assignment 2: explain the causes of a different historical event.

The student's responses contain a similar limitation: they identify
individual factors but do not explain how several factors interact.

### Demo sequence

1.  Submit Assignment 1.
2.  Show the agent extracting evidence.
3.  Show that the student has no relevant prior history.
4.  Show the first, limited finding.
5.  Save the result.
6.  Submit Assignment 2.
7.  Show the agent retrieving Assignment 1.
8.  Show the comparison between the two attempts.
9.  Show the evidence checker verifying the recurring-pattern claim.
10. Pause for teacher confirmation.
11. Show the updated longitudinal record.
12. Show a targeted next-step recommendation.

### What the audience should understand

The impressive behavior is not that the agent can comment on one answer.

The impressive behavior is that it remembers the earlier encounter,
compares evidence across time, avoids overstating the pattern, and asks
the teacher to make the consequential judgment.

------------------------------------------------------------------------

## 14. How this grows

The same architecture can support:

-   recurring vocabulary difficulties in language learning;
-   repeated reasoning gaps in mathematics;
-   misunderstandings in scientific explanations;
-   weak evidence use in history or social studies;
-   repeated problems with planning, revision, or argument structure in
    writing;
-   practical-skill development in vocational courses;
-   student self-reflection over a term;
-   teacher dashboards showing class-wide patterns without reducing
    students to scores.

Future versions could add:

-   student-facing progress narratives;
-   teacher-defined learning objectives;
-   multiple evidence types, including written work, oral responses, and
    project artifacts;
-   spaced follow-up activities;
-   class-level summaries;
-   explicit student correction of inaccurate records;
-   privacy controls and retention policies;
-   support for multiple teachers or courses.

The architecture should remain evidence-first and human-supervised as it
grows.

------------------------------------------------------------------------

## 15. What you are least sure about

The least certain parts of the project are:

1.  **Cross-subject consistency.**\
    Extracting and comparing learning signals may be easier in some
    subjects than others.

2.  **Concept alignment.**\
    Two assignments may use different language for the same skill, or
    the same word for different skills.

3.  **Recurrence thresholds.**\
    Two similar observations may be enough in one context but
    insufficient in another.

4.  **Teacher trust.**\
    Teachers may need transparent evidence and simple explanations
    before they trust the system.

5.  **Student response to review.**\
    Students may disagree with a record or may not want to answer
    clarification questions.

6.  **False positives.**\
    The agent may mistake a difficult assignment, unusual prompt, or
    temporary lapse for a persistent learning gap.

7.  **False negatives.**\
    The agent may miss a recurring issue when the student's wording
    changes.

8.  **Operational cost.**\
    Repeated retrieval, comparison, checking, and revision may increase
    latency and model usage.

These uncertainties should be tested rather than hidden.

------------------------------------------------------------------------

## 16. Claims to verify

Before treating the prototype as reliable, verify:

-   whether the selected model can consistently produce the required
    structured outputs;
-   whether the model cites the correct passages from student work;
-   whether the comparison step distinguishes recurrence from
    superficial similarity;
-   whether the checker catches unsupported or overly strong claims;
-   whether the state machine resumes correctly after human review;
-   whether records remain durable across separate runs;
-   whether duplicate submissions are handled safely;
-   whether teacher corrections are preserved in the audit trail;
-   whether the workflow performs acceptably across multiple subjects;
-   whether students and teachers understand the wording of provisional
    findings;
-   whether privacy, retention, and access controls are appropriate for
    student data;
-   whether the demo's second encounter truly depends on stored history
    rather than hidden hard-coded context.

The strongest claim the prototype should make is modest:

> It can maintain an evidence-backed learning history across encounters
> and use that history to surface possible recurring learning gaps for
> human review.

It should not claim that it can fully understand a student, diagnose
misconceptions with certainty, or replace a teacher.

------------------------------------------------------------------------

## Before you call it done

-   [ ] The system remembers a student's earlier attempt in a later run.
-   [ ] The second encounter produces a meaningfully different result
    because of that history.
-   [ ] Every important finding is tied to evidence.
-   [ ] The checker can reject unsupported claims.
-   [ ] The system distinguishes a first signal from a recurring
    pattern.
-   [ ] The system can pause for teacher review.
-   [ ] The teacher remains responsible for consequential decisions.
-   [ ] The record preserves corrections and uncertainty.
-   [ ] The workflow is demonstrated with a subject other than
    mathematics.
-   [ ] The design can plausibly be adapted to multiple subjects.
