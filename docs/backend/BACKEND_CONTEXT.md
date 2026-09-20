# Recall — Backend build context

**Read this before writing backend code.** It says what exists, what the Flutter app needs
that does not exist, how to build it on the spine already here, and in what order.
The endpoint contract is in [REST_API.md](REST_API.md). Project history and the agent
design are in [MAIN_CONTEXT.md](../MAIN_CONTEXT.md).

---

## 0. The situation in one paragraph

The Flutter app in `frontend_flutter/` has all 19 screens built and runs entirely on
**in-memory mock repositories** (`lib/data/repositories.dart`, `lib/data/fixtures.dart`).
The Python side has a working, tested agent pipeline (`app/flow.py`, `app/report.py`) and
an HTML-only web app (`webapp.py`) built for a different product shape: one tester at a
time, a fixed 20-question bank per department, no accounts, no teachers' own quizzes, no
live sessions. **There is no JSON API, and none of the data model the Flutter app assumes
exists on the server.** The job is to build that data model and API on top of the existing
spine, keep the agent at the centre, and swap the mocks for HTTP implementations.

---

## 1. Scope warning — decide this first

MAIN_CONTEXT §1 lists the judges' exclusions: *"No mobile app. No live in-class quiz
hosting. … No student-facing interface."* The Flutter app is a mobile app with live PIN
hosting and a student interface. The earlier web app was deliberately shaped to avoid those
("single-tester diagnostic … not a live in-class quiz").

Building this backend puts the team inside the exclusions. That is a team decision, not a
build decision. Options:

1. Build it anyway and be ready to defend it in the demo.
2. Build the teacher side + findings agent fully, and treat hosting/joining as the
   *collection mechanism* for evidence (same argument as the old web app used).
3. Keep the web app as the judged artefact and treat the Flutter app as post-event work.

Everything below assumes 1 or 2. The agentic part (§6) is what is scored either way.

---

## 2. What exists and is reusable

| piece | where | reuse |
|---|---|---|
| Append-only run store, SQLite, immutability triggers | `slice/store.py` | **Yes, unchanged.** Findings runs are written here |
| Token budget + per-step attempt counter that survive restarts | `slice/budget.py` | Yes |
| Human-in-the-loop as a state: `ask` / `answer` / `sweep` with timeout | `slice/callback.py` | Yes — a finding awaiting teacher review *is* an open question |
| LLM client: Groq primary, OpenRouter fallback, rate-limit wait, typed schema parsing | `slice/llm.py` | Yes, via `complete(...)` |
| Draft → check → route back with reason, 3 drafts, 90 s wall clock, trail kept | `app/report.py::_generate` | **Pattern to copy** for the findings agent |
| Citation check in code, not by model | `app/report.py::check_citations`, `app/provenance.py` | Pattern to copy |
| "Counts come from SQL, the model only interprets" | `app/roster.py` aggregate functions | Pattern + some SQL to adapt |
| Question bank with misconception per wrong option | `app/bank.py` | Seed data (§8) |
| FastAPI + uvicorn already a dependency | `requirements.txt` | Yes |

**Rule from MAIN_CONTEXT §2a that still holds: do not edit `slice/`.**

---

## 3. What is missing — the full list

Ordered roughly by how much else depends on it.

| # | missing | why the app needs it | where it goes |
|---|---|---|---|
| 1 | **JSON API layer** | Every screen. `webapp.py` returns HTML only | `api/` package, mounted at `/api/v1` |
| 2 | **Users, passwords, tokens, roles** | Login/Sign up (02), every role-gated screen. Currently `students` has name/phone/register no., no password, no teachers at all | `users`, `auth_tokens` tables |
| 3 | **Teacher-authored quizzes and questions** | My Quizzes (04), Builder (05). The bank is hard-coded Python, keyed by department | `quizzes`, `questions` tables |
| 4 | **Topics** | Builder combobox, every aggregate view | column on `questions`; `GET /topics` is a `SELECT DISTINCT` |
| 5 | **Sessions with PINs and a lifecycle** | Host Lobby (06), Live Monitor (07), Join (13), Lobby (14) | `sessions` table + `session_questions` snapshot |
| 6 | **Attempts scoped to a session** | Existing `responses` PK is `(student_id, question_id)` — a student can never answer a question twice, so a quiz can never be re-run | `attempts`, `answers` tables |
| 7 | **Server-side clock and deadline enforcement** | Countdown on 07/15/16, auto-submit at 0:00, "teacher's phone dies" and "device offline at deadline" open decisions | `endsAt` on session + a sweeper (§5.4) |
| 8 | **Real-time channel** | Lobby roster, monitor progress, student lobby "started" push (currently an 8-second fake timer), open-quiz banner | SSE endpoints (§5.2) |
| 9 | **Answer-key protection** | Flutter's `Question` carries `correctIndex`; sending it to students leaks the key | Separate student projection (REST_API §5) |
| 10 | **Result release gating** | "Results exist only after the window closes for everyone" | `423` until session `closed` |
| 11 | **Aggregations** | median, 5-band distribution, per-option shares, pooled topic scores, class average per quiz, attendance, recent/earlier split | `api/analytics.py`, SQL only |
| 12 | **Class-level findings agent + review queue** | Review Findings (10), topic gaps (09), Teacher Home badge. The existing report agent writes free-text reports, not reviewable findings | `app/findings.py` + `findings` table (§6) |
| 13 | **Background job runner** | Findings are model work (seconds to a minute) triggered by closing a session; must not block `/end` and must resume after a restart | `jobs` table + worker (§5.6) |
| 14 | **Class / roster definition** | `classSize = 42` is a fixture constant; nothing on the server says who is "in the class" | §5.5 decision |
| 15 | **CORS** | Flutter web (`chrome` launch config) calls from another origin | `CORSMiddleware` |
| 16 | **Flutter HTTP client + `Http*Repository` implementations + JSON (de)serialisation** | The swap itself. `pubspec.yaml` has no `http` package and models have no `fromJson` | `frontend_flutter/lib/data/api/` |
| 17 | **Seed + simulation** | Screens are meaningless on an empty DB; demo needs 40 students' history | `scripts/seed_api.py` (§8) |
| 18 | **Tests** | 44 existing tests cover the agent; nothing covers auth, sessions, gating | `tests/test_api_*.py` |

---

## 4. Layout

```
api/
  __init__.py
  main.py          # FastAPI app: mounts routers at /api/v1, CORS, error handler, startup (schema + sweeper + worker)
  db.py            # schema DDL, connection, get_store()
  auth.py          # hashing, tokens, current_user / require_teacher / require_student dependencies
  dto.py           # pydantic request/response models, camelCase aliases
  quizzes.py       # router: /quizzes, /topics
  sessions.py      # router: /quizzes/{id}/sessions, /sessions/*, SSE
  attempts.py      # router: /join, /attempts/*
  results.py       # router: /results, /analytics, /me
  findings.py      # router: /findings
  analytics.py     # pure SQL aggregation functions (no FastAPI imports - testable alone)
  jobs.py          # job table + worker loop + deadline sweeper
app/
  findings.py      # the findings AGENT (draft/check loop) - sits beside report.py
  prompts/finding_class.md, prompts/finding_class_check.md
scripts/seed_api.py
tests/test_api_auth.py, test_api_sessions.py, test_api_results.py, test_findings_agent.py
```

`webapp.py` stays as it is. Easiest wiring: in `webapp.py` add
`from api.main import api; app.mount("/api/v1", api)` so one `python webapp.py` serves
both, on port 8000.

**Same SQLite file or a new one?** Use a new file, `recall.db`, opened with the kit's
`Store` (so `versions`, `runs`, `questions`, `counters` tables come for free) and the new
tables created alongside. The old `webapp.db` tables (`students`, `responses`, `reports`)
have conflicting semantics (`students` ≠ `users`, one-attempt-ever `responses`); keeping
them apart avoids a migration during the event.

SQLite settings: `PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON; busy_timeout=5000`.
One connection per request (or a lock around the shared one) — `sqlite3` connections are
not safe to share across the threads FastAPI runs sync endpoints on. Check how
`slice/store.py` opens its connection (`check_same_thread`) before sharing it.

---

## 5. Data model and the decisions behind it

### 5.1 Schema

```sql
CREATE TABLE users (
  id            TEXT PRIMARY KEY,            -- usr_…
  name          TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('teacher','student')),
  identifier    TEXT NOT NULL,               -- roll number for students, email/staff id for teachers
  identifier_ci TEXT NOT NULL UNIQUE,        -- lower(trim(identifier))
  password_hash TEXT NOT NULL,               -- scrypt$N$r$p$salt$hash
  created_at    REAL NOT NULL
);

CREATE TABLE auth_tokens (
  token_hash TEXT PRIMARY KEY,               -- sha256 of the bearer token; the token itself is never stored
  user_id    TEXT NOT NULL REFERENCES users(id),
  created_at REAL NOT NULL,
  expires_at REAL NOT NULL,
  revoked    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE quizzes (
  id                 TEXT PRIMARY KEY,
  teacher_id         TEXT NOT NULL REFERENCES users(id),
  title              TEXT NOT NULL,
  time_limit_minutes INTEGER NOT NULL CHECK (time_limit_minutes BETWEEN 1 AND 180),
  week               TEXT,
  created_at REAL NOT NULL, updated_at REAL NOT NULL,
  deleted_at REAL                            -- soft delete: results must survive
);

CREATE TABLE questions (
  id            TEXT PRIMARY KEY,
  quiz_id       TEXT NOT NULL REFERENCES quizzes(id),
  position      INTEGER NOT NULL,
  text          TEXT NOT NULL,
  topic         TEXT NOT NULL,
  options_json  TEXT NOT NULL,               -- exactly 4 strings
  correct_index INTEGER NOT NULL CHECK (correct_index BETWEEN 0 AND 3),
  misconceptions_json TEXT                   -- 4 entries, null on the correct one; optional
);

CREATE TABLE sessions (
  id          TEXT PRIMARY KEY,
  quiz_id     TEXT NOT NULL REFERENCES quizzes(id),
  teacher_id  TEXT NOT NULL REFERENCES users(id),
  pin         TEXT NOT NULL,
  status      TEXT NOT NULL CHECK (status IN ('lobby','running','closed','cancelled')),
  time_limit_minutes INTEGER NOT NULL,       -- copied at host time
  created_at REAL NOT NULL, started_at REAL, ends_at REAL, closed_at REAL
);
CREATE UNIQUE INDEX sessions_live_pin ON sessions(pin) WHERE status IN ('lobby','running');

-- Frozen copy of the quiz's questions when the session opens. Editing the quiz later
-- must not rewrite what students in a past session were actually asked.
CREATE TABLE session_questions (
  session_id TEXT NOT NULL REFERENCES sessions(id),
  question_id TEXT NOT NULL,
  position INTEGER NOT NULL, text TEXT NOT NULL, topic TEXT NOT NULL,
  options_json TEXT NOT NULL, correct_index INTEGER NOT NULL, misconceptions_json TEXT,
  PRIMARY KEY (session_id, question_id)
);

CREATE TABLE attempts (
  id             TEXT PRIMARY KEY,
  session_id     TEXT NOT NULL REFERENCES sessions(id),
  student_id     TEXT NOT NULL REFERENCES users(id),
  joined_at      REAL NOT NULL,
  submitted_at   REAL,
  auto_submitted INTEGER NOT NULL DEFAULT 0,
  UNIQUE (session_id, student_id)
);

CREATE TABLE answers (
  attempt_id   TEXT NOT NULL REFERENCES attempts(id),
  question_id  TEXT NOT NULL,
  chosen_index INTEGER CHECK (chosen_index BETWEEN 0 AND 3),
  answered_at  REAL NOT NULL,
  PRIMARY KEY (attempt_id, question_id)      -- upsert until submitted, frozen after
);

CREATE TABLE findings (
  id            TEXT PRIMARY KEY,
  session_id    TEXT NOT NULL REFERENCES sessions(id),
  quiz_id       TEXT NOT NULL, question_id TEXT NOT NULL,
  topic         TEXT NOT NULL,
  chosen_index  INTEGER NOT NULL,
  chosen_count  INTEGER NOT NULL,            -- from SQL, never from the model
  class_size    INTEGER NOT NULL,            -- from SQL, never from the model
  statement     TEXT NOT NULL, uncertainty TEXT NOT NULL, next_step TEXT NOT NULL,
  status        TEXT NOT NULL CHECK (status IN ('awaitingReview','accepted','rejected')),
  rejection_reason TEXT, decided_at REAL,
  run_id        TEXT,                        -- slice run holding the draft/check trail
  review_question_id TEXT,                   -- slice callback question for the teacher
  unverified    TEXT,
  created_at    REAL NOT NULL
);

CREATE TABLE jobs (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, key TEXT NOT NULL,   -- ('findings', session_id)
  status TEXT NOT NULL CHECK (status IN ('queued','running','done','failed')),
  attempts INTEGER NOT NULL DEFAULT 0, error TEXT,
  created_at REAL NOT NULL, updated_at REAL NOT NULL,
  UNIQUE (kind, key)
);
```

### 5.2 Real-time: SSE, backed by the database

The Dart side is already stream-shaped (`Stream<List<AppUser>>`, `Stream<List<StudentProgress>>`,
`Stream<int>`), so Server-Sent Events map onto it with no UI change.

**Implementation: each SSE handler polls SQLite once a second and emits only when the
snapshot changed.** Not an in-memory pub/sub. Reasons: it survives a server restart, works
with more than one worker, has no fan-out bookkeeping, and at classroom scale (≤ 60
connections × 1 small query/s) SQLite does not notice. Use an `async def` generator with
`asyncio.sleep(1)` and a `StreamingResponse(media_type="text/event-stream")`; send
`: keepalive` every 15 s; stop when `await request.is_disconnected()`.

Every SSE endpoint has a plain `GET` twin returning the same snapshot, for clients or
networks where streaming fails. The Flutter side reads SSE with `http`'s streamed
response; no extra package needed.

### 5.3 Quiz editing vs. history

`session_questions` is copied from `questions` when a session is hosted. All results,
aggregates and findings read `session_questions`, never `questions`. Editing or
soft-deleting a quiz therefore never changes a past result.

### 5.4 The clock and the deadline sweeper

The server owns time. `start` sets `ends_at`; every response carrying a deadline carries
`serverNow`; clients compute `remaining = endsAt − serverNow` once and tick locally.

A **sweeper** runs every 5 s (startup task in `api/main.py`):

1. Sessions `running` with `ends_at + 10 s < now` → close them: set `submitted_at` and
   `auto_submitted = 1` on every attempt without one (answers already autosaved are what
   counts), set status `closed`, enqueue the findings job.
2. Sessions in `lobby` older than 3 h → `cancelled`.
3. Calls `slice.callback.sweep(store)` so teacher-review questions past their timeout are
   recorded as `no_reply` (§6.4).

This is what answers two open decisions from `recall-ui-built-context.md` §9: the
teacher's phone dying mid-quiz (the session still closes on time) and a student offline at
0:00 (whatever they autosaved is submitted). The second only works once the client calls
`PUT /attempts/{id}/answers/{qid}` on every choice — a small change to
`AttemptController.choose`.

### 5.5 "The class" — a decision the UI never made

Class Analytics shows "6 quizzes · 42 students"; Quiz Results shows "38 of 42"; the roster
shows attendance out of total quizzes. Nothing in the app defines membership.

**Recommendation for the event:** a teacher's class is *every student who has joined at
least one of that teacher's sessions*. `classSize` = that count at the time the session
closed (store it on the session row when closing, so old results don't drift);
`attended` = sessions joined; `totalQuizzes` = closed sessions. No enrolment screens are
needed. Proper classes (a `classes` table and a join code) are post-event work.

### 5.6 Background jobs

`POST /sessions/{id}/end` must return immediately; the findings agent takes seconds to a
minute and may wait on Groq's rate limit. Use a `jobs` row plus one worker loop started at
app startup (an `asyncio` task that runs the sync agent in `run_in_threadpool`). On startup,
reset `running` jobs to `queued` — that is the resume-after-restart property, same as the
kit's runs. One job at a time keeps inside Groq's 8,000 tokens/minute. Do **not** use
`BackgroundTasks` alone: it dies with the process and leaves nothing to resume.

### 5.7 Auth

- Hash with `hashlib.scrypt` (stdlib, no new dependency): `n=2**14, r=8, p=1`, 16-byte
  salt, compare with `hmac.compare_digest`.
- Token: `secrets.token_urlsafe(32)`, prefixed `rk_`; store only its SHA-256. 30-day expiry.
- Login failure message is identical for unknown identifier and wrong password.
- Flutter stores the token with `shared_preferences` (simplest) or
  `flutter_secure_storage` (better); `restoreSession` calls `GET /auth/me`.
- Authorisation is checked on **ownership**, not just role: a teacher only sees their own
  quizzes/sessions/findings; a student only their own attempts; a teacher sees a student's
  analytics only if that student is in their class (§5.5).

### 5.8 Scoring rules (make them one function)

- A blank counts as **wrong** in the score (matches screen 18's strip; the open decision
  is noted, but one rule in one place makes changing it later a one-line edit).
- Score percent = `round(correct / total * 100)`.
- Topic percent = **pooled** (`Σ correct / Σ answered` over all answers in the topic), not
  the mean of per-question percentages — the built-UI doc flags that the mean hides one
  brutal question among easy ones.
- Distribution bands: `[0,20) [20,40) [40,60) [60,80) [80,100]` of score percent.
- `tookIt` = attempts with ≥ 1 answer; zero-answer attempts count as not taken.
- Put these in `api/analytics.py` and test them directly.

---

## 6. The findings agent — the part that is scored

The Flutter app moved from per-student findings to **class-level gaps**
("19 of 42 students chose an answer that assumes no two keys share a slot"). The existing
`report.py` writes a free-text class report; the app needs **individual, reviewable
findings** with a status. This is a new agent, built the same way.

### 6.1 Candidates come from SQL, not the model

After a session closes, for each question in `session_questions`:

```sql
SELECT a.question_id, a.chosen_index, COUNT(*) AS n
FROM answers a JOIN attempts t ON t.id = a.attempt_id
WHERE t.session_id = ? AND a.chosen_index IS NOT NULL
GROUP BY a.question_id, a.chosen_index
```

A wrong option is a **candidate** when `n >= max(3, ceil(0.25 * respondents))` — a
distractor a quarter of the class converged on is a teaching problem; one student's slip is
not (same reasoning as `roster.class_common_wrong`). Cap at 5 candidates per session,
largest `n` first. Also attach, for each candidate, the same topic's figures from **earlier
sessions of this teacher** — that is the longitudinal read the project was built around
(MAIN_CONTEXT §1), now at class level: "this distractor also beat the answer in Week 6".

### 6.2 Draft → check → back-edge

Per candidate, one `slice` run (`store.create_run("recall_finding", meta={...})`), and a
loop copied from `report._generate`:

- **Draft** (model): `statement`, `uncertainty`, `next_step`, given the question, all four
  options, which one was chosen, the misconception text if the teacher supplied one, the
  counts, and the earlier-session figures.
- **Citation check (code, no model):** the statement contains exactly `chosen_count` and
  `class_size` as the SQL computed them; it names no student; the topic matches. Fail →
  `citation`, back to draft with the reason.
- **Claim-strength check (model):** describes the work, not the students' ability
  ("chose", "answered" — never "doesn't understand", "weak at"); does not claim recurrence
  unless earlier-session figures show it; the uncertainty names a real alternative reading
  of the question. Fail → `claim_strength`, back to draft.
- Three fences, never sharing a counter: `MAX_DRAFTS = 3`, 90 s wall clock, the token
  budget. Out of drafts → store the last one with `unverified` set; the UI shows it.
- Append every draft and check to the run (`store.append`), so
  `GET /findings/{id}/trail` is a read of `store.history(run_id, ...)`.

The overstated first draft being sent back is the live back-edge the rubric requires on
screen (MAIN_CONTEXT §15). `POST /sessions/{id}/findings/regenerate` exists so it can be
triggered in front of a judge.

### 6.3 Prompts

`app/prompts/finding_class.md` and `finding_class_check.md`. Follow the lesson from
`docs/evidence/bug-03`: write the check as an **ordered decision procedure**, not a
preference. Add a test that reads the prompt file, like
`test_compare_prompt_states_a_decision_rule`.

### 6.4 Teacher review is the kit's waiting state

When a finding is stored, call `slice.callback.ask(store, run_id, question, context,
settings)` and keep the returned id in `findings.review_question_id`. `POST
/findings/{id}/decision` calls `slice.callback.answer(...)` and updates the row. The
sweeper's `callback.sweep` turns an unanswered question into a recorded `no_reply` after
`SLICE_EXPERT_TIMEOUT_MINUTES`; the finding stays `awaitingReview` in the queue, but the run
records that the teacher was asked and did not answer — the same "asked vs. confirmed"
distinction as MAIN_CONTEXT §5. Rejected findings (with reasons) are passed to later
drafts for the same topic, so a teacher's rejection changes the next finding rather than
sitting unread.

### 6.5 What accepted findings do

Nothing on the student side yet — the built UI removed next steps from My Performance
(`recall-ui-built-context.md` §8–9), while Review Findings still says "Nothing reaches
students until you accept". Either the copy changes or a destination is added. Out of
scope for the backend until the UI decides.

---

## 7. Flutter side of the swap

1. `pubspec.yaml`: add `http` and `shared_preferences`.
2. `lib/data/api/api_client.dart`: base URL from `--dart-define=API_BASE_URL=…`
   (Android emulator reaches the host at `http://10.0.2.2:8000`; Chrome at
   `http://localhost:8000`), bearer header, error-body → exception with `message`.
3. `fromJson` on each model in `models.dart` (hand-written is fine; 12 small classes).
4. A **student question** without `correctIndex` — either make `correctIndex` nullable or
   add a `StudentQuestion`. Results screens get the full `Question` once released.
5. `Http*Repository` for each of the five interfaces, then change the five `Provider`
   lines in `main.dart`. Keep the mocks for tests and offline demo:
   `--dart-define=USE_MOCKS=true`.
6. Replace the three places screens reach into `Fixtures` (REST_API §10, last rows) and the
   student lobby's 8-second timer.
7. `AttemptController`: hold `attemptId` from `/join` (it currently hard-codes
   `studentId: 'me'`); call autosave in `choose`; use `endsAt − serverNow` for the clock.
8. `SessionRepository`/`AttemptRepository` are stateful (no ids in their method
   signatures); the HTTP implementations keep the current `sessionId`/`attemptId` in a
   field, same as the mocks keep `_quiz`.

Android needs `android:usesCleartextTraffic="true"` (or a network security config) to call
plain `http://10.0.2.2` in debug.

---

## 8. Seed data

`scripts/seed_api.py --reset`:

1. One teacher (`teacher@recall.test` / `password1`), 40 students (`21CS001`… /
   `password1`).
2. Quizzes converted from `app/bank.py` — each department's topics become quizzes, and
   each wrong option's `misconception` fills `misconceptions_json`. That gives the findings
   agent authored diagnoses to work with, exactly as `bank.py` intended.
3. Five closed past sessions with simulated attempts (reuse `simulate.py`'s approach;
   seed a real shared distractor in two of them so findings exist and one recurs).
4. Run the findings job once so the review queue is populated (`--warm`, like
   `simulate.py --warm`; needs a Groq key, `--stub` uses `app/stub.py`-style canned
   drafts for an offline seed).

---

## 9. Build order

Each step ends in a commit (and push, once pushing is authorised) naming what it adds.

| # | step | done when |
|---|---|---|
| 1 | `api/main.py`, `db.py`, schema, `/health`, CORS, error handler, mounted in `webapp.py` | `GET /api/v1/health` returns 200; existing 44 tests still green |
| 2 | Auth: signup/login/me/logout + dependencies | tests: duplicate identifier 409, wrong password 401 with the shared message, token revoked on logout |
| 3 | Quizzes + topics CRUD | tests: validation messages, ownership 403, delete blocked while live |
| 4 | Sessions: host/start/end/cancel, PIN allocation, snapshot | tests: start with nobody 409, end auto-submits, PIN unique among live |
| 5 | Join + attempts: outcomes, autosave, submit, student projection | tests: every `JoinOutcome`, **no `correctIndex` in any student payload**, submit idempotent |
| 6 | Sweeper + SSE endpoints | tests: session past `ends_at` closes itself and auto-submits autosaved answers |
| 7 | `api/analytics.py` + results/analytics/me routers, release gating | tests: `423` before close, median/distribution agree, pooled topic %, student sees only self |
| 8 | Seed script (without findings) | every Flutter screen has real data |
| 9 | Findings agent (`app/findings.py`), jobs worker, findings router, trail | tests: counts come from SQL, citation check rejects a wrong count, overstated draft routed back on `claim_strength`, decision answers the callback |
| 10 | Flutter `Http*Repository` swap (§7) | app runs against the server on emulator and Chrome |
| 11 | End-to-end: teacher hosts on Chrome, two students join on emulator, close, findings appear | recorded for `docs/evidence/` |

Steps 1–7 are plain CRUD and SQL — fast. Step 9 is where the time goes, same as phases
3–4 were for the original pipeline.

---

## 10. Rules carried over from the rest of the project

- Do not edit `slice/`.
- Counts come from SQL; the model interprets them. Never let the model produce a number
  that is shown to a user or checked against.
- Citation-type checks run in code; only judgement-type checks ask a model.
- Never `assert` on model output in a handler; record it or raise a named error.
- Read multi-instance record kinds with `history()`, never `latest()` (MAIN_CONTEXT §2a).
- Copy describes the work, never the person. This applies to API error messages too.
- No model call on the answer path. `PUT /answers` and `/submit` are single SQL writes,
  for the same reasons as MAIN_CONTEXT §17 (scale, rate limits, independent observations).
