import 'package:flutter/foundation.dart';

/// Role comes from the account and is chosen once at sign-up.
enum UserRole { teacher, student }

@immutable
class AppUser {
  const AppUser({
    required this.id,
    required this.name,
    required this.role,
    this.rollNumber,
  });

  final String id;
  final String name;
  final UserRole role;

  /// Students carry a roll number; teachers do not.
  final String? rollNumber;

  /// "Nithya P" becomes "NP".
  String get initials {
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty) return '?';
    if (parts.length == 1) {
      final one = parts.first;
      return one.substring(0, one.length >= 2 ? 2 : 1).toUpperCase();
    }
    return (parts.first[0] + parts.last[0]).toUpperCase();
  }

  /// The greeting uses the first name alone.
  String get firstName => name.trim().split(RegExp(r'\s+')).first;
}

/// Every question is four options labelled A to D, exactly one correct.
///
/// [options] always holds exactly four entries and [correctIndex] is always
/// 0-3. That invariant is not expressed as a constructor assert because a
/// const assert cannot read a list's length, so it is enforced by the only
/// two things that build a Question: the quiz builder and the fixtures.
@immutable
class Question {
  const Question({
    required this.id,
    required this.text,
    required this.topic,
    required this.options,
    required this.correctIndex,
  });

  final String id;
  final String text;

  /// One topic per question. Topics are the unit every aggregate view
  /// groups by, so nothing may carry more than one.
  final String topic;
  final List<String> options;
  final int correctIndex;

  static const letters = ['A', 'B', 'C', 'D'];

  String get correctLetter => letters[correctIndex];
  String get correctOption => options[correctIndex];
}

@immutable
class Quiz {
  const Quiz({
    required this.id,
    required this.title,
    required this.questions,
    required this.timeLimitMinutes,
    this.week,
    this.lastRun,
    this.pin,
    this.closedAt,
  });

  final String id;

  /// A quiz is known by the name its teacher gave it.
  final String title;
  final List<Question> questions;

  /// One deadline covers the whole attempt.
  final int timeLimitMinutes;

  /// Any week marker lives in the meta line beside the date, never in the name.
  final String? week;
  final DateTime? lastRun;
  final String? pin;
  final DateTime? closedAt;

  int get questionCount => questions.length;
  bool get hasRun => lastRun != null;

  /// "15 questions · 20 min"
  String get summaryLine => '$questionCount questions · $timeLimitMinutes min';

  Duration get duration => Duration(minutes: timeLimitMinutes);

  List<String> get topics {
    final seen = <String>[];
    for (final q in questions) {
      if (!seen.contains(q.topic)) seen.add(q.topic);
    }
    return seen;
  }

  Quiz copyWith({
    String? title,
    List<Question>? questions,
    int? timeLimitMinutes,
    String? week,
    DateTime? lastRun,
    String? pin,
    DateTime? closedAt,
  }) => Quiz(
    id: id,
    title: title ?? this.title,
    questions: questions ?? this.questions,
    timeLimitMinutes: timeLimitMinutes ?? this.timeLimitMinutes,
    week: week ?? this.week,
    lastRun: lastRun ?? this.lastRun,
    pin: pin ?? this.pin,
    closedAt: closedAt ?? this.closedAt,
  );
}

/// Where one student has got to, as the Live Monitor states it in words.
enum AttemptStage { joined, answering, allAnswered, submitted }

@immutable
class StudentProgress {
  const StudentProgress({
    required this.student,
    required this.stage,
    required this.answered,
    required this.total,
    this.submittedAt,
    this.autoSubmitted = false,
  });

  final AppUser student;
  final AttemptStage stage;
  final int answered;
  final int total;
  final DateTime? submittedAt;
  final bool autoSubmitted;

  /// The monitor states progress in words, which a progress bar could not do.
  String get progressLine {
    switch (stage) {
      case AttemptStage.joined:
        return 'Joined, not started';
      case AttemptStage.answering:
        return 'Answered $answered of $total';
      case AttemptStage.allAnswered:
        return 'All $total answered, not submitted';
      case AttemptStage.submitted:
        final t = submittedAt;
        final stamp = t == null
            ? ''
            : ' at ${t.hour.toString().padLeft(2, '0')}:'
                  '${t.minute.toString().padLeft(2, '0')}';
        return autoSubmitted ? 'Submitted at the deadline' : 'Submitted$stamp';
    }
  }
}

/// A student's answers for one quiz. Answers stay editable until submission.
class Attempt {
  Attempt({
    required this.quizId,
    required this.studentId,
    Map<String, int>? answers,
    this.submittedAt,
    this.autoSubmitted = false,
  }) : answers = answers ?? {};

  final String quizId;
  final String studentId;

  /// question id -> chosen option index. A missing key is a blank answer.
  final Map<String, int> answers;
  DateTime? submittedAt;
  bool autoSubmitted;

  bool get isSubmitted => submittedAt != null;
  int get answeredCount => answers.length;
}

/// One question as it reads on a result screen.
@immutable
class QuestionResult {
  const QuestionResult({
    required this.question,
    required this.chosenIndex,
    required this.position,
  });

  final Question question;

  /// null when the question was left blank.
  final int? chosenIndex;
  final int position;

  bool get isCorrect => chosenIndex == question.correctIndex;
  bool get isBlank => chosenIndex == null;

  String? get chosenLetter =>
      chosenIndex == null ? null : Question.letters[chosenIndex!];
  String? get chosenOption =>
      chosenIndex == null ? null : question.options[chosenIndex!];
}

/// A correct-out-of-total figure for one topic.
@immutable
class TopicScore {
  const TopicScore({
    required this.topic,
    required this.correct,
    required this.total,
  });

  final String topic;
  final int correct;
  final int total;

  double get fraction => total == 0 ? 0 : correct / total;
  int get percent => (fraction * 100).round();
  String get label => '$correct of $total';
}

/// A student's whole result for one quiz.
@immutable
class QuizResultData {
  const QuizResultData({
    required this.quiz,
    required this.questionResults,
    required this.topicScores,
    required this.autoSubmitted,
    required this.submittedAt,
  });

  final Quiz quiz;
  final List<QuestionResult> questionResults;
  final List<TopicScore> topicScores;
  final bool autoSubmitted;
  final DateTime submittedAt;

  int get correct => questionResults.where((r) => r.isCorrect).length;
  int get total => questionResults.length;

  /// Blank answers currently count as wrong, matching the segment strip on
  /// the canvas. Nothing has decided whether they should drop out of the
  /// denominator instead.
  int get blanks => questionResults.where((r) => r.isBlank).length;
  int get percent => total == 0 ? 0 : (correct / total * 100).round();
}

/// How the class as a whole answered one question.
@immutable
class QuestionBreakdown {
  const QuestionBreakdown({
    required this.question,
    required this.shares,
    required this.respondents,
  });

  final Question question;

  /// The share who chose each option, in A-to-D order.
  final List<int> shares;
  final int respondents;

  int get correctShare => shares[question.correctIndex];
  int get correctPercent =>
      respondents == 0 ? 0 : (correctShare / respondents * 100).round();
}

/// A class-level gap: what a share of the class did, never what one student
/// is like. A gap is a candidate until the teacher accepts it.
enum FindingStatus { awaitingReview, accepted, rejected }

@immutable
class Finding {
  const Finding({
    required this.id,
    required this.topic,
    required this.statement,
    required this.quizTitle,
    required this.questionStem,
    required this.chosenCount,
    required this.classSize,
    required this.uncertainty,
    required this.nextStep,
    this.status = FindingStatus.awaitingReview,
    this.rejectionReason,
  });

  final String id;
  final String topic;

  /// "19 of 42 students chose an answer that assumes no two keys share a slot"
  final String statement;
  final String quizTitle;
  final String questionStem;
  final int chosenCount;
  final int classSize;
  final String uncertainty;
  final String nextStep;
  final FindingStatus status;
  final String? rejectionReason;

  Finding copyWith({FindingStatus? status, String? rejectionReason}) => Finding(
    id: id,
    topic: topic,
    statement: statement,
    quizTitle: quizTitle,
    questionStem: questionStem,
    chosenCount: chosenCount,
    classSize: classSize,
    uncertainty: uncertainty,
    nextStep: nextStep,
    status: status ?? this.status,
    rejectionReason: rejectionReason ?? this.rejectionReason,
  );
}

/// A class-wide result for one quiz, as Quiz Results reads it.
@immutable
class ClassQuizResult {
  const ClassQuizResult({
    required this.quiz,
    required this.tookIt,
    required this.classSize,
    required this.medianScore,
    required this.distribution,
    required this.topicScores,
    required this.breakdowns,
  });

  final Quiz quiz;
  final int tookIt;
  final int classSize;
  final int medianScore;

  /// Students in each score band, lowest band first.
  final List<int> distribution;
  final List<TopicScore> topicScores;
  final List<QuestionBreakdown> breakdowns;

  bool get fullParticipation => tookIt == classSize;
  int get neverOpened => classSize - tookIt;
  int get averagePercent => quiz.questionCount == 0
      ? 0
      : (medianScore / quiz.questionCount * 100).round();
}

/// One student's row in the A-to-Z roster: attendance, never a score.
@immutable
class RosterEntry {
  const RosterEntry({
    required this.student,
    required this.attended,
    required this.totalQuizzes,
  });

  final AppUser student;
  final int attended;
  final int totalQuizzes;

  String get attendanceLine => '$attended of $totalQuizzes quizzes';
}

/// A point on the class-average-per-quiz trend.
@immutable
class QuizAverage {
  const QuizAverage({
    required this.quizTitle,
    required this.shortLabel,
    required this.percent,
    this.absent = false,
  });

  final String quizTitle;
  final String shortLabel;
  final int percent;

  /// Used on a student's own trend for a quiz they did not take.
  final bool absent;
}

/// A topic aggregated across the quizzes in view.
@immutable
class TopicAggregate {
  const TopicAggregate({
    required this.topic,
    required this.percent,
    required this.questionCount,
    required this.gapsAwaitingReview,
    this.gaps = const [],
  });

  final String topic;
  final int percent;
  final int questionCount;
  final int gapsAwaitingReview;
  final List<Finding> gaps;
}

/// One past attempt in a student's history.
@immutable
class AttemptSummary {
  const AttemptSummary({
    required this.quiz,
    required this.correct,
    required this.total,
    required this.takenOn,
  });

  final Quiz quiz;
  final int correct;
  final int total;
  final DateTime takenOn;

  int get percent => total == 0 ? 0 : (correct / total * 100).round();
}
