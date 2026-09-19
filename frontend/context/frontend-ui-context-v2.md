# Recall — Frontend UI Context (v2, as built)

**Purpose of this document.** This is the complete, self-contained description of the Recall
mobile app's screens, flows and interaction rules. Version 1 described what to design;
this version describes what exists. All nineteen screens are drawn, as 77 artboards on the
Recall — UI design canvas. Where the build departs from v1, this document follows the
build and says so.

**Status:** workflow, screen inventory and all screen states drawn. Visual direction used
throughout is a candidate, not an agreed brand — see §10.

---

## 1. What the app is

Recall is a mobile quiz application for a university course. A teacher builds a
multiple-choice quiz, launches it to a class, and students take it on their phones within a
fixed time window. After the quiz closes, both sides get analysis: the teacher sees how the
class performed and which topics it stumbled on, including gaps that recur across quizzes
over the semester, and the student sees their own work and what to look at next.

Kahoot is the reference point for the *join-by-PIN, teacher-hosts, students-play-on-phones*
mechanic only. Recall deliberately drops the game-show elements: no leaderboards, no
rankings, no podium, no per-question countdown pressure. The emphasis is on the analysis
after the quiz, not on competition during it.

**Platform:** Flutter, single codebase. Both roles use the same app on a phone; there is no
separate projector or desktop host screen. Artboards are 390 × 844, taller where the screen
scrolls.

**Scope:** frontend only. Backend, real-time transport and the analysis engine are out of
scope, though §10 lists the points where the design assumes something of them.

---

## 2. Roles and identity

| Role | Also called | What they do |
|---|---|---|
| Teacher | host, professor | Builds quizzes, hosts them, monitors progress, reads the class analysis, accepts or rejects class-level gaps |
| Student | player | Joins by PIN, answers questions, views their own results and progress |

**Identity is persistent.** Both roles sign in to an account. This is essential, not
cosmetic: the analysis layer tracks a student across many quizzes, which is impossible with
throwaway nicknames. Role comes from the account, so sign-in asks for an identifier and a
password only, and the join flow asks for a PIN only.

Role is chosen once at sign-up, presented as permanent. That permanence is an assumption in
the design, not a decision taken elsewhere.

After login each role lands on its own home dashboard. The dashboard is the hub: every flow
is entered from it and returns to it.

---

## 3. Quiz model and rules

These rules govern the whole design. They are decisions, not suggestions.

1. **Every question is 4-option multiple choice.** Exactly four options, labelled A, B, C,
   D. One is correct. No true/false, no free text, no image question, no poll.
2. **Answer options are compact, contained cards.** A bounded container with a letter badge
   and the full option text, minimum 60px tall. Options are *not* colour-coded, *not*
   shape-coded, and the screen is *not* divided into four blocks.
3. **There is no per-question timer.** One deadline covers the whole attempt, set in minutes
   in the builder and counted from the moment the teacher starts. At expiry every
   in-progress attempt auto-submits.
4. **The quiz is self-paced within that window.** The teacher does not advance questions.
5. **Answers stay editable until submission**, manual or automatic.
6. **No leaderboard, ranking or podium anywhere**, during or after, for either role.
7. **Results appear only after the window closes for everyone.** Submitting produces a
   receipt, not a score.
8. **Learning gaps are class-level and are candidates until the teacher accepts them.**
   *(Changed from v1.)* A gap describes what a share of the class did — "19 of 42 students
   chose an answer that assumes no two keys share a slot" — never what one student is like.
   Individual patterns are the backend's business and carry no review status in the UI.
9. **Every question carries one topic.** *(New in v2.)* Topics are chosen in the builder
   from a combobox that filters existing topics as you type. Topics are the unit that
   results, analytics, findings and performance all aggregate by; without them nothing in
   the app could name a concept.
10. **A quiz is known by the name its teacher gave it** — "Hash tables", "Graphs" — with any
    week marker living in the meta line beside the date.
11. **Interface copy describes a student's work, never their ability or character.**

---

## 4. Navigation map

```
Splash
  └── Login / Sign up
        │
        ├──────────────► TEACHER HOME DASHBOARD ◄──────── (returns here from every flow)
        │                  ├── Host a quiz ──► Host Lobby ──► Live Monitor ──► Quiz Results
        │                  │                                         └── topic ──► question sheet
        │                  ├── My quizzes ──► Quiz Builder
        │                  ├── Class Analytics ──► topic page ──► Review Findings
        │                  │                   └── roster ──► Individual Student Analytics ──► attempt
        │                  └── Review Findings
        │
        └──────────────► STUDENT HOME DASHBOARD ◄──────── (returns here from every flow)
                           ├── Join a quiz ──► Student Lobby ──► Question View
                           │                        ──► Review & Submit ──► Submitted
                           ├── My results ──► Quiz Result
                           └── My performance ──► Quiz Result
```

The quiz-taking flow (Join through Submitted) and the hosting flow (Host Lobby through Live
Monitor) are full-screen takeovers: no dashboard navigation is visible while a session is
live. Takeovers replace the back chevron with a plain text action at top left — Cancel,
Leave, Exit quiz, Back to questions.

---

## 5. Teacher workflow, end to end

1. Signs in and lands on the **Teacher Home Dashboard**. Host a quiz is a filled accent card
   on its own; My quizzes, Class analytics and Review findings sit in one list below it,
   each carrying a live secondary line.
2. Opens **My Quizzes** and creates a new quiz or edits an existing one. Hosting is also
   available directly from each row.
3. In the **Quiz Builder** they set a title and a time limit for the whole quiz, then
   compose questions one at a time — question text, one topic, four options, the correct one
   marked by a radio on its row — appending each to a list they can edit and delete.
4. From the dashboard they choose **Host a quiz**. The **Host Lobby** shows a six-digit PIN
   and students appearing as chips as they join.
5. They start the session. The deadline begins for everyone at once.
6. The **Live Monitor** replaces the lobby: countdown, three counts (Joined, Answering,
   Submitted), and per-student rows stating progress in words. Exiting the monitor ends the
   quiz — *(changed from v1)* there is no way to leave it with the session still running.
7. When the window closes, **Quiz Results** shows participation, the score distribution,
   and topics worst-first. A topic opens its own page of that topic's questions; a question
   opens the split across all four options.
8. **Class Analytics** shows the longitudinal picture: class average per quiz, topics
   aggregated worst-first, and an A-to-Z roster showing attendance, never a score. Each
   topic opens a class-level topic page carrying that topic's gaps.
9. A gap opens **Review Findings**, a queue of one class gap at a time with its evidence and
   what is uncertain. The teacher accepts or rejects each one; rejecting takes an optional
   reason. *(Changed from v1: no "revise".)*
10. From the roster, **Individual Student Analytics** shows one student's own score per
    quiz, a correct-out-of-total table by topic across two time windows, and each past
    attempt question by question.

---

## 6. Student workflow, end to end

1. Signs in and lands on the **Student Home Dashboard**, which mirrors the teacher's: a
   filled accent card for Join a quiz, a list for My results and My performance, and a
   Latest result card. When a quiz is open, a banner surfaces it.
2. Chooses **Join a quiz** and types the PIN. No nickname is asked for. The screen handles a
   PIN that matches nothing, a quiz that has closed, a quiz already submitted, and a quiz
   that has already started.
3. The **Student Lobby** names the quiz, gives question count and duration, and waits. One
   status block carries the state; a "How it works" list sits at the bottom.
4. The quiz starts and the **Question View** opens, with the whole-quiz countdown and the
   position in the quiz in one header. They select one of four option cards and move with
   Previous and Next.
5. At any point they open **Review & Submit**: a grid of every question number marked
   answered or not, with a jump back to any of them.
6. They submit. Submitting with blanks is allowed; the confirmation names which questions
   are blank and warns the attempt cannot be reopened. If they do not submit before the
   deadline, the attempt auto-submits with whatever is answered.
7. **Submitted Confirmation** is a receipt: what was answered, when, when the quiz closes.
   No score. The auto-submitted variant says the time ran out and what was left blank.
8. Once the window closes, **Quiz Result** shows their score as a count, a breakdown by
   topic, and every question with what they chose and, when wrong, the correct answer.
9. **My Performance** shows their score history, topics split into Steady and To work on,
   and the list of their past results.

---

## 7. Screen inventory and specifications

Nineteen screens, 77 artboards. *(Changed from v1: screens 10 and 11 are swapped, so the
flow runs Class Analytics → Review Findings → Individual Student Analytics.)*

### Inventory

| # | Screen | Role | Artboards |
|---|---|---|---|
| 1 | Splash | shared | 2 |
| 2 | Login / Sign up | shared | 5 |
| 3 | Teacher Home Dashboard | teacher | 3 |
| 4 | My Quizzes | teacher | 3 |
| 5 | Quiz Builder | teacher | 5 |
| 6 | Host Lobby | teacher | 3 |
| 7 | Live Monitor | teacher | 5 |
| 8 | Quiz Results | teacher | 4 |
| 9 | Class Analytics | teacher | 9 |
| 10 | Review Findings | teacher | 5 |
| 11 | Individual Student Analytics | teacher | 3 |
| 12 | Student Home Dashboard | student | 3 |
| 13 | Join | student | 7 |
| 14 | Student Lobby | student | 3 |
| 15 | Question View | student | 6 |
| 16 | Review & Submit | student | 4 |
| 17 | Submitted Confirmation | student | 2 |
| 18 | Quiz Result | student | 3 |
| 19 | My Performance | student | 2 |

### Specifications

For each screen: what it is for, what it contains, what the user can do, and the states
drawn.

### 7.1 Splash — shared

- Contains: the Recall lockup, a loading indicator.
- States: loading while the session restores; cannot connect, with a retry.

### 7.2 Login / Sign up — shared

- Contains: identifier and password fields, sign in, password recovery, a route to sign up.
  Role is not asked on sign-in.
- Sign up adds a two-card role choice, presented as permanent.
- States: idle; submitting; invalid credentials, with recovery re-labelled "Reset your
  password"; network failure, in the neutral band rather than red, with an inline retry;
  sign up.
- Sets the shared control vocabulary: 52px inputs and buttons, hairline borders, 10px
  radius, label above field, error text below.

### 7.3 Teacher Home Dashboard

- Contains: greeting and name, sign out, Host a quiz as a filled accent card, a list of My
  quizzes / Class analytics / Review findings each with a live secondary line, and a Recent
  activity card naming the last quiz, its participation and its worst question.
- The Review findings badge is an accent pill, not red: it is a queue count, not an error.
- States: default; nothing to review, with the badge gone; first run, where the invitation
  card becomes the primary and all four entry points grey out with a line saying what
  unlocks them.

### 7.4 My Quizzes — teacher

- Contains: rows of title, "15 questions · 20 min", and last-run ("Not run yet" if never),
  each with an outlined Host pill and a kebab for edit and delete.
- States: populated; confirm delete, as a bottom sheet over a dimmed list with a red Delete
  and an outlined "Keep it"; empty.
- The delete copy warns that results and the analysis built from the quiz go too. That
  cascade is an assumption in the design.

### 7.5 Quiz Builder — teacher

- Contains: quiz details (title, time limit for the whole quiz with helper text stating it
  counts once for everyone and there is no per-question timer), then the question composer —
  question text, topic combobox, four option rows each with a radio marking the correct one
  — and a running list of added questions each showing its topic as a pill.
- Add question is outlined, Save quiz is filled. Outlined means a repeatable step, filled
  means commit; that distinction holds app-wide.
- States: no questions yet, with a dashed empty slot; composing; validation errors shown per
  field, with Add question disabled until all are resolved; saving; leaving with unsaved
  changes, where Keep editing is the filled action and Discard is a red outline.
- To build: the composer should carry the last topic forward to the next question, and topic
  matching should be case-insensitive substring.

### 7.6 Host Lobby — teacher

- Full-screen takeover; top left is Cancel.
- Contains: the quiz name and its counts; the PIN in a white card at 52px with 6px
  letter-spacing, grouped as two blocks of three, set in the sans because it is read aloud
  and typed; one line phrased as what the student does; joined students as initial chips
  with the most recent tinted; a live count with a pulsing dot.
- States: nobody joined, with Start disabled and a dashed placeholder; students joining;
  starting, with the action busy and a line saying question 1 is being sent.
- The helper line under Start avoids mentioning latecomers, since late entry is undecided.

### 7.7 Live Monitor — teacher

- Contains: the countdown as the hero figure in tabular numerals labelled "Time left"; a
  live dot and "Running"; three stat tiles — Joined, Answering, Submitted; per-student rows
  stating progress in words, including "All 15 answered, not submitted", which a progress
  bar could not express; an outlined red End the quiz now.
- States: running; deadline near, where the countdown card turns red-tinted and says
  attempts submit themselves at 0:00; everyone submitted, where the primary becomes "Close
  the quiz now" with a quieter "Let it run to 0:00"; confirm ending early; closed, where the
  countdown becomes "Ran 20 minutes", an auto-submitted count appears as its own tile, and
  the primary becomes "See class results".
- *(Changed from v1.)* Top left is "Exit quiz", which opens the end-quiz confirmation,
  auto-submits every open attempt and closes the window. v1's "leave the monitor without
  ending the quiz" does not exist.

### 7.8 Quiz Results — teacher

- Contains: participation and median as two tiles; a score distribution column chart; then
  topics worst-first. *(Changed from v1: the screen does not list loose questions.)*
- A topic opens its own board with the topic's percentage, a line naming what is wrong, and
  its questions worst-first. A question opens a sheet showing all four options with the
  share who chose each — correct accent-filled with a check, the three wrong in neutral grey
  so the distractor that beat the answer is visible without being flattered.
- States: full participation; partial participation, which adds a neutral band saying how
  many never opened the quiz and states the denominator on every chart label; topic opened;
  one question opened.
- Median is shown beside participation because it survives the long tail of low scores that
  a mean does not.

### 7.9 Class Analytics — teacher

- Order on screen: filter, class average per quiz, topics across quizzes, students.
- The trend is a single-series column chart of class average per quiz, zero baseline, every
  bar labelled. Under three quizzes in view it becomes two stat tiles plus a note, not a
  chart.
- Topics are aggregated across the quizzes in view, worst-first, top five with "Show all".
  A topic row opens a class-level topic page holding that topic's percentage and its gaps:
  status (Awaiting review / Accepted / Rejected), a statement like "19 of 42 students
  chose…", and evidence as quiz plus question. No student names appear. A topic with a gap
  waiting carries a "1 to review" tag; a topic with none says "Nothing flagged."
- The roster is A to Z with search, showing attendance ("5 of 6 quizzes") and never a score,
  so it cannot read as a ranking.
- States: populated; filter open as a bottom sheet with a quiz checklist and From/To dates;
  too few quizzes for a trend; no quizzes closed yet; five topic pages.
- *(Changed from v1: no findings indicator on student rows.)*

### 7.10 Review Findings — teacher

*(Was 7.11 in v1.)*

- Contains: one class gap at a time with an "n of total" counter; the statement in the
  serif; "Where it showed up" as quiz, question, stem and how many chose it; "What is
  uncertain" in the neutral band; and the next step students would see.
- Actions: Accept, filled; Reject, outlined and neutral because dismissal is not
  destructive; Skip for now. Reject opens a sheet with an optional reason.
- States: a gap waiting; reject sheet; saving the decision; the next gap after accepting,
  with a confirmation line; nothing to review.
- The line "Nothing reaches students until you accept" stays on screen because it is the
  rule behind the screen. See §10 — it is currently untrue.
- *(Changed from v1: no "revise", and the queue holds class gaps, not student findings.)*

### 7.11 Individual Student Analytics — teacher

*(Was 7.10 in v1.)*

- Contains: the student's name and roll number with attendance; their own percentage per
  quiz as bars, with a dash for a quiz not taken; a correct-out-of-total table by topic
  split into two time columns; and a list of attempts.
- An attempt opens a page listing every question with the option chosen and the correct one.
- States: populated; one attempt only, which collapses to a single bar and a single topic
  column; one past attempt.
- No class average line anywhere, so no peer comparison.
- *(Changed from v1: flagged patterns and their statuses are gone from this screen.)*

### 7.12 Student Home Dashboard

- Contains: greeting and name, sign out, Join a quiz as a filled accent card, a list of My
  results and My performance, and a Latest result card naming the quiz, the date, "9 of 15
  answered correctly" and a link to the full result. No rank, no comparison, no next step.
- States: default; a quiz open, which adds a pulsing banner above the Join card naming the
  quiz, its question count and duration; first run, where an invitation card explains the
  steps in the teacher's own instructional voice and the two rows grey out.

### 7.13 Join — student

- Full-screen takeover; top left is Cancel.
- Contains: one 76px PIN field with 40px digits on a numeric keyboard, one line saying where
  the PIN comes from, and Join directly beneath the field so the keyboard never covers it.
  Join is disabled until six digits are entered.
- States: idle; PIN typed; checking; PIN not found — the only red state, shown on the field;
  quiz closed and already submitted, both in the neutral band with only "Back to home";
  quiz already started.
- The already-started board draws late entry as **allowed**: it shows the time left of the
  full duration, says the deadline is the same for everyone so there will be less time, and
  goes straight to the questions, skipping the lobby. This is an assumption — see §10.

### 7.14 Student Lobby

- Full-screen takeover; top left is Leave, with no confirmation, greyed out while starting.
- Contains: the quiz name as the page heading with "15 questions · 20 minutes" beneath it;
  one status block that is the only thing differing between states; and a "How it works"
  checklist at the bottom — answer in any order, change any answer until you submit, no
  timer on individual questions.
- States: waiting, with the pulsing dot and a count of others present (a count only, no
  names); starting, accent-tinted with a spinner; connection lost, in the neutral band with
  "Try again now".

### 7.15 Question View — student

- Contains: one header holding the countdown and "Question 4 of 15"; the question in the
  serif; four option cards; Previous and Next as equal-width buttons with a quieter "Review
  & submit" link beneath.
- Selected state is a 2px accent border, accent tint, filled letter badge and heavier text.
- States: unanswered; answered; first question, with Previous greyed; last question, where
  Next becomes "Review & submit"; deadline near, where the header turns red-tinted and says
  attempts submit themselves at 0:00; auto-submitting, an overlay stating the time is up and
  naming how many answers are being submitted.
- Absent by design: per-question countdown, right/wrong feedback, points, score, any
  indication of how others are doing.

### 7.16 Review & Submit — student

- Top left is "Back to questions".
- Contains: the countdown; a five-by-three grid of 52px question cells — answered in accent
  tint with an accent border, unanswered as a dashed outline on the ground colour — with a
  legend; one line stating the count in words; and Submit, never disabled.
- States: all answered; three unanswered; the confirmation sheet, which names the blank
  questions and says the attempt cannot be reopened, with "Submit anyway" filled and "Go
  back and finish them" outlined; submitting.

### 7.17 Submitted Confirmation — student

- Contains: an icon, a heading, one line, and a facts list.
- States: submitted by the student — answered, submitted at, quiz closes in; auto-submitted
  at the deadline — answered, left blank, submitted at the deadline.
- Both state that the result appears once the quiz closes for everyone and that nothing is
  marked before then. The auto board says "Time ran out" rather than blaming the student and
  confirms everything answered was saved.
- Absent by design: score, correctness, rank.

### 7.18 Quiz Result — student

- Contains: the quiz name and when it ran; the score as "11 of 15" in the serif with the
  percentage as a secondary line, over a fifteen-segment strip, one segment per question;
  a correct-out-of-total breakdown by topic; and every question with the stem, what was
  chosen, and — only when wrong — the correct answer. Correct is an accent check, wrong a
  grey cross; red is not used, because a wrong answer is not an error state.
- A link to My Performance sits at the bottom.
- States: available; auto-submitted, which adds "2 left blank when time ran out"; not yet
  available, which explains in the neutral band that the quiz is still open, says when the
  result lands, and shows what was submitted rather than an empty chart.
- Absent by design: class rank, percentile, comparison to named peers.

### 7.19 My Performance — student

- Contains: score history as the student's own percentage per quiz, with a dash and a line
  explaining a quiz not taken; topics split into "Steady" and "To work on", each row
  carrying correct out of total across quizzes; and "Your quizzes", the list of past results.
- Both topic headings describe the work: "Answered correctly most times these came up",
  "Answered wrongly more often than not".
- States: populated; one quiz only, which explains there is nothing to compare against yet
  and shows two stat tiles instead of a trend.
- *(Changed from v1: the "next steps from your teacher" section was removed at review, and
  with it the no-next-steps state. See §10.)*
- Absent by design: peer comparison of any kind; any statement about ability, intelligence
  or character.

---

## 8. Cross-cutting elements

**The countdown.** One component in three places — Live Monitor, Question View, Review &
Submit. Tabular numerals, labelled "Time left", counting to one deadline for the whole quiz.
It becomes red-tinted in the final minutes with a line stating that attempts submit
themselves at 0:00. It is never presented in a way that could read as a per-question timer.

**Auto-submit.** At the deadline, in-progress attempts submit themselves. The approach is
warned in the countdown; the moment itself is an overlay naming how many answers are being
sent; the destination is Submitted Confirmation, which says it happened automatically.

**Option cards.** One component on every question. States: unselected, selected, and — on
result screens only — correct and incorrect.

**The navigation list.** A white card with a hairline border and 14px radius, rows of icon,
title, one line of live secondary text, and a chevron. Set on Teacher Home, reused by every
list in the app.

**The live marker.** A pulsing accent dot on anything updating in real time: the joined
count, the monitor's status line, the open-quiz banner, the lobby's waiting state.

**Topics.** One per question, set in the builder. Every aggregate view — quiz results, class
analytics, findings, a student's page, my performance — groups by topic.

**Empty and first-run states.** Drawn rather than left blank: a teacher with no quizzes, a
builder with no questions, a review queue with nothing in it, a student with one attempt, a
class with too few quizzes for a trend, a student's first run, a lobby with nobody joined.
Each explains the condition instead of showing an empty container.

**Loading and error states.** Drawn for Splash, Login, Join, the Student Lobby, and every
submitting action. Not yet drawn for the data screens — see §10.

**Live-updating lists.** The Host Lobby's chips and the Live Monitor's rows both change
while the teacher watches; both are designed for items appearing, not for a static snapshot.

**Colour discipline.** One accent, switchable per board. Red is reserved for destructive
actions, user error, and time running out. Charts are single-series with no legend: length
carries the value, colour carries nothing, and text never wears the data colour.

---

## 9. What this design does not include

These are exclusions, and they are deliberate. Designing any of them would contradict a
decision already taken.

1. **No leaderboard, ranking, podium or peer comparison**, at any point, for either role.
2. **No per-question timer**, and nothing that implies one.
3. **No colour-coded or shape-coded answer options**, and no four-quadrant layout.
4. **No free-text answers.**
5. **No immediate right/wrong feedback during the quiz.**
6. **No nickname entry.**
7. **No teacher-driven question advancement.**
8. **No student-facing next step that the teacher has not accepted.**
9. **No language describing a student's ability, character or capacity** — only their work.
10. **No question type other than four-option MCQ**, no team mode, no streaks, no bonuses.
11. **No ranked list of students anywhere in the teacher's screens** — the roster carries
    attendance, not scores.
12. **No student names on a class-level gap.**

---

## 10. Open items

**Visual direction.** The palette, type and tone used across all 77 artboards are a
proposal, not an agreed brand. Everything else is downstream of this.

**Late entry.** Drawn as allowed, with only the remaining time. If it is not, screen 13's
already-started board becomes a dead end and the Host Lobby's Start helper line changes.

**Accepted findings have nowhere to land.** Next steps were removed from My Performance, so
nothing a teacher accepts in Review Findings now reaches a student anywhere, while Review
Findings still says "Nothing reaches students until you accept". Either that copy changes or
accepted steps need a destination.

**Blank answers in the score.** Undecided whether a blank counts as wrong or drops out of
the denominator. Screen 18's segment strip currently treats it as wrong.

**"My results" has no list screen.** The Student Home row points at a single result, while
the list of past results sits at the bottom of My Performance. One of the two must move.

**Loading and error states** are missing on screens 3, 8, 9, 11, 18 and 19, all of which
fetch data.

**Offline at the deadline.** The auto-submit overlay assumes the client can submit at 0:00.
Nothing covers a device that is offline when the window closes.

**Unattended session.** No defined behaviour for a quiz still running when the teacher's app
closes or their phone dies. Does the window survive on the deadline alone?

**Red carries three meanings** — destructive, user error, time running out. Accept the
overload or introduce a fourth hue for urgency.

**Topic percentage is a plain mean** of its questions, so one brutal question among easy ones
reads as average. And a single-topic quiz collapses the topic view into one row, which is
worse than a flat question list.

**Topic name collisions.** Topics match by name across quizzes, so "Hash table" and "Hash
tables" would split. The combobox must be the only way a topic is entered.

**The open-quiz banner** assumes the app knows a quiz is live before a PIN is typed. That
needs the backend to push it, or the banner goes.

**Two placeholder inconsistencies** remain in the artboards: screen 8's topic mean (~53%)
does not reconcile with its score distribution (~67%), and the result boards list six
questions for a fifteen-question quiz.
