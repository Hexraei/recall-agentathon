# Recall — Frontend UI Context

**Purpose of this document.** This is the complete, self-contained description of the
Recall mobile app's screens, flows and interaction rules. It exists to be handed to a
visual UI design tool (Galileo AI, Uizard, Figma AI or similar) as the basis for a design
brief, and to whoever directs that tool. It describes *what each screen does and contains*.
It does not prescribe colours, typography or visual mood — that direction is still open and
is recorded as such in §10.

**Status:** workflow and screen inventory finalised. Visual style pending.

---

## 1. What the app is

Recall is a mobile quiz application for a university course. A teacher builds a
multiple-choice quiz, launches it to a class, and students take it on their phones within a
fixed time window. After the quiz closes, both sides get analysis: the teacher sees how the
class and each individual student performed — including learning gaps that recur across
multiple quizzes over the semester — and the student sees their own performance and what to
work on next.

Kahoot is the reference point for the *join-by-PIN, teacher-hosts, students-play-on-phones*
mechanic only. Recall is not a copy of Kahoot and deliberately drops its game-show
elements: there are no leaderboards, no rankings, no podium, and no per-question countdown
pressure. The emphasis is on the analysis after the quiz, not on competition during it.

**Platform:** Flutter, single codebase. Both teacher and student use the same app on a
phone or tablet; there is no separate projector or desktop host screen.

**Scope note:** this document covers the frontend only. Backend, real-time transport and
the AI analysis engine are out of scope here.

---

## 2. Roles and identity

There are two roles, distinguished by account:

| Role | Also called | What they do |
|---|---|---|
| Teacher | host, professor | Builds quizzes, launches them, monitors progress, reviews analysis and confirms flagged learning gaps |
| Student | player | Joins a quiz by PIN, answers questions, views their own results and progress |

**Identity is persistent.** Both roles sign in to an account. This is essential, not
cosmetic: the analysis layer tracks a student's performance across many quizzes over a
semester, which is impossible with throwaway nicknames. A student's role and identity are
known at login, so the join flow asks for a PIN only — never a nickname.

After login, each role lands on its own home dashboard. The dashboard is the hub: every
flow is entered from it and returns to it.

---

## 3. Quiz model and rules

These rules govern the whole design. They are decisions, not suggestions.

1. **Every question is 4-option multiple choice.** Exactly four options, labelled A, B, C,
   D. One is correct. There is no true/false variant, no free-text answer, no image
   question, no poll.
2. **Answer options are compact, contained cards.** Each option is a bounded card
   containing its label and its full text. Options are *not* colour-coded, *not*
   shape-coded, and the screen is *not* divided into four equal blocks. Splitting the
   screen into four coloured quadrants is explicitly rejected as a waste of space.
3. **There is no per-question timer.** The quiz has one deadline for the whole attempt,
   set as a duration in minutes and counted from the moment the teacher starts the
   session. When it expires, every in-progress attempt auto-submits.
4. **The quiz is self-paced within that window.** The teacher does not advance questions.
   Each student moves forward and backward through the questions at their own speed.
5. **Answers stay editable until submission.** A student can revisit any question and
   change their answer right up to the moment they submit or the deadline auto-submits.
6. **There is no leaderboard, ranking or podium anywhere in the app.** Students are never
   shown their standing relative to peers, during or after the quiz.
7. **Results appear only after the quiz window closes.** On submitting, a student sees a
   confirmation that their attempt was received, not a score. The score and per-question
   breakdown become available once the window has closed for everyone.
8. **Learning gaps are candidates until a teacher confirms them.** A flagged recurring gap
   is shown to the teacher for review first. Only after the teacher confirms it does any
   corresponding next step reach the student.

---

## 4. Navigation map

```
Splash
  └── Login / Sign up
        │
        ├──────────────► TEACHER HOME DASHBOARD ◄──────── (returns here from every flow)
        │                  ├── Host a quiz ──► Host Lobby ──► Live Monitor ──► Quiz Results
        │                  ├── My quizzes ──► Quiz Builder
        │                  ├── Class Analytics ──► Individual Student Analytics
        │                  └── Review Findings
        │
        └──────────────► STUDENT HOME DASHBOARD ◄──────── (returns here from every flow)
                           ├── Join a quiz ──► Student Lobby ──► Question View
                           │                        ──► Review & Submit ──► Submitted
                           ├── My results ──► Quiz Result
                           └── My performance
```

The quiz-taking flow (Student Lobby through Submitted) and the hosting flow (Host Lobby
through Live Monitor) are full-screen takeovers: no dashboard navigation is visible while a
session is live.

---

## 5. Teacher workflow, end to end

1. Teacher signs in and lands on the **Teacher Home Dashboard**.
2. Opens **My Quizzes** and creates a new quiz, or selects an existing one to edit.
3. In the **Quiz Builder** they set a title and a duration in minutes, then compose
   questions one at a time — question text, four options, mark which is correct — appending
   each to a running list they can edit, delete and reorder. They save the quiz.
4. From the dashboard they choose **Host a quiz** and pick a saved quiz. The **Host Lobby**
   opens, showing a join PIN and a list of students as they join in real time.
5. When ready, the teacher starts the session. The countdown begins for everyone at once.
6. The **Live Monitor** replaces the lobby, showing time remaining and how many students
   have joined, are in progress, and have submitted, with a per-student status list. The
   teacher can end the quiz early.
7. When the window closes, **Quiz Results** shows how the class did on that specific quiz:
   participation, score distribution, and which questions were answered worst.
8. Later, **Class Analytics** shows the longitudinal picture across all quizzes so far —
   performance trends and the concepts the class is weakest on — with a student roster.
9. Selecting a student opens **Individual Student Analytics**: that student's history,
   concept-level gaps over time, and any flagged recurring patterns.
10. **Review Findings** presents flagged gaps as candidates with their supporting evidence.
    The teacher confirms, revises or rejects each one. Confirmation is what releases a next
    step to the student.

---

## 6. Student workflow, end to end

1. Student signs in and lands on the **Student Home Dashboard**.
2. Chooses **Join a quiz** and enters the PIN the teacher displayed. No nickname is asked
   for — the account already identifies them.
3. The **Student Lobby** confirms they are in and shows what they are about to take (quiz
   title, number of questions, duration), then waits for the teacher to start.
4. The quiz starts and the **Question View** opens on question 1, with the whole-quiz
   countdown visible. They select one of four option cards, and move between questions
   freely with previous/next.
5. At any point they can open **Review & Submit**, which shows every question number marked
   answered or unanswered, and lets them jump back to any of them.
6. They submit, confirming in a dialog. If they do not submit before the deadline, their
   attempt auto-submits with whatever is answered.
7. **Submitted Confirmation** tells them the attempt was received and that results come
   when the quiz closes. No score is shown yet.
8. Once the window closes, **Quiz Result** shows their score, which questions they got
   right and wrong, and the correct answers.
9. **My Performance** shows the longitudinal view: their score history across quizzes, the
   concepts they are strong in, the concepts to work on, and next steps — but only next
   steps the teacher has confirmed.

---

## 7. Screen inventory and specifications

Nineteen screens. The inventory below is the working checklist: screens are designed one at
a time, in this order, each finished before the next begins. The detailed specification for
each follows in §7.1 onwards, numbered to match.

### Inventory

| # | Screen | Role | What it is for | Designed |
|---|---|---|---|---|
| 1 | Splash | shared | Launch and session restore | ☐ |
| 2 | Login / Sign up | shared | Authenticate and establish role | ☐ |
| 3 | Teacher Home Dashboard | teacher | Hub: host, quizzes, analytics, review | ☐ |
| 4 | My Quizzes | teacher | Library of saved quizzes | ☐ |
| 5 | Quiz Builder | teacher | Compose a quiz, appending questions | ☐ |
| 6 | Host Lobby | teacher | Show PIN, watch students join, start | ☐ |
| 7 | Live Monitor | teacher | Track progress while the window is open | ☐ |
| 8 | Quiz Results | teacher | How the class did on one quiz | ☐ |
| 9 | Class Analytics | teacher | Longitudinal view across all quizzes | ☐ |
| 10 | Individual Student Analytics | teacher | One student across the course | ☐ |
| 11 | Review Findings | teacher | Confirm, revise or reject flagged gaps | ☐ |
| 12 | Student Home Dashboard | student | Hub: join, results, performance | ☐ |
| 13 | Join | student | PIN entry | ☐ |
| 14 | Student Lobby | student | Confirm joined, wait for start | ☐ |
| 15 | Question View | student | Answer questions, self-paced | ☐ |
| 16 | Review & Submit | student | Overview of answered, then submit | ☐ |
| 17 | Submitted Confirmation | student | Acknowledge receipt, no score yet | ☐ |
| 18 | Quiz Result | student | Own outcome on one quiz, after close | ☐ |
| 19 | My Performance | student | Own longitudinal progress and next steps | ☐ |

### Order of work

The numbering follows the user's journey and is the default order to design in. Three
screens carry most of the design language and are worth settling early, because every other
screen inherits from them:

- **Screen 15, Question View** — the most-used screen in the app, and the one that defines
  the option card, the countdown and the question layout.
- **Screens 3 and 12, the two dashboards** — they set the navigation pattern, card style
  and typographic hierarchy that the rest of the app repeats.

Once those three are settled, the remaining sixteen are variations on an established
language rather than fresh decisions.

### Specifications

For each screen: what it is for, what it contains, what the user can do, and the states it
must handle.

### 7.1 Splash — shared

Brief launch screen while the session is restored.
- Contains: app name/logo lockup ("Recall"), loading indicator.
- States: loading; failed-to-connect (retry).

### 7.2 Login / Sign up — shared

Authenticates the user and establishes their role.
- Contains: app identity, identifier field (email or roll number), password field, primary
  sign-in action, link to switch to sign-up.
- Sign-up additionally asks for a display name and a role choice (teacher or student).
- Actions: sign in, switch to sign-up, recover password.
- States: idle; submitting; invalid credentials; field-level validation errors; network
  failure.

### 7.3 Teacher Home Dashboard

The teacher's hub.
- Contains: greeting with the teacher's name; four primary entry points — **Host a quiz**,
  **My quizzes**, **Class analytics**, **Review findings**. The Review findings entry
  carries a badge with the number of findings awaiting review. A compact summary of recent
  activity (most recent quiz, when it ran, participation) sits below.
- Actions: open any of the four sections; sign out.
- States: default; no quizzes created yet (the summary area shows an invitation to build a
  first quiz); nothing awaiting review (no badge).

### 7.4 My Quizzes — teacher

The library of saved quizzes.
- Contains: a list of quizzes, each row showing title, number of questions, duration, and
  when it was last run; a prominent action to create a new quiz.
- Actions: create new quiz; open a quiz to edit; host a quiz directly from its row; delete
  a quiz.
- States: populated; empty (first-run invitation to create a quiz); deleting (confirm).

### 7.5 Quiz Builder — teacher

Where a quiz is composed, question by question. This screen carries the most interaction
complexity in the teacher flow.
- Contains, top to bottom:
  - Quiz title field.
  - Duration field, in minutes, applying to the whole quiz. Label it so it is unmistakably
    a deadline for the entire attempt, not a per-question limit.
  - A question composer: question text input, four option inputs labelled A to D, and a
    single-select control marking which option is correct.
  - An "Add question" action that appends the composed question to the list and clears the
    composer for the next one.
  - The running list of questions already added, each row showing its number and question
    text, with edit, delete and reorder affordances.
  - A save action for the whole quiz.
- Actions: compose and append a question; edit an existing question inline or in place;
  delete a question; reorder questions; save; discard.
- States: empty (no questions added yet — the list area explains that added questions
  appear here); composing; validation errors (question text empty, fewer than four options
  filled, no correct option marked); unsaved-changes warning on leaving; saving.
- Explicitly absent: any per-question time setting.

### 7.6 Host Lobby — teacher

The waiting room before a session starts.
- Contains: the join PIN, displayed as the dominant element on the screen and easily read
  aloud or shown to a room; the quiz title, its question count and its duration; a live
  count and list of students as they join; a start action.
- Actions: start the session; cancel and return to the dashboard.
- States: no students joined yet (start disabled, with an explanation); students joining
  (each arrival appears in the list); starting.

### 7.7 Live Monitor — teacher

Replaces the lobby once the session is running. It monitors progress; it does not display
questions, because the teacher does not drive the pacing.
- Contains: time remaining, as the most prominent element; three status counts — joined, in
  progress, submitted; a per-student list showing each student's name and their progress
  (for example, answered 7 of 15, or submitted); an action to end the quiz early.
- Actions: end the quiz early (with confirmation, warning that in-progress attempts will be
  auto-submitted); leave the monitor without ending the quiz.
- States: running; approaching deadline (time remaining should become visually more urgent
  in the final minutes); all students submitted before the deadline (offer to close early);
  closing; closed.

### 7.8 Quiz Results — teacher

How the class did on one specific quiz, available once its window has closed.
- Contains: quiz title and when it ran; participation (how many of the class took it);
  overall class performance, shown as a distribution rather than a single average alone;
  a per-question breakdown ordered so the worst-answered questions are easy to find, each
  showing the question text and the proportion who answered it correctly; the ability to
  open an individual student's analysis.
- Actions: open a question for detail (which options were chosen); open a student; go to
  Class Analytics.
- States: populated; partial participation (make clear how many did not attempt).
- Explicitly absent: any ranked list of students by score.

### 7.9 Class Analytics — teacher

The longitudinal view across every quiz the class has taken. This is a different screen
from Quiz Results: that one is about a single session, this one is about the semester.
- Contains: class performance trend over successive quizzes; the concepts the class is
  weakest on, aggregated across quizzes; a student roster where each student can be opened,
  with an indicator on students who have flagged patterns awaiting review; a filter by quiz
  or by date range.
- Actions: open a student; filter; open Review Findings.
- States: populated; too few quizzes to show a trend (explain that trends appear after more
  quizzes rather than showing an empty chart); no data at all.

### 7.10 Individual Student Analytics — teacher

One student, across the whole course.
- Contains: the student's name and identifier; their score history across quizzes; a
  concept-level breakdown showing where they are strong and where they struggle, and how
  that has changed over time; a list of flagged patterns for this student, each marked as
  candidate, confirmed or rejected, with the evidence it rests on (which quizzes, which
  questions); an entry point into reviewing any candidate.
- Actions: open a flagged pattern to review it; view a specific past attempt.
- States: populated; new student with only one attempt (no pattern can exist yet — say so
  explicitly rather than showing an empty section); no flagged patterns.

### 7.11 Review Findings — teacher

The decision queue. This screen is where the teacher, not the system, decides whether a
flagged learning gap is real.
- Contains: a queue of candidate findings. Each finding shows: the student it concerns; a
  plainly worded statement of the gap; the supporting evidence — the specific questions
  across specific quizzes that led to it; a note on what remains uncertain; and three
  actions — confirm, revise, reject.
- Actions: confirm (the finding becomes confirmed, and its next step is released to the
  student); revise (edit the statement or its proposed next step before confirming);
  reject (dismiss it, optionally with a reason); skip for now.
- States: queue populated; empty queue (nothing awaiting review); submitting a decision;
  revise mode (editable statement and next step).
- Language constraint for any placeholder copy: findings describe *work*, never the person.
  "Has repeatedly miscounted operations inside nested loops" is acceptable phrasing; "does
  not understand time complexity" or anything describing ability, character or capacity is
  not.

### 7.12 Student Home Dashboard

The student's hub.
- Contains: greeting with the student's name; a prominent **Join a quiz** action; **My
  results** (past quizzes and their outcomes); **My performance** (the longitudinal view).
  If a quiz they can join is currently live, a banner surfaces it.
- Actions: join a quiz; open results; open performance; sign out.
- States: default; no quizzes taken yet; a live quiz available.

### 7.13 Join — student

PIN entry. Nothing else, because the account already identifies the student.
- Contains: a single prominent PIN input sized for quick entry; a join action; brief
  instruction on where the PIN comes from.
- Actions: enter PIN and join; cancel.
- States: idle; validating; invalid PIN; quiz already closed; quiz already started (decide
  whether late entry is permitted and surface it here); already submitted this quiz.

### 7.14 Student Lobby

Confirms the student is in, and waits for the teacher to start.
- Contains: confirmation that they have joined; the quiz title, its number of questions and
  its duration, so they know what they are about to take; a waiting indicator; optionally
  how many others have joined.
- Actions: leave the lobby.
- States: waiting; starting (transition into question 1).

### 7.15 Question View — student

The core screen of the student experience.
- Contains:
  - A persistent header with time remaining for the whole quiz and the position in the quiz
    (for example, question 4 of 15).
  - The question text.
  - Four option cards, stacked. Each card is a bounded container holding its label (A, B, C
    or D) and its full option text. No colour coding. No shape icons. No four-way split of
    the screen.
  - Previous and next navigation, and a way to open Review & Submit.
- Actions: select an option; change a previously selected option; move to the previous or
  next question; jump to review.
- States: unanswered; answered (the selected card is clearly distinguished from the other
  three); first question (previous disabled); last question (next leads to review);
  deadline approaching (the countdown becomes more urgent); auto-submitting at deadline.
- Explicitly absent: per-question countdown, right/wrong feedback, points, score, any
  indication of how others are doing.

### 7.16 Review & Submit — student

The overview before committing.
- Contains: a grid of every question number, each marked answered or unanswered; a count of
  how many remain unanswered; the time remaining; a submit action.
- Actions: jump back to any question by tapping its number; submit, via a confirmation
  dialog that names how many questions are unanswered.
- States: all answered; some unanswered (submission still allowed, but the dialog must say
  what is being left blank); submitting.

### 7.17 Submitted Confirmation — student

- Contains: confirmation that the attempt was received; a clear statement that results
  become available once the quiz closes for everyone; time remaining until that happens; a
  way back to the dashboard.
- States: submitted manually; auto-submitted at the deadline (say so, and say what was
  captured).
- Explicitly absent: score, correctness, rank.

### 7.18 Quiz Result — student

Their own outcome on one quiz, available after the window closes.
- Contains: the quiz title and when it ran; their score; a per-question list marking each
  right or wrong, showing what they chose and what the correct answer was; optionally a
  short concept-level summary of the quiz.
- Actions: open My Performance; return to results list.
- States: available; not yet available (quiz still open — explain when it will be);
  auto-submitted attempt (note any unanswered questions).
- Explicitly absent: class rank, percentile, or comparison to named peers.

### 7.19 My Performance — student

The longitudinal view of their own learning.
- Contains: score history across quizzes over the semester; the concepts they are
  consistently strong in; the concepts to work on; and next steps — concrete, actionable,
  and shown only where the teacher has confirmed the underlying finding.
- Actions: open an individual quiz result; open a suggested next step.
- States: populated; only one quiz taken so far (no trend or pattern yet — say so plainly);
  no confirmed next steps yet.
- Explicitly absent: peer comparison of any kind; any statement about the student's ability,
  intelligence or character. Everything shown describes their *work*.

---

## 8. Cross-cutting elements

**The countdown.** A single, consistent time-remaining component appears on the student's
Question View and Review & Submit screens, and on the teacher's Live Monitor. It counts down
to one deadline for the whole quiz. It must become visibly more urgent as the deadline
nears, and it must never be mistaken for a per-question timer.

**Auto-submit.** When the deadline is reached, in-progress student attempts submit
automatically. Design for a warning as the deadline approaches, and for the moment of
auto-submission itself, which takes the student to Submitted Confirmation with an
explanation that it happened automatically.

**Option cards.** The same option card component is used on every question. Its states are:
unselected, selected, and — on the results screen only — correct and incorrect.

**Empty and first-run states.** Several screens have a meaningful "not yet" condition that
must be designed rather than left blank: a teacher with no quizzes, a review queue with
nothing in it, a student with one attempt and therefore no possible pattern, a class with
too few quizzes to show a trend. Each should explain the condition rather than showing an
empty container.

**Loading and error states.** Every screen that fetches data needs a loading state and a
recoverable error state.

**Live-updating lists.** The Host Lobby's joined-students list and the Live Monitor's
per-student progress list both update while the teacher watches. Design for items appearing
and changing, not for a static snapshot.

---

## 9. What this design must not include

These are exclusions, and they are deliberate. Designing any of them would contradict a
decision already taken.

1. **No leaderboard, ranking, podium or peer comparison**, at any point, for either role.
2. **No per-question timer** — one deadline for the whole quiz, and nothing that implies
   otherwise.
3. **No colour-coded or shape-coded answer options**, and no four-quadrant split of the
   answer screen.
4. **No free-text answer input** — every question is four-option multiple choice.
5. **No immediate right/wrong feedback during the quiz** — results come after the window
   closes.
6. **No nickname entry** — identity comes from the account.
7. **No teacher-driven question advancement** — the student sets the pace.
8. **No student-facing next step that the teacher has not confirmed.**
9. **No language describing a student's ability, character or capacity** anywhere in the
   interface copy — findings and feedback describe work.
10. **No question types beyond four-option multiple choice**, no team mode, no streaks or
    bonus mechanics.

---

## 10. Open item

**Visual style and mood are not yet decided.** Colour palette, typography, illustration
style, motion and overall tone are still to be chosen, and reference material is being
gathered. Until that is settled, this document should be treated as the structural and
behavioural half of the brief; the visual direction will be appended before it goes to a
design tool.

One observation that should inform that choice: with rankings and countdown pressure
removed, and the analysis layer carrying most of the product's value, this app sits closer
to a considered assessment-and-feedback tool than to a game show. A visual direction
borrowed wholesale from Kahoot would misrepresent what the product actually does.
