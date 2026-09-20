# Recall — Flutter Conversion Prompt

**What this is.** A complete, standalone task brief for building the Recall Flutter app
from the 19 Claude-Design screens already drafted in `frontend/*.html`. It is meant to be
handed to a fresh Claude Code session — in this repository, but with no memory of any prior
conversation about this project — as the instruction to build the app **fully, end to end,
autonomously**. Nobody will be present to answer questions mid-build. Where this document
doesn't resolve something, make the most reasonable call, note it in a commit message or
in `frontend/context/`, and keep going rather than stopping to ask.

**One-paragraph background, for a session with no other context.** Recall is a classroom
quiz app being built for a hackathon (CEG ASTRA Agent-a-thon). A teacher writes four-option
multiple-choice questions, hosts a session, and reviews class performance including
recurring learning gaps flagged across quizzes over a semester. A student joins with a PIN,
answers at their own pace against a single whole-quiz deadline (no per-question timers, no
leaderboard), and afterwards sees only their own results. The UI/UX has already been fully
designed and reviewed on Claude Design's canvas; this task is the frontend implementation
of that finished design in Flutter — not further design work, and not backend work.

**Why a prompt, not just a spec.** The three documents this brief draws on
(`recall-ui-built-context.md`, `frontend-ui-context-v2.md`, and the HTML files themselves)
describe *what was designed*. This document describes *how to turn that into Flutter
code*, in what order, and what "matches the design" means well enough to check it.

**Start here, in order:**
1. Read this document in full.
2. Read `frontend/context/recall-ui-built-context.md` (the as-built design system).
3. Read `frontend/context/frontend-ui-context-v2.md` (the functional spec, all 19 screens).
4. Proceed to §2 below and start building. Do not wait for confirmation between steps,
   between screens, or before committing — build the whole app in this one session.

---

## 1. Inputs, and which one wins

Three sources exist. They disagree occasionally — usually because the written docs
describe intent and the canvas is what actually got drawn. When they disagree, this is the
order of precedence:

1. **The rendered HTML screen itself** (`frontend/<name>_screenN.html`), viewed in a
   browser. This is the pixel-accurate source of truth for layout, spacing, exact colors,
   type, and component structure on that specific screen.
2. **`frontend/context/recall-ui-built-context.md`** — the as-built design system
   (palette, type scale, radii, shared components, what departed from the brief). Use this
   to understand *why* a screen looks the way it does, and to keep screens consistent with
   each other when the canvas alone doesn't make a rule obvious (e.g. exact hex values that
   are hard to eyedrop precisely from a screenshot).
3. **`frontend/context/frontend-ui-context-v2.md`** (or the earlier
   `docs/context/frontend-ui-context.md`) — the functional spec. Use this for *behavior*
   the static HTML can't show: what happens on tap, what the empty/error/loading states
   are, what data a screen needs, and which states must exist even if only one is drawn on
   the canvas.

**A visual detail on the canvas beats a written description of it. A behavior in the
functional spec that has no corresponding artboard still must be built** — the HTML files
only show the states that were drawn, not necessarily all of them.

### A rendering gotcha, found while inspecting these files

The HTML files in `frontend/` are Claude Design canvas exports (`dc-runtime` bundles): each
artboard's actual markup is gzip-compressed, base64-encoded, and nested inside JSON that a
runtime script unpacks in the browser at load time. **Opening the file as text (Read tool,
grep, cat) shows only the unpacking runtime and compressed payloads — not the design.**
These files only render correctly when loaded in an actual browser, where the bundler
script runs and reconstructs the page. Any step below that says "view the screen" means
open it in a real browser (the built-in browser tool, or a local static file server plus a
screenshot), not read it as a file.

Each HTML file contains multiple artboards (states/variants of that screen stitched onto
one canvas) — `recall-ui-built-context.md` says 77 artboards across 19 files, roughly 4 per
screen. Expect to scroll/pan the rendered canvas to find all of them, not just the first
one visible.

---

## 2. Technical decisions for the Flutter project

No Flutter project exists in this repo yet — it needs to be created. The choices below are
sensible defaults for this project's scope (single developer/team, hackathon timeline, UI
built ahead of a real backend). They are not locked; if a default turns out to be wrong
once building starts (e.g. a package conflict), change it and note why in a commit message
— don't stop to ask, since no one is present to answer.

| Decision | Default | Why |
|---|---|---|
| Project location | `recall-agentathon/frontend_flutter/` (new folder, sibling to `frontend/`, on the **same `frontend` branch** as the HTML designs) | Keeps the design canvas exports and the Flutter source in one place in history; no new branch is created for this work |
| Target platforms | Android, iOS, and Web (`flutter create --platforms=android,ios,web`) | Web matters here for quick demoing without a device/emulator — verify the app actually builds for web, not just mobile, since font/asset handling can differ |
| State management | `provider` package, simple `ChangeNotifier`s per feature area | Lightest option that still avoids prop-drilling across the dashboard → session → results flow; nothing here needs Bloc/Riverpod's ceremony |
| Navigation | Named routes via Flutter's built-in `Navigator`, one route table split by role | The navigation map in the functional spec (§4) is a small fixed tree, not deep-linked — doesn't need `go_router` |
| Fonts | `google_fonts` package for Fraunces and IBM Plex Sans | No manual font licensing/asset bundling needed; confirm it renders correctly under `flutter build web` too, since web font loading can behave differently from mobile |
| Data layer | Mock/in-memory data matching the record shapes implied by the functional spec, behind a small repository interface per feature | No backend is wired yet (per the standalone-frontend decision); the interface boundary means swapping in real API calls later doesn't touch UI code |
| Folder structure | `lib/theme/` (colors, type, radii from the design system), `lib/widgets/shared/` (option card, countdown, nav list, pulsing dot), `lib/screens/teacher/`, `lib/screens/student/`, `lib/screens/shared/`, `lib/models/`, `lib/data/` (mock repositories) | Mirrors the role split already in the functional spec and design docs |

**Build the theme and shared components first, before any screen**, since every screen
depends on them:
- `lib/theme/colors.dart` — every hex value from §3 of `recall-ui-built-context.md`
- `lib/theme/text_styles.dart` — Fraunces/IBM Plex Sans scale, per §3
- `lib/widgets/shared/option_card.dart` — unselected/selected/correct/incorrect variants
- `lib/widgets/shared/countdown.dart` — the one countdown component used on 3 screens
- `lib/widgets/shared/nav_list.dart` — the reusable list-with-chevron component
- `lib/widgets/shared/live_dot.dart` — the pulsing indicator

---

## 3. Per-screen conversion procedure

Work through the screen inventory in `frontend-ui-context-v2.md` §7 in order, one screen
fully finished — built, verified, checked off — before starting the next. This mirrors how
the screens were designed.

For each screen:

1. **Open the corresponding HTML file in a browser** and locate every artboard on that
   canvas (a screen typically has 3–5: default state, empty state, error state, and any
   role-specific variant).
2. **Read that screen's entry** in `frontend-ui-context-v2.md` §7.1–7.19 for its purpose,
   contents, actions and required states — including any state not drawn on the canvas.
3. **Cross-check ambiguous visual details** (an exact color that's hard to eyedrop, a
   spacing value) against `recall-ui-built-context.md` §3–4 rather than guessing from the
   screenshot.
4. **Build the screen as a Flutter widget**, reusing the shared components from §2 rather
   than re-implementing option cards, countdowns, etc. per screen.
5. **Wire it to the mock data layer**, not hardcoded literals inside the widget, so later
   screens that read the same data (e.g. a quiz's title and question count, shown on both
   Host Lobby and Live Monitor) stay consistent.
6. **Implement every required state**, not just the one that happened to be drawn:
   loading, empty/first-run, error, and any role-specific variant named in the functional
   spec.
7. **Verify against the checklist below**, then mark the screen `☑` in the inventory table
   in `frontend-ui-context-v2.md` §7 (or a working copy of it) before moving on.

### Suggested order

Per the "order of work" note already in `frontend-ui-context-v2.md` §7: build the theme and
shared components (§2 above) first, then **Question View (screen 15)** and **both
dashboards (screens 3 and 12)** before the rest — they carry the navigation pattern, card
style and typographic hierarchy every other screen inherits. After those three, the
remaining sixteen follow the numbered order.

---

## 4. Verification checklist (per screen)

A screen is not done until all of these hold:

- [ ] Colors match `recall-ui-built-context.md` §3 exactly — no ad-hoc hex values invented
      because a screenshot color looked "close enough"
- [ ] Fraunces is used for headings and any number meant to be read as a result; IBM Plex
      Sans for everything else, including the PIN and countdown
- [ ] Control radius 10px, container radius 14px; buttons/inputs 52px; no tap target under
      44px
- [ ] Any shared component (option card, countdown, nav list, live dot) is the actual
      shared widget, not a copy-pasted one-off
- [ ] Every state required by the functional spec exists, including ones not drawn on the
      canvas (loading, empty/first-run, error)
- [ ] Nothing from the exclusions list (`frontend-ui-context-v2.md` §9 /
      `recall-ui-built-context.md` §2) has crept back in — no leaderboard, no per-question
      timer, no colour-/shape-coded options, no free-text answer input, no nickname field,
      no peer comparison
- [ ] Interface copy describes the student's work, never their ability or character
- [ ] Session-flow screens (host lobby, join, lobby, the attempt) use a plain text
      back-action (Cancel/Leave/Exit quiz/Back to questions), not a back chevron, per
      `recall-ui-built-context.md` §3
- [ ] The screen is checked off in the inventory table

---

## 5. Git conventions for this session

- Work directly on the `frontend` branch — do not create a new branch for this.
- Commit incrementally as you go rather than as one giant commit at the end: a reasonable
  granularity is one commit per shared component set (§2) and one commit per screen (or
  small group of related screens), so the history shows the same one-at-a-time progression
  the design itself was built in.
- Each commit message should name the screen(s) or component(s) it adds, not just "progress"
  or "wip".
- If a technical default from §2 is changed mid-build, say so in the commit that changes it
  and why.
- Do not push to any remote unless separately instructed — commit locally only.

---

## 6. Definition of done

This task is finished when, in one uninterrupted session:

- All 19 screens from the inventory in `frontend-ui-context-v2.md` §7 exist as Flutter
  widgets and are checked off.
- `flutter analyze` runs clean (no errors; warnings should be resolved where reasonable).
- The app builds successfully for Android, iOS, and Web (`flutter build apk`,
  `flutter build ios --no-codesign`, `flutter build web` — or the equivalent checks
  available in the environment actually running this).
- Navigating the full teacher path and the full student path (per the workflows in
  `frontend-ui-context-v2.md` §5–6) works against the mock data layer without crashing.
- Every item in the §4 verification checklist holds for every screen, not just a sample.
- Progress and decisions are committed on the `frontend` branch per §5, not left
  uncommitted at the end of the session.

---

## 7. What this prompt deliberately leaves open

- **No real backend integration.** Mock data only; the repository-interface boundary in §2
  is what makes wiring a real API later a data-layer change, not a UI rewrite.
- **No decision yet on how confirmed teacher findings reach the student's My Performance
  screen in real time** — for now, mock data can just reflect a confirmed state; the actual
  sync mechanism is a backend question, not a frontend one.
- **Tablet/larger-screen layout is not addressed** — the design canvas is 390×844 (phone)
  throughout; whether the host's screens need a distinct larger layout was never decided
  and isn't assumed here.
