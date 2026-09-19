import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:recall/main.dart';
import 'package:recall/theme/colors.dart';

/// Splash restores the session on a 900ms delay and animates a looping bar
/// while it does, so a test that stops on Splash would leave both a pending
/// timer and a never-settling animation. Every test below runs the clock past
/// the restore first, which disposes Splash and lands on the auth screen.
Future<void> _bootToAuth(WidgetTester tester) async {
  await tester.pumpWidget(const RecallApp());
  await tester.pump();
  await tester.pump(const Duration(seconds: 1));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('Splash shows the lockup while the session restores', (
    tester,
  ) async {
    await tester.pumpWidget(const RecallApp());
    await tester.pump();

    expect(find.text('Recall'), findsOneWidget);
    expect(find.text('Restoring your session'), findsOneWidget);

    // Let the restore finish so Splash is disposed with nothing left pending.
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
  });

  testWidgets('An unrestored session lands on sign in', (tester) async {
    await _bootToAuth(tester);

    expect(find.text('Sign in'), findsWidgets);
    expect(find.text('Use your college email or roll number.'), findsOneWidget);
  });

  testWidgets('The ground colour is the warm off-white, not white', (
    tester,
  ) async {
    await _bootToAuth(tester);

    final scaffold = tester.widget<Scaffold>(find.byType(Scaffold).first);
    expect(scaffold.backgroundColor, AppColors.ground);
  });

  testWidgets('Sign in is where the account is created from too', (
    tester,
  ) async {
    await _bootToAuth(tester);

    // The toggle is one Text.rich, so its label only matches with
    // findRichText; the tap target is the GestureDetector wrapping it.
    final toggle = find
        .ancestor(
          of: find.textContaining('Create an account', findRichText: true),
          matching: find.byType(GestureDetector),
        )
        .first;
    await tester.ensureVisible(toggle);
    await tester.pumpAndSettle();
    await tester.tap(toggle);
    await tester.pumpAndSettle();

    expect(find.text('Create your account'), findsOneWidget);
    // Role is chosen once at sign-up and presented as permanent.
    expect(find.text('Teacher'), findsOneWidget);
    expect(find.text('Student'), findsOneWidget);
  });
}
