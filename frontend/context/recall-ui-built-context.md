# Recall — built UI context

Companion to `frontend-ui-context.md`. That file said what to design; this one records what exists on the canvas, why it takes the shape it does, and where it departs from the brief. 19 screens, 77 artboards, all at 390 × 844 (taller where a screen scrolls).

---

## 1. What the product is

Recall is a Flutter classroom quiz app with two roles on one account system. A teacher writes four-option questions, hosts a live session, watches it run, and reads what the class got wrong. A student joins with a PIN, answers at their own pace against one deadline, and afterwards sees their own work — never anyone else's.

The design's centre of gravity is the gap between a quiz ending and a teacher knowing what to reteach. Most of the teacher's screens exist to close that gap; most of the student's exist to keep the experience calm and free of comparison.

---

## 2. Rules the whole interface obeys

Every question is exactly four options, labelled A to D, one correct. There is no other question type anywhere.

One deadline covers the whole attempt, set in minutes when the quiz is built and started by the teacher. Nothing in the interface implies a per-question timer, and two screens say so in words.

The student moves between questions, not the teacher. Answers stay editable until submit or auto-submit.

Results exist only after the window closes for everyone. Submitting produces a receipt, not a score.

A class-level gap is a candidate until the teacher accepts it. Acceptance is what would release anything to students.

Interface copy describes a student's work, never their ability, character or capacity. "Answered wrongly more often than not" is allowed; "weak at collisions" is not.

Excluded on purpose, and absent everywhere: leaderboards, ranking, podiums, peer comparison, percentile, per-question timers, colour- or shape-coded options, four-quadrant answer layouts, free-text answers, immediate right/wrong feedback during the quiz, nickname entry, teacher-driven question advancement, team mode, streaks and bonuses.

---

## 3. Visual system

Warm off-white ground `#F5F2EC`, ink `#16191A`, greys `#43403A` / `#5A574E` / `#6E6A61`, hairlines `#E2DCD0` and `#EFEAE0`, white cards. A neutral band `#EEE9DE` with border `#DBD2C0` carries conditions that are nobody's fault. An accent tint `#ECF1EF` with border `#C9DAD5` carries affirmative state. The accent is pine `#1F5F55`, switchable per board to navy, rust or ink.

Red `#8C2A20` is reserved and now carries three meanings: destructive actions, user error, and time running out. That third meaning was added at the Live Monitor and is flagged as a possible overload — the alternative is a fourth hue for urgency.

Fraunces sets headings and any number meant to be read as a result; IBM Plex Sans sets everything else, including the PIN and the countdown, because those are read aloud and typed rather than read as headings. Radius is fixed at 10px for controls and 14px for containers. Buttons and inputs are 52px; tap targets never fall below 44px.

Inner screens open with a 44px back chevron, a Fraunces title and one line of secondary text. Session flows — host lobby, join, lobby, the attempt — replace the chevron with a plain text action at top left (Cancel, Leave, Exit quiz, Back to questions), which is how the design signals there is no dashboard behind this screen.

Charts are single-series only: no legend, one hue, length carries the value. Bars cap at 24px with a 4px rounded data end and a zero baseline. Text never wears the data colour. Where a chart would be empty or meaningless, the screen explains the condition instead of drawing an empty frame.

---

## 4. Shared components

The countdown is one component in three places — Live Monitor, Question View, Review & Submit. It shows time for the whole quiz in tabular numerals, labelled "Time left", and turns red-tinted in the final minutes with a line saying attempts submit themselves at 0:00.

The option card is one component used on every question: a 28px letter badge and full option text in a bounded container, minimum 60px tall. Unselected is white with a hairline; selected is a 2px accent border, accent tint, filled badge and heavier text. On results screens it gains correct and incorrect variants — accent check and grey cross, never red.

The navigation list — a white card with hairline border, rows of icon, title, one line of live secondary text, and a chevron — is set on Teacher Home and reused by every list in the app.

A pulsing accent dot marks anything live: the joined-students count, the monitor's status line, the open-quiz banner, the lobby's waiting state.

Topics are the connective tissue. One topic per question, chosen in the builder from a combobox that filters existing topics as you type. Topics are what make "Collisions" nameable on the results, analytics, findings and performance screens; before they existed, nothing in the brief said where a concept came from.

A quiz is named by the teacher and shown by that name alone — "Hash tables", "Graphs", "Recursion". Where a week matters it sits in the meta line beside the date: "Week 8 · 9 September".

---

## 5. Teacher workflow

**Write → host → watch → read → act.**

From Teacher Home the teacher opens My quizzes and either edits an existing quiz or builds a new one: title, time limit for the whole quiz, then questions, each with its topic and four options with the correct one marked by a radio on the option row. Validation is per field and Add question greys out until the question, its options and its correct answer are all resolved.

Hosting opens the Host Lobby, a full-screen takeover showing a six-digit PIN at 52px with a live roster of joined students as initial chips. Start is disabled until someone joins, and the helper line under it changes with state rather than the button changing label.

Starting hands the teacher the Live Monitor: countdown as the hero figure, three stat tiles (Joined, Answering, Submitted), and per-student rows that state progress in words — "Answered 12 of 15", "Submitted at 10:51", "All 15 answered, not submitted". Exit quiz at top left opens the end-quiz confirmation, auto-submits every open attempt and closes the window; there is deliberately no way to leave the monitor with the quiz still running. When everyone has submitted, the end-early button is replaced by "Close the quiz now" plus a quieter "Let it run to 0:00".

Closing releases results. Quiz Results opens with participation and median as tiles, a score distribution column chart, then topics worst-first. A topic opens its own page listing that topic's questions worst-first; a question opens a sheet showing the split across all four options, with the correct one accent-filled and the three wrong ones neutral, so the distractor that beat the answer is visible without being flattered.

Across quizzes, Class Analytics shows the class average per quiz, topics aggregated worst-first, and an A-to-Z roster that shows attendance and never a score. Each topic row opens a class-level topic page with its percentage and its gaps — "19 of 42 students chose an answer that assumes no two keys share a slot", with the quizzes and questions it showed up in. No student names appear on any gap.

Those gaps queue into Review Findings, one at a time: the statement, where it showed up, what is uncertain, and the next step students would see. Accept is filled, Reject is outlined and neutral because dismissal is not destructive, and Skip for now sits below. Rejecting opens a sheet with an optional reason. The line "Nothing reaches students until you accept" stays on screen because it is the rule behind the screen.

Individual Student Analytics is reached from the roster: the student's own score per quiz, a correct-out-of-total table by topic split into two time columns, and a list of attempts, each opening to every question with what was chosen and what was correct. No class average line, so no comparison.

---

## 6. Student workflow

**Join → wait → answer → submit → receipt → result → performance.**

Student Home mirrors Teacher Home so the two read as one app: greeting, sign-out, a filled accent card for Join a quiz, a bounded list for My results and My performance, and a Latest result card. When a quiz is open, a pulsing banner appears above the Join card.

Join is one large PIN field, 40px digits on a numeric keyboard, with the Join button directly beneath it so the keyboard never covers it. Join stays disabled until six digits are entered. A PIN that matches nothing is the only red state on the screen; a closed quiz and an already-submitted quiz use the neutral band, because neither is a mistake. A quiz that has already started shows the remaining time and a line saying the deadline is the same for everyone, then goes straight to the questions — late entry drawn as allowed, which is still an assumption rather than a decision.

The Student Lobby names the quiz, gives the question count and duration, and carries one status block that is the only thing that changes between its three states: waiting with the pulsing dot and a count of others present, starting with a spinner, connection lost in the neutral band with a retry. A "How it works" checklist sits at the bottom as reference — answer in any order, change any answer until you submit, no timer on individual questions.

The attempt is Question View: one header holding the countdown and the position, the question in the serif, four option cards, then Previous and Next as equal-width buttons with a quieter "Review & submit" link beneath. Previous greys out on question 1 and Next becomes "Review & submit" on question 15. In the final minute the header turns red. At 0:00 an overlay states the time is up and names how many answers are being submitted.

Review & Submit is a five-by-three grid of question numbers — accent tint for answered, dashed outline for not — with a legend, a line stating the count in words, and a submit button that is never disabled. Submitting with blanks opens a sheet naming them ("Questions 3, 9 and 14") and warning the attempt cannot be reopened; "Submit anyway" is the filled action.

Submitted Confirmation is a receipt with no score anywhere: what was answered, when it was submitted, when the quiz closes, and the statement that the result appears once the quiz closes for everyone. The auto-submitted variant says "Time ran out", shows what was left blank, and confirms everything answered was saved.

Quiz Result opens after the window closes: the score as "11 of 15" over a fifteen-segment strip, a correct-out-of-total breakdown by topic, then every question with what was chosen and, only when wrong, what was correct. While the quiz is still open the same screen shows a neutral band explaining when the result will appear.

My Performance is the longitudinal view: the student's own percentage per quiz with a dash for one not taken, topics split into "Steady" and "To work on" with correct-out-of-total across quizzes, and the list of past results. Nothing on this screen compares them to anyone.

---

## 7. Screen inventory

| # | Screen | Artboards |
|---|---|---|
| 01 | Splash | loading; can't connect |
| 02 | Login / Sign up | idle; submitting; invalid credentials; network failure; sign up |
| 03 | Teacher Home | default; nothing to review; first run |
| 04 | My Quizzes | populated; confirm delete; empty |
| 05 | Quiz Builder | no questions yet; composing; validation errors; saving; unsaved changes |
| 06 | Host Lobby | nobody joined yet; students joining; starting |
| 07 | Live Monitor | running; deadline near; everyone submitted; confirm ending early; closed |
| 08 | Quiz Results | full participation; partial participation; topic opened; one question opened |
| 09 | Class Analytics | populated; filter open; too few quizzes for a trend; no quizzes closed; five topic pages |
| 10 | Review Findings | class gap waiting; reject; saving decision; next gap after accepting; nothing to review |
| 11 | Individual Student Analytics | populated; one attempt only; one past attempt |
| 12 | Student Home | default; quiz open; first run |
| 13 | Join | idle; PIN typed; checking; PIN not found; quiz closed; already submitted; quiz already started |
| 14 | Student Lobby | waiting; starting; connection lost |
| 15 | Question View | unanswered; answered; first question; last question; deadline near; auto-submitting |
| 16 | Review & Submit | all answered; three unanswered; confirm; submitting |
| 17 | Submitted Confirmation | by you; at the deadline |
| 18 | Quiz Result | available; auto-submitted; not yet available |
| 19 | My Performance | populated; one quiz only |

---

## 8. Where this departs from the brief

Findings are class-level only. The brief put flagged patterns on the individual student page with candidate, confirmed and rejected status, and a findings indicator in the roster. All of that is gone: a student's own patterns are the backend's business, and only class-wide topic gaps are reviewed by the teacher. This overrides §7.9, §7.10 and §7.11.

Screen order is reversed for 10 and 11 — Review Findings is 10, Individual Student Analytics is 11 — so the flow runs Class Analytics → Review Findings → Student Analytics.

The Live Monitor has no way to leave without ending the quiz, which contradicts §7.7's "leave the monitor without ending the quiz".

Topics did not exist in the brief. They were added to the builder because screens 09, 10 and 19 all depend on naming a concept and nothing said where one came from.

Quiz Results is organised by topic, not by loose questions. Ordering questions says which question went badly; ordering topics says what to reteach.

Next steps were removed from My Performance at review, which also removed the only place an accepted finding would reach a student.

---

## 9. Open decisions

The visual direction is a candidate, not an agreed one. Every board inherits it.

Late entry is drawn as allowed, with only the remaining time. If it is not allowed, screen 13's started board becomes a dead end and the Host Lobby's Start helper line changes with it.

With next steps gone from My Performance, nothing a teacher accepts in Review Findings reaches a student anywhere — while Review Findings still says "Nothing reaches students until you accept". Either the copy changes or accepted steps need a destination.

Nobody has decided whether a blank answer counts as wrong in the score or drops out of the denominator. The score strip on screen 18 currently treats it as wrong.

"My results" on Student Home points at a single result; the actual list of past results sits at the bottom of My Performance. One of the two needs to move.

Loading and recoverable error states are drawn only for the lobby and Join. Screens 03, 08, 09, 11, 18 and 19 all fetch data without them, which the brief requires.

The auto-submit overlay assumes the client can submit at 0:00. Nothing covers a device that is offline at the deadline.

There is no defined behaviour for a quiz that is running when the teacher's app closes or their phone dies.

Red now means destructive, user error and time running out. Accept the overload or add a fourth hue.

A topic's percentage is a plain mean of its questions, so one brutal question among easy ones reads as average. And a single-topic quiz collapses the topic view into one row, which is worse than a flat question list.

Topics match by name across quizzes, so "Hash table" and "Hash tables" would split. The combobox needs to be the only way a topic is entered.

The open-quiz banner on Student Home assumes the app knows a quiz is live before a PIN is typed. That needs the backend to push it, or the banner goes.

Two data inconsistencies remain in the placeholder content: screen 08's topic mean (~53%) does not reconcile with its score distribution (~67%), and the result boards list six questions for a fifteen-question quiz.
