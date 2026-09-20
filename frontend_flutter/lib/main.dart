import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'data/controllers.dart';
import 'data/repositories.dart';
import 'route_observer.dart';
import 'route_table.dart';
import 'routes.dart';
import 'theme/app_theme.dart';
import 'widgets/shared/responsive_shell.dart';

void main() => runApp(const RecallApp());

class RecallApp extends StatelessWidget {
  const RecallApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        // The repository interfaces are what the screens depend on; which
        // implementation sits behind them is decided here and nowhere else.
        Provider<AuthRepository>(create: (_) => MockAuthRepository()),
        Provider<QuizRepository>(
          create: (c) => MockQuizRepository(c.read<AuthRepository>()),
        ),
        Provider<SessionRepository>(create: (_) => MockSessionRepository()),
        Provider<AttemptRepository>(create: (_) => MockAttemptRepository()),
        Provider<ResultsRepository>(
          create: (c) => MockResultsRepository(c.read<AuthRepository>()),
        ),
        ChangeNotifierProvider<AuthController>(
          create: (c) => AuthController(c.read<AuthRepository>()),
        ),
      ],
      child: MaterialApp(
        title: 'Recall',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light,
        initialRoute: Routes.splash,
        onGenerateRoute: onGenerateRoute,
        navigatorObservers: [routeObserver],
        builder: (context, child) =>
            ResponsiveShell(child: child ?? const SizedBox.shrink()),
      ),
    );
  }
}
