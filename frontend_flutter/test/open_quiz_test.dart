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
      final repo = MockResultsRepository();
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
      final repo = MockResultsRepository();
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

        expect(
          await repo.openQuiz(),
          isNull,
          reason: 'a quiz already handed in is not still on offer',
        );
      },
    );

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
}
