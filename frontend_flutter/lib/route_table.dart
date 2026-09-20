import 'package:flutter/material.dart';

import 'data/controllers.dart';
import 'models/models.dart';
import 'routes.dart';
import 'screens/shared/auth_screen.dart';
import 'screens/shared/splash_screen.dart';
import 'screens/student/join_screen.dart';
import 'screens/student/my_performance_screen.dart';
import 'screens/student/question_view_screen.dart';
import 'screens/student/quiz_result_screen.dart';
import 'screens/student/review_submit_screen.dart';
import 'screens/student/student_home_screen.dart';
import 'screens/student/student_lobby_screen.dart';
import 'screens/student/submitted_screen.dart';
import 'screens/teacher/class_analytics_screen.dart';
import 'screens/teacher/host_lobby_screen.dart';
import 'screens/teacher/live_monitor_screen.dart';
import 'screens/teacher/my_quizzes_screen.dart';
import 'screens/teacher/quiz_builder_screen.dart';
import 'screens/teacher/quiz_results_screen.dart';
import 'screens/teacher/review_findings_screen.dart';
import 'screens/teacher/student_analytics_screen.dart';
import 'screens/teacher/teacher_home_screen.dart';
import 'screens/teacher/topic_page_screen.dart';

/// The one place that knows every screen.
///
/// It is kept apart from `routes.dart` — which holds only the route names and
/// the argument types — so that a screen can refer to a route without the
/// route table having to exist yet.
Route<dynamic>? onGenerateRoute(RouteSettings settings) {
  final a = settings.arguments;

  Widget page() {
    switch (settings.name) {
      case Routes.splash:
        return const SplashScreen();
      case Routes.auth:
        return const AuthScreen();

      // ------------------------------------------------------------ teacher
      case Routes.teacherHome:
        return const TeacherHomeScreen();
      case Routes.myQuizzes:
        return MyQuizzesScreen(
          hosting: (a as MyQuizzesArgs?)?.hosting ?? false,
        );
      case Routes.quizBuilder:
        return QuizBuilderScreen(quiz: a as Quiz?);
      case Routes.hostLobby:
        return HostLobbyScreen(quiz: a as Quiz);
      case Routes.liveMonitor:
        return LiveMonitorScreen(controller: a as HostSessionController);
      case Routes.quizResults:
        return QuizResultsScreen(quizId: a as String);
      case Routes.classAnalytics:
        return const ClassAnalyticsScreen();
      case Routes.classTopic:
        return ClassTopicScreen(topic: a as String);
      case Routes.reviewFindings:
        return const ReviewFindingsScreen();
      case Routes.studentAnalytics:
        return StudentAnalyticsScreen(studentId: a as String);
      case Routes.studentAttempt:
        final args = a as StudentAttemptArgs;
        return StudentAttemptScreen(
          studentId: args.studentId,
          quizId: args.quizId,
        );

      // ------------------------------------------------------------ student
      case Routes.studentHome:
        return const StudentHomeScreen();
      case Routes.join:
        return JoinScreen(prefilledPin: a as String?);
      case Routes.studentLobby:
        return StudentLobbyScreen(quiz: a as Quiz);
      case Routes.questionView:
        return QuestionViewScreen(controller: a as AttemptController);
      case Routes.reviewSubmit:
        return ReviewSubmitScreen(controller: a as AttemptController);
      case Routes.submitted:
        return SubmittedScreen(args: a as SubmittedArgs);
      case Routes.quizResult:
        return StudentQuizResultScreen(args: a as QuizResultArgs);
      case Routes.myPerformance:
        return const MyPerformanceScreen();

      default:
        return const SplashScreen();
    }
  }

  return MaterialPageRoute<dynamic>(builder: (_) => page(), settings: settings);
}
