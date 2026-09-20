import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:recall/data/fixtures.dart';
import 'package:recall/data/repositories.dart';
import 'package:recall/main.dart';
import 'package:recall/models/models.dart';

/// Regressions for three things that contradicted each other on the student
/// dashboard: a banner advertising a quiz that had already closed, a result
/// released before the quiz window shut, and "Open now" asking for a PIN the
/// app had just displayed.

Future<void> _settle(WidgetTester tester, {int frames = 24}) async {
  for (var i = 0; i < frames; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

Future<void> _signInAsStudent(WidgetTester tester) async {
  await tester.pumpWidget(const RecallApp());
  await tester.pump();
  await _settle(tester);

  final fields = find.byType(TextField);
  await tester.enterText(fields.at(0), 's2021042');
  await tester.enterText(fields.at(1), 'password');
  await tester.tap(find.widgetWithText(Center, 'Sign in').hitTestable());
  await _settle(tester, frames: 24);
}

void main() {
  group('the data itself stays coherent', () {
    test('the open quiz has no closing time, so it cannot have a result', () {
      final open = Fixtures.hashTables;
      expect(
        open.closedAt,
        isNull,
        reason: 'a quiz students can still join has not closed',
      );
    });

    test('a student history holds only quizzes that have closed', () async {
      final repo = MockResultsRepository(MockAuthRepository());
      final attempts = await repo.myAttempts();

      expect(attempts, isNotEmpty);
      for (final a in attempts) {
        expect(
          a.quiz.closedAt,
          isNotNull,
          reason: 'results appear only after the window closes',
        );
      }
      expect(
        attempts.map((a) => a.quiz.id),
        isNot(contains(Fixtures.hashTables.id)),
        reason: 'the quiz that is still open must not be in results',
      );
    });

    test('isClosed gates the open quiz and allows a finished one', () {
      final repo = MockResultsRepository(MockAuthRepository());
      expect(repo.isClosed(Fixtures.hashTables.id), isFalse);
      expect(repo.isClosed(Fixtures.graphs.id), isTrue);
    });
  });

  group('the open-quiz banner', () {
    test(
      'offers the quiz that is open, and stops once it is submitted',
      () async {
        final repo = MockAttemptRepository();

        final before = await repo.openQuiz();
        expect(before, isNotNull);
        expect(before!.quiz.id, Fixtures.hashTables.id);
        expect(before.pin.replaceAll(' ', ''), '408217');

        await repo.submit(Attempt(quizId: before.quiz.id, studentId: 'me'));

        final next = await repo.openQuiz();
        expect(
          next?.quiz.id,
          isNot(before.quiz.id),
          reason: 'a quiz already handed in is not still on offer',
        );
      },
    );

    test('the banner follows the quiz last found by PIN', () async {
      final repo = MockAttemptRepository();

      // Nothing found yet, so it offers whichever session is running.
      final initial = await repo.openQuiz();
      expect(initial!.quiz.id, Fixtures.hashTables.id);

      // Look up the other live PIN, then back out without joining.
      final started = await repo.join('333333');
      expect(started.outcome, JoinOutcome.alreadyStarted);
      expect(started.quiz!.id, Fixtures.trees.id);

      final after = await repo.openQuiz();
      expect(
        after!.quiz.id,
        Fixtures.trees.id,
        reason: 'the banner should offer the quiz just looked up',
      );
      expect(
        after.pin.replaceAll(' ', ''),
        '333333',
        reason: 'and carry that PIN, not the default one',
      );
    });

    test('a PIN that is not live does not become the banner', () async {
      final repo = MockAttemptRepository();
      await repo.join('333333');
      await repo.join('111111'); // closed
      await repo.join('999999'); // not found

      final open = await repo.openQuiz();
      expect(
        open!.quiz.id,
        Fixtures.trees.id,
        reason: 'a closed or unknown PIN must not displace a live one',
      );
    });

    test('submitting the followed quiz falls back to the other one', () async {
      final repo = MockAttemptRepository();
      await repo.join('333333');
      await repo.submit(Attempt(quizId: Fixtures.trees.id, studentId: 'me'));

      final open = await repo.openQuiz();
      expect(open!.quiz.id, Fixtures.hashTables.id);
    });

    test('rejoining something already submitted says so', () async {
      final repo = MockAttemptRepository();
      await repo.submit(
        Attempt(quizId: Fixtures.hashTables.id, studentId: 'me'),
      );

      final result = await repo.join('408217');
      expect(result.outcome, JoinOutcome.alreadySubmitted);
    });
  });

  testWidgets('the banner names the open quiz, not one already in results', (
    tester,
  ) async {
    await _signInAsStudent(tester);

    expect(find.textContaining('Open now'), findsOneWidget);
    expect(find.textContaining('Open now · Hash tables'), findsOneWidget);

    // The quiz being offered must not also be sitting in the history below it.
    expect(find.text('Hash tables'), findsNothing);
  });

  group('a quiz row states whether it has been conducted', () {
    test('the open quiz reads as running, not as conducted', () {
      expect(Fixtures.hashTables.isRunning, isTrue);
      expect(Fixtures.hashTables.isConducted, isFalse);
    });

    test('a closed quiz reads as conducted', () {
      expect(Fixtures.graphs.isConducted, isTrue);
      expect(Fixtures.graphs.isRunning, isFalse);
    });

    test('a quiz never hosted is neither', () {
      const draft = Quiz(
        id: 'draft',
        title: 'Sorting',
        questions: [],
        timeLimitMinutes: 15,
      );
      expect(draft.hasRun, isFalse);
      expect(draft.isRunning, isFalse);
      expect(draft.isConducted, isFalse);
    });
  });

  testWidgets('My quizzes tags a conducted quiz and the running one', (
    tester,
  ) async {
    await tester.pumpWidget(const RecallApp());
    await tester.pump();
    await _settle(tester);

    final fields = find.byType(TextField);
    await tester.enterText(fields.at(0), 't-iyer');
    await tester.enterText(fields.at(1), 'password');
    await tester.tap(find.widgetWithText(Center, 'Sign in').hitTestable());
    await _settle(tester, frames: 24);

    await tester.tap(find.text('My quizzes'));
    await _settle(tester, frames: 24);

    expect(find.text('Conducted'), findsWidgets);
    // Two quizzes are live in the mock: one waiting in its lobby and one
    // already under way.
    expect(find.text('Running now'), findsNWidgets(2));
    expect(find.textContaining('still open'), findsNWidgets(2));
  });

  testWidgets('tapping "Open now" does not ask for the PIN again', (
    tester,
  ) async {
    await _signInAsStudent(tester);

    await tester.tap(find.textContaining('Open now'));
    await _settle(tester);

    expect(find.text('Join a quiz'), findsOneWidget);

    final field = tester.widget<TextField>(find.byType(TextField).first);
    expect(
      field.controller!.text.replaceAll(' ', ''),
      '408217',
      reason: 'the PIN travels with the banner',
    );
  });

  testWidgets('the dashboard drops the banner after a lobby-started attempt is '
      'submitted, not just an already-started one', (tester) async {
    // A quiz joined before the teacher starts it goes through the lobby,
    // which later hands off to the question view with
    // pushReplacementNamed. That replace completes the *first* pushed
    // route's future — the one the banner's tap was relying on for its
    // reload — long before the attempt is anywhere near submitted. Only
    // the already-started path (tested above, via a straight push chain)
    // happened to exercise the working case; this is the one that found
    // the bug.
    await _signInAsStudent(tester);

    // Submit the other live quiz first, through its already-started
    // shortcut, so Hash tables joined below is the only one left open.
    await tester.tap(find.text('Join a quiz'));
    await _settle(tester, frames: 4);
    await tester.enterText(find.byType(TextField).first, '333333');
    await _settle(tester, frames: 4);
    await tester.tap(find.widgetWithText(Center, 'Join'));
    await _settle(tester, frames: 24);
    await tester.tap(find.widgetWithText(Center, 'Join now'));
    await _settle(tester, frames: 24);
    await tester.tap(find.text('Review & submit'));
    await _settle(tester, frames: 24);
    await tester.tap(find.widgetWithText(Center, 'Submit'));
    await _settle(tester);
    await tester.tap(find.widgetWithText(Center, 'Submit anyway'));
    await _settle(tester, frames: 24);
    await tester.tap(find.widgetWithText(Center, 'Back to home'));
    await _settle(tester, frames: 24);
    expect(find.textContaining('Hash tables'), findsOneWidget);

    await tester.tap(find.textContaining('Open now'));
    await _settle(tester, frames: 4);
    await tester.tap(find.widgetWithText(Center, 'Join'));
    await _settle(tester, frames: 24);
    expect(find.text('Waiting to start'), findsOneWidget);

    // Past the lobby's own auto-start timer.
    await tester.pump(const Duration(seconds: 9));
    await _settle(tester, frames: 24);
    expect(find.textContaining('Question 1 of'), findsOneWidget);

    await tester.tap(find.text('Review & submit'));
    await _settle(tester, frames: 24);
    await tester.tap(find.widgetWithText(Center, 'Submit'));
    await _settle(tester);
    await tester.tap(find.widgetWithText(Center, 'Submit anyway'));
    await _settle(tester, frames: 24);
    expect(find.text('Submitted'), findsOneWidget);

    await tester.tap(find.widgetWithText(Center, 'Back to home'));
    await _settle(tester, frames: 24);

    expect(
      find.textContaining('Open now'),
      findsNothing,
      reason:
          'the quiz just submitted was the only one left open, so the '
          'dashboard must reload rather than show what it cached before '
          'the attempt started',
    );
  });
}
