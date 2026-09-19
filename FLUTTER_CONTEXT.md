# Flutter app — build context

The mobile app's one job is to show **persistent memory working, and persistent
memory not working**, on a phone, while a person standing next to it explains
what is happening.

---

## The rule that shapes everything here

**The app states what happened. It never states why.**

When a sitting comes back with no pattern found, or a claim that looks wrong,
the presenter explains that live. The screen's job is to show the record
clearly enough that the explanation lands — not to pre-empt it.

Concretely, in the UI:

- ✅ "No repeat found." / "Repeat found — cites 2 earlier answers." / "Waiting on
  a professor."
- ❌ "No repeat found *because the sittings share no concept*."
- ❌ "This is expected behaviour" / "working as intended" / "this is a limitation of…"
- ❌ Any tooltip, caption, empty-state or error copy that diagnoses a cause.

The API is built to make this easy: it returns records and an `outcome` word,
and there is deliberately **no `reason` or `why` field anywhere in it**. If a
screen feels like it needs one, that is the presenter's line, not the app's.

The one exception is the **provenance disclosure** (below), which is a
statement of fact about the data and must always be visible.

---

## Always on screen: the disclosure

Every endpoint returns a `disclosure` string. Show it — a footer, a banner, an
info chip on the record screen. Do not let the app render this data without it.

> Every answer in this record is a real answer from a real student who took this
> quiz. The timeline is constructed: separate real students are shown here as one
> person sitting the quiz several times, because the system detects mistakes that
> repeat across separate occasions and a two-day event cannot produce that
> naturally.

Every sitting also carries `real_answers_from` (the real student whose answers
these are) and `synthetic_timeline: true`. Surfacing the name on the sitting
detail screen is the strongest honesty signal the app has — it shows, per
record, exactly which part is real.

---

## The API

Read-only JSON, served by the existing FastAPI process, mounted at
`/api/memory`. Source: [`app/memory_api.py`](app/memory_api.py).

```bash
.venv/bin/python webapp.py          # http://localhost:8000
curl localhost:8000/api/memory/students
```

It reads `memory.db`, which is **separate from the live quiz database**
(`webapp.db`). Nothing the app can do writes anything.

### `GET /api/memory/students`

The list screen. Each identity:

| field | meaning |
|---|---|
| `student_id` | pass to the next route |
| `name`, `department` | display |
| `sittings` | how many times this identity sat the quiz |
| `found_a_repeat` | true if any sitting found one |
| `awaiting_human` | true if any sitting is parked on a professor |

### `GET /api/memory/student/{student_id}`

The main screen. `sittings` is **oldest first** — render it as a vertical
timeline and the persistence tells itself: sitting 1 has nothing behind it,
each later one decides against everything before it.

Per sitting:

| field | meaning |
|---|---|
| `sitting`, `date`, `score` / `asked` | the occasion |
| `outcome` | **key the UI off this** — `first`, `found`, `none_found` |
| `label` | the agent's own word (`recurring`, `similar`, `not_enough_evidence`, `improving`) |
| `explanation` | the agent's own sentences. Render verbatim, never summarise |
| `cited_answers` | question refs, e.g. `cs_t4_q1#C` |
| `prior_sittings_visible` | how many earlier sittings this one could read — `0` on sitting 1 |
| `finding` | `status`, `statement`, `uncertainty`, `next_step`, `cites` |
| `awaiting_human` | true = the agent stopped and handed the decision to a professor |
| `real_answers_from` | the real student behind this sitting |

`summary` gives `total_sittings`, `repeats_found`, `no_repeat_claimed`,
`awaiting_human`.

### `GET /api/memory/sitting/{run_id}`

Detail. Everything above plus `answers[]`, each with `ref`, `concept`,
`kind` (`strength` | `difficulty`), `detail`, and **`cited_here`** — true if the
agent cited that specific answer.

Put the citation next to the claim. A claim shown beside the actual answers it
rests on is checkable by whoever is watching; the same claim alone is an
assertion.

---

## The three states to design for

`outcome` has exactly three values. All three are real screens — the second is
not an error state and must not look like one.

**`first`** — sitting 1. Nothing to compare against yet.
> *"First sitting. Nothing earlier to compare against."*

**`found`** — the agent identified a repeat and cited it. Show `explanation`,
`cited_answers`, and the cited answers themselves.
> *"Repeat found — cites cs_t4_q1, cs_t1_q4."*

**`none_found`** — the agent looked, had history, and did not claim a pattern.
**Style this as a normal, confident result.** Not grey, not an empty state, not
an error card. Show the `label` and the `explanation` verbatim.
> *"No repeat claimed."*

`none_found` is the demo, as much as `found` is. A system that always finds
something is not detecting anything.

---

## Showing it fail

You asked to be able to show this breaking. Two honest ways, no rigging needed.

**1. Show a sitting with its memory removed.** The demo DB is a file. Copy it,
delete the earlier sittings for one identity, point the app at the copy: a
sitting that previously found a repeat now returns `first`. Same code, same
answers, no history — the memory *is* the feature.

```bash
cp memory.db memory-broken.db
# delete the earlier runs for one identity, then serve that file
```

**2. Show a sitting the agent got wrong, or nearly wrong.** Some sittings in the
data return a `recurring` claim resting on a thinner connection than others, and
some return `similar` where a person might have expected `recurring`. Both are
in `memory.db` now. The app shows the claim and its citations; you say what is
wrong with it.

Leave `awaiting_human` visible in both cases. A run parked on a professor is the
system declining to decide — that is a load-bearing part of the story.

---

## Suggested screens

1. **Identity list** — name, department, sitting count, whether a repeat was
   found, whether anything is awaiting a human. Disclosure in the footer.
2. **Timeline** — the sittings, oldest at top. One card each: date, score,
   outcome chip, the agent's explanation. Make `prior_sittings_visible` visible
   somewhere ("could see 0 earlier sittings" → "could see 3").
3. **Sitting detail** — the finding, then the answers, with cited ones marked.

---

## Practical notes

- **Base URL.** `http://localhost:8000` on desktop; the Android emulator needs
  `http://10.0.2.2:8000`. On a real phone use the machine's LAN IP, or the
  ngrok tunnel if one is up.
- **`503` from the API** means `memory.db` has not been built. Rebuild:
  ```bash
  .venv/bin/python tools/build_memory_demo.py --force
  .venv/bin/python tools/run_memory_demo.py
  ```
  The second step makes real model calls and takes a few minutes. Sittings must
  be replayed in order — that is what gives the later ones a history to read.
- **Cache the responses in the app.** They are static between rebuilds, and a
  demo should not depend on the network being good in the room.
- **Don't write to `webapp.db` from the app.** Real students' answers live
  there. The memory API cannot touch it.

Background on how the demo data was built, and what is real in it:
[`docs/memory-demo.md`](docs/memory-demo.md).
