import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:recall/main.dart';

/// Walks the teacher path and the student path against the mock data layer,
/// which is what the conversion brief asks to be proven before the build is
/// called done.
///
/// The session screens — host lobby, live monitor, student lobby, the attempt
/// — run streams and a one-second ticker that never finish on their own, so
/// they are driven with explicit pumps and left by the route that shuts them
/// down, rather than with pumpAndSettle.

/// The pulsing live dot never stops, so pumpAndSettle would time out on any
/// screen carrying one. Pumping a fixed run of frames advances animations,
/// route transitions and pending mock latency without requiring the tree to
/// ever go still.
Future<void> _settle(WidgetTester tester, {int frames = 24}) async {
  for (var i = 0; i < frames; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

/// Splash restores on a 900ms delay behind a looping animation, so every flow
/// runs the clock past it before doing anything.
Future<void> _bootToAuth(WidgetTester tester) async {
  await tester.pumpWidget(const RecallApp());
  await tester.pump();
  await _settle(tester);
}

/// The mock auth reads the role off the identifier, so both dashboards are
/// reachable without a backend.
Future<void> _signIn(WidgetTester tester, {required bool asStudent}) async {
  await _bootToAuth(tester);

  final fields = find.byType(TextField);
  await tester.enterText(fields.at(0), asStudent ? 's2021042' : 't-iyer');
  await tester.enterText(fields.at(1), 'password');
  await tester.tap(find.widgetWithText(Center, 'Sign in').hitTestable());
  await _settle(tester, frames: 24);
}

Future<void> _tapRow(WidgetTester tester, String label) async {
  final row = find.text(label);
  await tester.ensureVisible(row.first);
  await _settle(tester, frames: 4);
  await tester.tap(row.first);
  await _settle(tester, frames: 24);
}

Future<void> _back(WidgetTester tester) async {
  await tester.tap(find.byIcon(Icons.arrow_back).first);
  await _settle(tester);
}

void main() {
  testWidgets(
    'Teacher path: home to quizzes, analytics, findings and results',
    (tester) async {
      await _signIn(tester, asStudent: false);
      expect(find.text('Host a quiz'), findsWidgets);

      await _tapRow(tester, 'My quizzes');
      expect(find.text('Week 9 · Graphs'), findsWidgets);
      await _back(tester);

      await _tapRow(tester, 'Class analytics');
      expect(find.text('Class average'.toUpperCase()), findsOneWidget);
      expect(find.text('Students'.toUpperCase()), findsOneWidget);

      // A topic opens its class-level page, carrying its gaps.
      await _tapRow(tester, 'Collisions');
      expect(find.text('Class gaps'.toUpperCase()), findsOneWidget);
      await _back(tester);

      // The roster reaches one student's own analytics, which chains four
      // mock loads before it can draw.
      await _tapRow(tester, 'Divya Krishnan');
      await _settle(tester, frames: 24);
      expect(find.text('Attempts'.toUpperCase()), findsOneWidget);
      await _back(tester);
      await _back(tester);

      await _tapRow(tester, 'Review findings');
      expect(
        find.text('Nothing reaches students until you accept'),
        findsOneWidget,
      );
      await _back(tester);

      await _tapRow(tester, 'See full results');
      expect(find.text('How the class scored'.toUpperCase()), findsOneWidget);
      expect(
        find.text('Topics — worst answered first'.toUpperCase()),
        findsOneWidget,
      );
    },
  );

  testWidgets('Teacher path: accepting a finding clears it from the queue', (
    tester,
  ) async {
    await _signIn(tester, asStudent: false);
    await _tapRow(tester, 'Review findings');

    expect(find.text('1 of 3'), findsOneWidget);

    await tester.tap(find.widgetWithText(Center, 'Accept'));
    await _settle(tester, frames: 24);

    expect(find.text('1 of 2'), findsOneWidget);
    expect(
      find.text('Accepted. It is on its way to students.'),
      findsOneWidget,
    );
  });

  testWidgets('Student path: home to result and performance', (tester) async {
    await _signIn(tester, asStudent: true);
    expect(find.text('Join a quiz'), findsWidgets);

    await _tapRow(tester, 'My performance');
    expect(find.text('Your quizzes'.toUpperCase()), findsOneWidget);
    // Nothing on this screen may compare the student to anyone.
    expect(find.textContaining('class average'), findsNothing);
    expect(find.textContaining('rank'), findsNothing);
    await _back(tester);

    await _tapRow(tester, 'See full result');
    expect(find.text('By topic'.toUpperCase()), findsOneWidget);
    expect(find.text('Every question'.toUpperCase()), findsOneWidget);
  });

  testWidgets(
    'Student path: a PIN that matches nothing is the only red state',
    (tester) async {
      await _signIn(tester, asStudent: true);
      await _tapRow(tester, 'Join a quiz');

      await tester.enterText(find.byType(TextField).first, '999999');
      await _settle(tester, frames: 4);
      await tester.tap(find.widgetWithText(Center, 'Join'));
      await _settle(tester, frames: 24);

      expect(
        find.text(
          'No open quiz has this PIN. Check the digits with your teacher.',
        ),
        findsOneWidget,
      );
    },
  );

  testWidgets('Student path: a closed quiz explains itself without red', (
    tester,
  ) async {
    await _signIn(tester, asStudent: true);
    await _tapRow(tester, 'Join a quiz');

    await tester.enterText(find.byType(TextField).first, '111111');
    await _settle(tester, frames: 4);
    await tester.tap(find.widgetWithText(Center, 'Join'));
    await _settle(tester, frames: 24);

    expect(find.text('This quiz has closed'), findsOneWidget);
    expect(find.text('Back to home'), findsOneWidget);
  });

  testWidgets('Student path: answering, reviewing and submitting an attempt', (
    tester,
  ) async {
    await _signIn(tester, asStudent: true);
    await _tapRow(tester, 'Join a quiz');

    await tester.enterText(find.byType(TextField).first, '408217');
    await _settle(tester, frames: 4);
    await tester.tap(find.widgetWithText(Center, 'Join'));
    await _settle(tester, frames: 24);

    // The lobby waits for the teacher, then hands over to question 1.
    expect(find.text('Waiting to start'), findsOneWidget);
    await _settle(tester, frames: 110);

    expect(find.text('Question 1 of 15'), findsOneWidget);
    expect(find.text('Time left'), findsOneWidget);

    // Answer the first question, then jump straight to Review & submit.
    await tester.tap(find.text('A slot index in the table'));
    await tester.pump();

    await _tapRow(tester, 'Review & submit');
    expect(find.text('Review & submit'), findsWidgets);
    expect(
      find.textContaining('14 questions have no answer yet'),
      findsOneWidget,
    );

    // Submitting with blanks is allowed; the sheet names them first.
    await tester.tap(find.widgetWithText(Center, 'Submit'));
    await _settle(tester);
    expect(find.text('Submit with 14 blank?'), findsOneWidget);

    await tester.tap(find.widgetWithText(Center, 'Submit anyway'));
    await _settle(tester, frames: 24);

    // The receipt carries no score anywhere.
    expect(find.text('Submitted'), findsOneWidget);
    expect(find.text('Questions answered'), findsOneWidget);
    expect(find.text('1 of 15'), findsOneWidget);
    expect(find.textContaining('correct'), findsNothing);
  });

  testWidgets('Teacher path: hosting a quiz reaches the live monitor', (
    tester,
  ) async {
    await _signIn(tester, asStudent: false);

    await _tapRow(tester, 'Host a quiz');
    await _tapRow(tester, 'Host');

    expect(find.text('JOIN PIN'), findsOneWidget);
    // The PIN is what students type, so it must be on screen before anyone
    // can join.
    expect(find.text('408 217'), findsOneWidget);

    // Students arrive about a second apart; Start unlocks once one has.
    await _settle(tester, frames: 14);
    expect(find.textContaining('joined'), findsOneWidget);

    await tester.tap(find.widgetWithText(Center, 'Start the quiz'));
    await _settle(tester, frames: 24);

    expect(find.text('Running'), findsOneWidget);
    expect(find.text('TIME LEFT'), findsOneWidget);

    // Leaving is only possible by ending the quiz, which closes the window
    // and stops the ticker.
    await tester.tap(find.text('Exit quiz'));
    await _settle(tester, frames: 4);
    await tester.tap(find.widgetWithText(Center, 'End it now'));
    await _settle(tester, frames: 24);

    expect(find.text('WINDOW CLOSED'), findsOneWidget);
    expect(find.text('See class results'), findsOneWidget);
  });
}
