import 'models/models.dart';

/// The navigation map is a small fixed tree split by role, not a deep-linked
/// graph, so named routes over the built-in Navigator are enough.
class Routes {
  Routes._();

  static const splash = '/';
  static const auth = '/auth';

  // Teacher
  static const teacherHome = '/teacher';
  static const myQuizzes = '/teacher/quizzes';
  static const quizBuilder = '/teacher/builder';
  static const hostLobby = '/teacher/host';
  static const liveMonitor = '/teacher/monitor';
  static const quizResults = '/teacher/results';
  static const classAnalytics = '/teacher/analytics';
  static const classTopic = '/teacher/analytics/topic';
  static const reviewFindings = '/teacher/findings';
  static const studentAnalytics = '/teacher/student';
  static const studentAttempt = '/teacher/student/attempt';

  // Student
  static const studentHome = '/student';
  static const join = '/student/join';
  static const studentLobby = '/student/lobby';
  static const questionView = '/student/question';
  static const reviewSubmit = '/student/review';
  static const submitted = '/student/submitted';
  static const myResults = '/student/results';
  static const quizResult = '/student/result';
  static const myPerformance = '/student/performance';
}

/// Arguments for My Quizzes, which behaves differently when it was reached
/// from Host a quiz.
class MyQuizzesArgs {
  const MyQuizzesArgs({this.hosting = false});
  final bool hosting;
}

/// Arguments for a student attempt viewed by their teacher.
class StudentAttemptArgs {
  const StudentAttemptArgs({required this.studentId, required this.quizId});
  final String studentId;
  final String quizId;
}

/// Arguments for the student result screen.
class QuizResultArgs {
  const QuizResultArgs({
    required this.quizId,
    this.stillOpen = false,
    this.backLabel,
  });
  final String quizId;

  /// Where the back chevron says it goes. The result screen is reachable from
  /// the dashboard and from the list of results, and the label should name
  /// whichever one opened it.
  final String? backLabel;

  /// The quiz has not closed yet, so the screen shows what was submitted and
  /// says when the result lands, rather than an empty chart.
  final bool stillOpen;
}

/// Arguments for the submitted receipt.
class SubmittedArgs {
  const SubmittedArgs({
    required this.quiz,
    required this.answered,
    required this.submittedAt,
    this.auto = false,
  });

  final Quiz quiz;
  final int answered;
  final DateTime submittedAt;
  final bool auto;
}
