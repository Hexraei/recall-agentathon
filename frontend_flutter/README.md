# Recall — Flutter app

A classroom quiz app with two roles on one account system: a teacher builds
and hosts quizzes, and students join by PIN, answer, and get their results
back. This app is currently **standalone** — there is no backend. Every
screen reads and writes through an in-memory mock data layer
(`lib/data/repositories.dart`, seeded from `lib/data/fixtures.dart`), so all
state resets whenever the app is stopped and restarted.

## Requirements

- Flutter SDK matching `environment.sdk` in `pubspec.yaml` (currently `^3.9.2`)
- For Android: an Android emulator or device, with Android toolchain set up
- For iOS: a Mac with Xcode (iOS builds cannot be produced elsewhere)
- For web: any of Flutter's supported web browsers (Chrome is the one this
  project has been tested against)

## Getting started

```bash
cd frontend_flutter
flutter pub get
```

Run `flutter doctor` first if you haven't set up a Flutter toolchain on this
machine before.

## Running the app

```bash
flutter devices          # see what Flutter can see
flutter run -d chrome     # web
flutter run -d <android-device-id>
flutter run -d <ios-device-id>   # macOS only
```

### Signing in

There's no real account system yet, so sign-in is a shortcut: **any
identifier that starts with `s` signs in as the student account; anything
else signs in as the teacher account.** The password just needs to be 4 or
more characters — its value isn't checked further. For example:

- Teacher: `t-iyer` / `pass1234`
- Student: `s2021042` / `pass1234`

## Building

```bash
flutter build apk        # Android
flutter build ios        # iOS, macOS only, needs a signing setup for a real device
flutter build web        # Web
```

## Testing

```bash
flutter analyze
flutter test
```

## Project layout

```
lib/
  main.dart              # app entry point, routing, providers
  route_observer.dart    # shared RouteObserver so dashboards reload on return
  routes.dart            # route names and typed navigation arguments
  data/
    fixtures.dart        # the mock quizzes, users, roster, attempts
    repositories.dart     # mock repository interfaces + implementations
    controllers.dart      # auth/attempt state exposed to the widget tree
  models/                # plain data classes (Quiz, Attempt, QuizAverage, ...)
  screens/
    shared/               # splash, sign in/up
    student/               # join, lobby, question view, results, performance
    teacher/               # quiz builder, host lobby, live monitor, analytics
  widgets/shared/         # cards, bands, charts, sheets, ResponsiveShell, ...
  theme/                  # colors, text styles, metrics
test/                     # widget and repository tests
```

## Responsive behaviour

The design is a 390px-wide mobile layout. On web, `ResponsiveShell`
(`lib/widgets/shared/responsive_shell.dart`) centers that layout inside a
capped content width on wider viewports instead of stretching it edge to
edge; on Android, iOS, and in tests it is a no-op (gated on `kIsWeb`).

## Design reference

The 19 screens (77 named states across them) originate from the HTML design
canvas in `../frontend/*.html` on the `frontend` branch. That folder isn't
part of the shipped app — it's the design source the screens under
`lib/screens/` were built from.
