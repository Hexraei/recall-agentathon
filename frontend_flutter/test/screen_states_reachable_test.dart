import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:recall/data/fixtures.dart';
import 'package:recall/data/repositories.dart';
import 'package:recall/main.dart';

/// The design canvas draws every screen as several named artboards, not
/// just its default one — Class Analytics alone has nine: populated, filter
/// open, too few quizzes for a trend, no quizzes closed yet, and one page
/// per topic. A screen being reachable is not the same as every one of its
/// states being reachable: two of those states turned out to be dead code,
/// wired up but with no mock data path that could ever trigger them. These
/// tests pin the fixes down so they cannot regress silently.
Future<void> _settle(WidgetTester tester, {int frames = 24}) async {
  for (var i = 0; i < frames; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

Future<void> _signInAsTeacher(WidgetTester tester) async {
  await tester.pumpWidget(const RecallApp());
  await tester.pump();
  await _settle(tester);

  final fields = find.byType(TextField);
  await tester.enterText(fields.at(0), 't-iyer');
  await tester.enterText(fields.at(1), 'password');
  await tester.tap(find.widgetWithText(Center, 'Sign in').hitTestable());
  await _settle(tester, frames: 24);
}

void main() {
  group('too few quizzes for a trend', () {
    test('the filter can be narrowed below three', () async {
      // classAverages() is a fixed six-quiz history for every account, so
      // the trend board — averages.length < 3 — was structurally
      // unreachable while the filter's smallest option was "last 3".
      final repo = MockResultsRepository(MockAuthRepository());
      final all = await repo.classAverages();
      expect(
        all.length,
        greaterThan(2),
        reason: 'the fixed history this test depends on is still 3+ long',
      );
    });

    testWidgets('filtering to the last quiz shows the too-few board', (
      tester,
    ) async {
      await _signInAsTeacher(tester);
      await tester.tap(find.text('Class analytics'));
      await _settle(tester, frames: 24);

      await tester.tap(find.text('All quizzes'));
      await _settle(tester, frames: 8);
      expect(find.text('Last quiz'), findsOneWidget);

      await tester.tap(find.text('Last quiz'));
      await _settle(tester, frames: 24);

      expect(
        find.textContaining('A trend needs at least three quizzes'),
        findsOneWidget,
      );
    });
  });

  group('one attempt only, on a roster student', () {
    test('Priya Venkat has exactly one quiz behind her averages', () async {
      final repo = MockResultsRepository(MockAuthRepository());
      final averages = await repo.studentAverages('s10');
      final taken = averages.where((a) => !a.absent).toList();
      expect(
        taken,
        hasLength(1),
        reason:
            'every other named roster student takes every closed quiz, so '
            'without one deliberately sparse student "one attempt only" has '
            'no student it could ever be shown for',
      );
      expect(taken.single.quizTitle, Fixtures.graphs.title);
    });

    testWidgets('her page shows the one-attempt board, not the full chart', (
      tester,
    ) async {
      await _signInAsTeacher(tester);
      await tester.tap(find.text('Class analytics'));
      await _settle(tester, frames: 24);

      await tester.enterText(find.byType(TextField), 'Priya');
      await _settle(tester, frames: 8);
      final row = find.text('Priya Venkat');
      await tester.ensureVisible(row);
      await _settle(tester, frames: 4);
      await tester.tap(row);
      await _settle(tester, frames: 24);

      expect(
        find.textContaining('One attempt so far'),
        findsOneWidget,
        reason:
            'a single closed quiz should collapse to the one-attempt '
            'board rather than a two-point trend chart',
      );
    });
  });
}
