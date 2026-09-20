# Recall — REST API specification

**For:** whoever builds the JSON backend behind `frontend_flutter/`.
**Companion:** [BACKEND_CONTEXT.md](BACKEND_CONTEXT.md) — why the API is shaped this way,
what infrastructure is missing, and the build order.

Every endpoint here was derived from a method on one of the five repository
interfaces in `frontend_flutter/lib/data/repositories.dart`, or from a place a
screen reaches past them into `Fixtures`. The mapping table in §10 lists each one,
so a real `Http*Repository` can be written against this document without touching
a screen.

---

## 0. Conventions

| | |
|---|---|
| Base path | `/api/v1` |
| Format | JSON in and out, UTF-8. Field names are **camelCase**, matching the Dart models |
| Auth | `Authorization: Bearer <token>` on everything except `/health`, `/auth/signup`, `/auth/login` |
| Ids | opaque strings with a prefix: `usr_`, `quiz_`, `qn_`, `ses_`, `att_`, `fnd_` |
| Time | ISO 8601 UTC (`2026-09-19T10:51:00Z`). Every response that carries a deadline also carries `serverNow`, so clients compute time left from the server clock, not their own |
| Enums | Dart enum names as strings: `teacher`, `awaitingReview`, `allAnswered`, … |
| Option index | `0`–`3`, meaning A–D. `null` means blank |

### Errors

Non-2xx responses always have this body:

```json
{ "error": { "code": "invalid_credentials", "message": "Those details did not match an account." } }
```

`message` is written to be shown to the user as-is; `code` is for the client to branch on.

| status | when |
|---|---|
| 400 `validation_failed` | body fails validation; adds `"fields": {"title": "Give the quiz a name."}` |
| 401 `unauthenticated` | missing, expired or unknown token |
| 403 `forbidden` | right token, wrong role, or someone else's resource |
| 404 `not_found` | |
| 409 `conflict` | the action is invalid in the current state (e.g. starting a session nobody joined) |
| 423 `results_not_released` | results asked for while the session is still open |
| 503 `agent_busy` | a model-backed step is rate limited; `Retry-After` header is set |

### Roles

`T` = teacher only, `S` = student only, `*` = any signed-in user.

---

## 1. Health

### `GET /health` — public

Used by Splash (screen 01) to tell "can't connect" apart from "not signed in".

```json
200 { "ok": true, "serverNow": "2026-09-19T10:00:00Z", "version": "1.0.0" }
```

---

## 2. Auth — `AuthRepository`

`identifier` is a student's **roll number** or a teacher's **email or staff id**. It is
unique across all users.

### `POST /auth/signup` — public

```json
{ "name": "Nithya P", "identifier": "21CS042", "password": "••••••", "role": "student" }
```

```json
201 {
  "token": "rk_7f3c…",
  "expiresAt": "2026-10-19T10:00:00Z",
  "user": { "id": "usr_a1b2", "name": "Nithya P", "role": "student", "rollNumber": "21CS042" }
}
```

- `400` — name empty, password shorter than 8, role not `teacher`/`student`.
- `409 identifier_taken` — "An account already uses that roll number."
- `rollNumber` is set only for students (it is the identifier); `null` for teachers.

### `POST /auth/login` — public

```json
{ "identifier": "21CS042", "password": "••••••" }
```

`200` — same body as signup. `401 invalid_credentials` with the message
*"Those details did not match an account."* — the same message whether the identifier
or the password was wrong.

### `GET /auth/me` — `*`

`restoreSession()`. `200 { "user": User }`, or `401` → the client treats it as "no session".

### `POST /auth/logout` — `*`

Revokes the token. `204`.

---

## 3. Quizzes — `QuizRepository` (teacher)

### Quiz object (teacher view)

```json
{
  "id": "quiz_hash",
  "title": "Hash tables",
  "timeLimitMinutes": 20,
  "week": "Week 8",
  "lastRun": "2026-09-09T10:30:00Z",
  "pin": null,
  "closedAt": "2026-09-09T10:50:00Z",
  "openSessionId": null,
  "questions": [
    {
      "id": "qn_01",
      "text": "Two distinct keys hash to the same slot. What has happened?",
      "topic": "Collisions",
      "options": ["A collision", "An overflow", "A rehash", "Nothing, keys are unique"],
      "correctIndex": 0,
      "misconceptions": [null, "confuses collision with capacity", "…", "assumes no two keys share a slot"]
    }
  ]
}
```

- `options` is **always exactly four** strings; `correctIndex` is always `0`–`3`.
- `pin` and `openSessionId` are set only while a session of this quiz is in `lobby`
  or `running`. `lastRun` / `closedAt` come from the **most recent closed session**.
- `misconceptions` is optional and **new** (the builder does not collect it yet): what
  choosing each wrong option would reveal, `null` on the correct one. The findings agent
  uses it when present and falls back to the option text when absent. See
  BACKEND_CONTEXT §6.

### `GET /quizzes` — T

The teacher's quizzes, newest `lastRun` first, never-run quizzes after. `200 Quiz[]`.

### `GET /quizzes/{quizId}` — T

`200 Quiz`, `404`, `403` if another teacher's.

### `PUT /quizzes/{quizId}` — T

**Upsert**, matching `saveQuiz(quiz)` — the builder generates its own id before saving.
Body is a Quiz without the server-owned fields (`lastRun`, `pin`, `closedAt`,
`openSessionId`). Question ids may be client-generated; the server keeps them.

Validation (`400`, with per-field messages the builder already uses):

| field | rule | message |
|---|---|---|
| `title` | non-blank | Give the quiz a name. |
| `timeLimitMinutes` | integer 1–180 | Set a whole number of minutes. |
| `questions` | at least 1 | Add at least one question. |
| `questions[i].text` | non-blank | Write the question. |
| `questions[i].topic` | non-blank, trimmed | Choose a topic. |
| `questions[i].options` | exactly 4, all non-blank | Fill this option in. |
| `questions[i].correctIndex` | 0–3 | Mark which option is correct. |

`200 Quiz` (updated) or `201 Quiz` (created). `409 session_open` if a session of this quiz
is in `lobby` or `running`. Editing a quiz that has already run is allowed: past sessions
keep the question snapshot they started with (BACKEND_CONTEXT §5.3).

### `DELETE /quizzes/{quizId}` — T

`204`. `409 session_open` while a session is live. Past results are **kept** (the quiz is
soft-deleted), because class analytics and student history still reference them.

### `GET /topics` — T

`knownTopics()`: every topic on the teacher's quizzes plus the seed list, de-duplicated
case-insensitively, sorted. `200 string[]`.

---

## 4. Live sessions — `SessionRepository` (teacher)

A session is one hosting of one quiz. Lifecycle: `lobby → running → closed`, or
`lobby → cancelled`. `deadlineNear` and `everyoneSubmitted` from `HostPhase` are derived by
the client from `endsAt` and the progress rows; the server does not store them.

### Session snapshot

```json
{
  "id": "ses_9k2",
  "quizId": "quiz_hash",
  "pin": "408217",
  "status": "running",
  "createdAt": "2026-09-19T10:28:00Z",
  "startedAt": "2026-09-19T10:30:00Z",
  "endsAt": "2026-09-19T10:50:00Z",
  "closedAt": null,
  "serverNow": "2026-09-19T10:41:12Z",
  "joined": [ { "id": "usr_a1b2", "name": "Nithya P", "role": "student", "rollNumber": "21CS042" } ],
  "progress": [
    {
      "student": { "id": "usr_a1b2", "name": "Nithya P", "role": "student", "rollNumber": "21CS042" },
      "stage": "answering",
      "answered": 12,
      "total": 15,
      "submittedAt": null,
      "autoSubmitted": false
    }
  ]
}
```

`stage` is `joined | answering | allAnswered | submitted`. `pin` is six digits with no
space; the client formats it as `408 217`.

### `POST /quizzes/{quizId}/sessions` — T

`host(quiz)`. Opens a lobby and allocates a PIN unique among live sessions.
`201 Session`. `409 session_open` if this quiz already has a live session — the body then
carries the existing session so the client can re-attach instead of failing.

### `GET /sessions/{sessionId}` — T

Current snapshot. Also the **polling fallback** for the event stream below.

### `GET /sessions/{sessionId}/events` — T — Server-Sent Events

Replaces `joinedStudents()` and `progress()` streams. `Content-Type: text/event-stream`.
The first event is always a full `snapshot`, so the monitor is never briefly empty.

```
event: snapshot
data: { …Session… }

event: joined
data: { "joined": [ …User[] … ] }

event: progress
data: { "progress": [ …StudentProgress[] … ], "serverNow": "…" }

event: status
data: { "status": "closed", "closedAt": "…" }
```

A `: keepalive` comment is sent every 15 s. On disconnect the client reconnects and
receives a fresh `snapshot`; no event replay is needed.

### `POST /sessions/{sessionId}/start` — T

`start()`. Sets `startedAt = now`, `endsAt = now + timeLimitMinutes`.
`200 Session`. `409 nobody_joined` — Start is disabled in the UI until someone joins, the
server enforces it too. `409` if not in `lobby`.

### `POST /sessions/{sessionId}/end` — T

`endQuiz()`. Auto-submits every open attempt with whatever is saved, sets `closedAt`,
releases results, and queues findings generation (§7). Idempotent: ending a closed
session returns `200` with the closed snapshot.

```json
200 { "session": { …Session, "status": "closed"… }, "autoSubmitted": 3, "findingsJob": "queued" }
```

The server also does this on its own at `endsAt` (BACKEND_CONTEXT §5.4), so a teacher's
phone dying mid-quiz does not strand a session.

### `POST /sessions/{sessionId}/cancel` — T

The Host Lobby's Cancel, before Start. `204`. `409` once running (use `/end`).

---

## 5. Joining and attempts — `AttemptRepository` (student)

### Student quiz view

What a student receives. **No `correctIndex`, no `misconceptions`.** The answer key never
leaves the server before results are released.

```json
{
  "id": "quiz_hash",
  "title": "Hash tables",
  "timeLimitMinutes": 20,
  "week": "Week 8",
  "questions": [
    { "id": "qn_01", "text": "…", "topic": "Collisions", "options": ["…", "…", "…", "…"] }
  ]
}
```

### `POST /join` — S

```json
{ "pin": "408 217" }
```

Spaces are stripped server-side. Every outcome the Join screen draws is a `200`, because
none of them is a transport error — the UI treats them as states:

```json
200 {
  "outcome": "ok",
  "sessionId": "ses_9k2",
  "attemptId": "att_77x",
  "quiz": { …StudentQuiz… },
  "remainingSeconds": null,
  "serverNow": "…"
}
```

| `outcome` | when | extra fields |
|---|---|---|
| `ok` | session in `lobby` | `sessionId`, `attemptId`, `quiz` |
| `alreadyStarted` | session `running` (late entry allowed) | + `remainingSeconds`, `endsAt` |
| `closed` | session `closed` / `cancelled` | `quiz` title only |
| `alreadySubmitted` | this student already submitted in this session | `quiz` title only |
| `notFound` | no live session has this PIN | — |

Joining is idempotent: joining the same session twice returns the same `attemptId`.

### `GET /sessions/{sessionId}/lobby` — S — Server-Sent Events

Replaces `othersWaiting()` **and the 8-second timer** that currently stands in for the
teacher pressing Start.

```
event: waiting
data: { "othersWaiting": 7 }

event: started
data: { "startedAt": "…", "endsAt": "…", "serverNow": "…" }

event: closed
data: { "closedAt": "…" }
```

Polling fallback: `GET /sessions/{sessionId}/lobby?poll=1` returns
`{ "status": "lobby", "othersWaiting": 7, "startedAt": null, "endsAt": null, "serverNow": "…" }`.
The lobby's "connection lost" state is the client failing to reach either.

### `GET /attempts/{attemptId}` — S (own only)

Resume after the app is killed mid-quiz.

```json
200 {
  "id": "att_77x", "sessionId": "ses_9k2", "quiz": { …StudentQuiz… },
  "answers": { "qn_01": 2, "qn_02": 0 },
  "submittedAt": null, "autoSubmitted": false,
  "endsAt": "…", "serverNow": "…"
}
```

### `PUT /attempts/{attemptId}/answers/{questionId}` — S

Autosave one answer as it is chosen. Body `{ "chosenIndex": 2 }`, or `{ "chosenIndex": null }`
to clear. `204`. `409 attempt_closed` once submitted or past `endsAt`.

This is **new** — the client currently holds answers in memory and sends them only at
submit. Autosave is what lets the server auto-submit a device that is offline at 0:00
(BACKEND_CONTEXT §5.4). Until the client adopts it, `/submit` with the full map still works.

### `POST /attempts/{attemptId}/submit` — S

`submit(attempt, auto:)`.

```json
{ "answers": { "qn_01": 2, "qn_02": 0 }, "auto": false }
```

`answers` is merged over anything autosaved (the client's copy wins). A missing key is a
blank. Returns the receipt the Submitted screen draws — **no score**:

```json
200 {
  "submittedAt": "2026-09-19T10:47:03Z",
  "autoSubmitted": false,
  "answered": 13,
  "total": 15,
  "blankPositions": [3, 9],
  "closesAt": "2026-09-19T10:50:00Z"
}
```

Idempotent: a second submit returns the first receipt unchanged (attempts cannot be
reopened). Submitting after `endsAt` within a 10-second grace window is accepted and
marked `autoSubmitted: true`; after that, `409 attempt_closed` with the receipt of the
server-side auto-submission.

---

## 6. Results — `ResultsRepository`

Results for a session exist only once it is `closed`. Before that every result endpoint
returns `423 results_not_released` with `{ "closesAt": "…" }`, which Quiz Result (screen
18) draws as its "not yet available" band.

### 6.1 Teacher: one quiz

#### `GET /results/quizzes/{quizId}` — T

`classResult(quizId)`, from the quiz's most recent closed session (`?sessionId=` to pick
another).

```json
200 {
  "quiz": { …Quiz… },
  "sessionId": "ses_9k2",
  "tookIt": 38,
  "classSize": 42,
  "medianScore": 11,
  "distribution": [1, 4, 11, 17, 9],
  "topicScores": [ { "topic": "Collisions", "correct": 71, "total": 152 } ],
  "breakdowns": [
    {
      "question": { …Question with correctIndex… },
      "shares": [19, 14, 3, 2],
      "respondents": 38
    }
  ]
}
```

- `distribution` — students per score band, lowest first: `[0–20%), [20–40%), [40–60%),
  [60–80%), [80–100%]`. Computed from the same attempt scores as `medianScore`, so the
  two tiles cannot disagree.
- `medianScore` — median **number correct**, blanks counted as wrong.
- `topicScores` — pooled: `correct` / `total` over every answer to every question in the
  topic, worst first.
- `breakdowns` — one per question, worst `correctShare` first. `shares[i]` counts
  students who chose option `i`; blanks are in `respondents` but no share.
- `tookIt` — attempts with at least one answer. `classSize` — see BACKEND_CONTEXT §5.5.

### 6.2 Teacher: across quizzes (Class Analytics, screen 09)

#### `GET /analytics/class/averages?limit=6` — T

`classAverages()`. One point per closed quiz, oldest first.

```json
200 [ { "quizId": "quiz_arr", "quizTitle": "Arrays", "shortLabel": "W4", "percent": 71 } ]
```

`shortLabel` is `week` with `Week ` → `W`, or the title when there is no week.

#### `GET /analytics/class/topics` — T

`topicAggregates()`. Every topic across closed sessions, worst first, with its findings.

```json
200 [
  {
    "topic": "Collisions",
    "percent": 44,
    "questionCount": 7,
    "gapsAwaitingReview": 1,
    "gaps": [ { …Finding… } ]
  }
]
```

#### `GET /analytics/class/roster` — T

`roster()`. A–Z, attendance only — **never a score**.

```json
200 [ { "student": { …User… }, "attended": 5, "totalQuizzes": 6 } ]
```

### 6.3 Teacher: one student (screen 11)

All `403` unless the student has attended at least one of this teacher's sessions.

| endpoint | repository method | body |
|---|---|---|
| `GET /analytics/students/{studentId}` | *(new — replaces the `roster().firstWhere` lookup)* | `RosterEntry` |
| `GET /analytics/students/{studentId}/averages` | `studentAverages` | `QuizAverage[]`, with `"absent": true, "percent": 0` for quizzes not taken |
| `GET /analytics/students/{studentId}/topics?window=recent` | `studentTopicScores(recent:)` | `TopicScore[]` |
| `GET /analytics/students/{studentId}/attempts` | `studentAttempts` | `AttemptSummary[]`, newest first |
| `GET /analytics/students/{studentId}/attempts/{quizId}` | `studentAttemptDetail` | `QuizResultData` |

`window` is `recent` (the student's last 3 closed attempts), `earlier` (everything before
those), or `all`. The screen's two columns are `recent` and `earlier`; they always sum to
`all`.

### 6.4 Student: own results (screens 12, 18, 19)

| endpoint | repository method | body |
|---|---|---|
| `GET /me/results/{quizId}` | `myResult` | `QuizResultData`, or `423` while open |
| `GET /me/attempts` | `myAttempts` | `AttemptSummary[]`, newest first |
| `GET /me/averages` | `myAverages` | `QuizAverage[]` |
| `GET /me/topics?window=all` | `myTopicScores` | `TopicScore[]` |
| `GET /me/open-quiz` | *(new — replaces `Fixtures.graphs` on Student Home)* | `{ "quiz": StudentQuiz, "sessionId": "…", "pin": null }` or `204` |

No `/me/*` endpoint ever returns another student's data or a class figure. There is no
class average anywhere on the student side.

#### Shapes

```json
QuizResultData {
  "quiz": { …Quiz with correctIndex — results are released… },
  "questionResults": [ { "question": { … }, "chosenIndex": 2, "position": 1 } ],
  "topicScores": [ { "topic": "Collisions", "correct": 2, "total": 4 } ],
  "autoSubmitted": false,
  "submittedAt": "…"
}

AttemptSummary { "quiz": { …Quiz… }, "correct": 11, "total": 15, "takenOn": "…" }
TopicScore     { "topic": "Collisions", "correct": 2, "total": 4 }
```

`GET /me/open-quiz` returns a live session of any teacher whose sessions this student has
joined before; it never reveals the PIN (`pin: null`) — the student still types it.

---

## 7. Findings — review queue (screen 10)

A finding is a **class-level** gap: what a share of the class chose, never what one student
is like, never a student's name. It is written by the findings agent after a session
closes (BACKEND_CONTEXT §6) and is a candidate until the teacher decides.

### Finding object

```json
{
  "id": "fnd_c01",
  "topic": "Collisions",
  "statement": "19 of 42 students chose an answer that assumes no two keys share a slot",
  "quizId": "quiz_hash",
  "quizTitle": "Hash tables",
  "questionId": "qn_01",
  "questionStem": "Two distinct keys hash to the same slot. What has happened?",
  "chosenIndex": 3,
  "chosenCount": 19,
  "classSize": 42,
  "uncertainty": "The same distractor also reads as correct if …",
  "nextStep": "Work through a table where two keys collide, and show …",
  "status": "awaitingReview",
  "rejectionReason": null,
  "decidedAt": null,
  "unverified": null
}
```

`status` is `awaitingReview | accepted | rejected`. `unverified` is non-null when the agent
ran out of drafts without the checker passing one; the UI should show it, never hide it.

### `GET /findings?status=awaitingReview` — T

`findings()`. Omit `status` for all. Oldest awaiting first.

### `POST /findings/{findingId}/decision` — T

`decideFinding(id, status, reason:)`.

```json
{ "status": "rejected", "reason": "The stem really does allow a perfect hash." }
```

`200 Finding`. `status` must be `accepted` or `rejected`; `reason` is optional and only
kept on rejection. `409 already_decided` if it is not `awaitingReview`. "Skip for now"
is client-side only and makes no request.

### `GET /findings/jobs?sessionId=` — T

Whether generation for a closed session is `queued | running | done | failed`, so Teacher
Home can say "Findings are being written" instead of "Nothing to review".

### `GET /findings/{findingId}/trail` — T — demo and audit

Every draft and every check the agent produced for this finding, in order — the same
`_trail` `app/report.py` already keeps. This is what shows the back-edge on screen.

```json
200 [
  { "step": "draft", "revision": 1, "body": { "statement": "Most of the class does not understand hashing", … } },
  { "step": "check", "revision": 1, "body": { "verdict": "rejected", "failedCheck": "claimStrength", "detail": "…" } },
  { "step": "draft", "revision": 2, "body": { … } },
  { "step": "check", "revision": 2, "body": { "verdict": "accepted" } }
]
```

### `POST /sessions/{sessionId}/findings/regenerate` — T — demo

Re-runs the findings agent live for a closed session (the `?force=1` button of the old web
app). Existing **decided** findings are kept; undecided ones are replaced.
`202 { "job": "queued" }`.

---

## 8. Teacher Home composite (optional)

Teacher Home currently makes four calls (`myQuizzes`, `findings`, `classAverages`, then
`classResult` of the latest run). The individual endpoints are enough. If the round
trips hurt on a slow network, add:

### `GET /teacher/home` — T

```json
200 { "quizCount": 6, "pendingFindings": 3, "quizzesClosed": 6, "recent": { …ClassQuizResult… } }
```

---

## 9. Legacy routes

`webapp.py`'s HTML routes (`/`, `/quiz/{sid}`, `/answer`, `/report/{sid}`, `/teacher`,
`/teacher/{dept}`) stay as they are, in the same process, so the tested department
diagnostic and its agent reports keep working for walkthroughs and the demo. The new API
lives under `/api/v1` and does not share their tables (BACKEND_CONTEXT §4).

---

## 10. Repository → endpoint map

| Dart method | endpoint |
|---|---|
| `AuthRepository.signIn` | `POST /auth/login` |
| `AuthRepository.signUp` | `POST /auth/signup` |
| `AuthRepository.restoreSession` | `GET /auth/me` |
| `AuthRepository.signOut` | `POST /auth/logout` |
| `QuizRepository.myQuizzes` | `GET /quizzes` |
| `QuizRepository.quizById` | `GET /quizzes/{id}` |
| `QuizRepository.saveQuiz` | `PUT /quizzes/{id}` |
| `QuizRepository.deleteQuiz` | `DELETE /quizzes/{id}` |
| `QuizRepository.knownTopics` | `GET /topics` |
| `SessionRepository.host` | `POST /quizzes/{id}/sessions` |
| `SessionRepository.joinedStudents` | `GET /sessions/{id}/events` (`snapshot`, `joined`) |
| `SessionRepository.start` | `POST /sessions/{id}/start` |
| `SessionRepository.progress` | `GET /sessions/{id}/events` (`snapshot`, `progress`) |
| `SessionRepository.endQuiz` | `POST /sessions/{id}/end` |
| *(Host Lobby Cancel — no method yet)* | `POST /sessions/{id}/cancel` |
| `AttemptRepository.join` | `POST /join` |
| `AttemptRepository.othersWaiting` | `GET /sessions/{id}/lobby` (`waiting`) |
| *(lobby's 8 s start timer)* | `GET /sessions/{id}/lobby` (`started`) |
| *(no method yet — autosave)* | `PUT /attempts/{id}/answers/{questionId}` |
| `AttemptRepository.submit` | `POST /attempts/{id}/submit` |
| `ResultsRepository.classResult` | `GET /results/quizzes/{quizId}` |
| `ResultsRepository.classAverages` | `GET /analytics/class/averages` |
| `ResultsRepository.topicAggregates` | `GET /analytics/class/topics` |
| `ResultsRepository.roster` | `GET /analytics/class/roster` |
| `ResultsRepository.findings` | `GET /findings` |
| `ResultsRepository.decideFinding` | `POST /findings/{id}/decision` |
| `ResultsRepository.myResult` | `GET /me/results/{quizId}` |
| `ResultsRepository.myAttempts` | `GET /me/attempts` |
| `ResultsRepository.myAverages` | `GET /me/averages` |
| `ResultsRepository.myTopicScores` | `GET /me/topics` |
| `ResultsRepository.studentAverages` | `GET /analytics/students/{id}/averages` |
| `ResultsRepository.studentTopicScores` | `GET /analytics/students/{id}/topics?window=` |
| `ResultsRepository.studentAttempts` | `GET /analytics/students/{id}/attempts` |
| `ResultsRepository.studentAttemptDetail` | `GET /analytics/students/{id}/attempts/{quizId}` |
| *(`Fixtures.graphs` on Student Home)* | `GET /me/open-quiz` |
| *(`Fixtures.classSize` on Class Analytics)* | `classSize` field on `/results/…` and `/analytics/class/roster` length |
| *(`Fixtures.roster.first` fallback, screen 11)* | `GET /analytics/students/{id}` |
