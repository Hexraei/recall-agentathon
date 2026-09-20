import 'package:flutter/foundation.dart';

/// The response of `GET /api/report/{student_id}` (app/report_api.py), which
/// wraps the existing agent pipeline's own return dict — see
/// `report.for_student()` — unchanged, plus the student's identity and score
/// so the screen has everything the equivalent HTML page
/// (`webapp.py`'s `/report/{sid}`) shows.
///
/// Two fields carry the report's provenance, and the screen must show both
/// in plain language, same as the HTML page does:
///
///   [fromCache]   true = this is the report from when the student finished
///                 the quiz (a database read, no new model call). false =
///                 freshly generated just now.
///   [unverified]  true = the wording has not been double-checked yet. The
///                 numbers behind it are still accurate regardless.
@immutable
class StudentReport {
  const StudentReport({
    required this.studentId,
    this.name,
    this.department,
    this.registerNo,
    required this.score,
    required this.asked,
    this.headline,
    this.crossTopicPattern,
    this.strengths = const [],
    this.gaps = const [],
    this.nextStep,
    this.byTopic = const [],
    required this.fromCache,
    required this.unverified,
  });

  final String studentId;
  final String? name;
  final String? department;
  final String? registerNo;
  final int score;
  final int asked;

  final String? headline;
  final String? crossTopicPattern;
  final List<ReportConcept> strengths;
  final List<ReportConcept> gaps;
  final String? nextStep;
  final List<TopicLine> byTopic;

  /// A plain database read of an earlier run, not a new model call.
  final bool fromCache;

  /// The wording has not passed the checker yet — a fact about this report,
  /// not a verdict on the student.
  final bool unverified;

  factory StudentReport.fromJson(Map<String, dynamic> j) => StudentReport(
    studentId: j['student_id'] as String? ?? '',
    name: j['name'] as String?,
    department: j['department'] as String?,
    registerNo: j['register_no'] as String?,
    score: (j['score'] as num?)?.toInt() ?? 0,
    asked: (j['asked'] as num?)?.toInt() ?? 0,
    headline: j['headline'] as String?,
    crossTopicPattern: j['cross_topic_pattern'] as String?,
    strengths: (j['strengths'] as List? ?? const [])
        .map((e) => ReportConcept.fromJson(e as Map<String, dynamic>))
        .toList(),
    gaps: (j['gaps'] as List? ?? const [])
        .map((e) => ReportConcept.fromJson(e as Map<String, dynamic>))
        .toList(),
    nextStep: j['next_step'] as String?,
    byTopic: (j['by_topic'] as List? ?? const [])
        .map((e) => TopicLine.fromJson(e as Map<String, dynamic>))
        .toList(),
    fromCache: j['_from_cache'] as bool? ?? false,
    unverified: j['_unverified'] as bool? ?? false,
  );
}

/// One entry of `strengths` or `gaps` — a concept, the agent's verdict word,
/// and (sometimes) one supporting sentence.
@immutable
class ReportConcept {
  const ReportConcept({required this.concept, this.verdict, this.evidence});

  final String concept;
  final String? verdict;
  final String? evidence;

  factory ReportConcept.fromJson(Map<String, dynamic> j) => ReportConcept(
    concept: j['concept'] as String? ?? '',
    verdict: j['verdict'] as String?,
    evidence: j['evidence'] as String?,
  );
}

/// One row of the by-topic score table.
@immutable
class TopicLine {
  const TopicLine({
    required this.topic,
    required this.correct,
    required this.asked,
  });

  final String topic;
  final int correct;
  final int asked;

  factory TopicLine.fromJson(Map<String, dynamic> j) => TopicLine(
    topic: j['topic'] as String? ?? '',
    correct: (j['correct'] as num?)?.toInt() ?? 0,
    asked: (j['asked'] as num?)?.toInt() ?? 0,
  );
}
