import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:recall/main.dart';
import 'package:recall/theme/colors.dart';

void main() {
  testWidgets('Splash shows the lockup while the session restores',
      (tester) async {
    await tester.pumpWidget(const RecallApp());
    await tester.pump();

    expect(find.text('Recall'), findsOneWidget);
    expect(find.text('Restoring your session'), findsOneWidget);
  });

  testWidgets('An unrestored session lands on sign in', (tester) async {
    await tester.pumpWidget(const RecallApp());
    // The mock restore resolves after 900ms with no user.
    await tester.pump(const Duration(seconds: 2));
    await tester.pumpAndSettle();

    expect(find.text('Sign in'), findsWidgets);
    expect(find.text('Use your college email or roll number.'), findsOneWidget);
  });

  testWidgets('The ground colour is the warm off-white, not white',
      (tester) async {
    await tester.pumpWidget(const RecallApp());
    await tester.pump();

    final scaffold = tester.widget<Scaffold>(find.byType(Scaffold).first);
    expect(scaffold.backgroundColor, AppColors.ground);
  });
}
