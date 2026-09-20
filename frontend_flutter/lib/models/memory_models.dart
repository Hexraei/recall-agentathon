import 'package:flutter/foundation.dart';

/// Models for `GET /api/memory/*` (app/memory_api.py) — the persistent-memory
/// demo. These mirror the JSON fields exactly; see FLUTTER_CONTEXT.md for
/// what each one means and the three rules the API is built around:
/// it states what happened and never why, it is read-only, and every screen
/// that shows this data must also show [disclosureText].
///
/// The one word the UI keys off is [SittingOutcome] — deliberately three
/// values, all three real screens, none of them an error state.
enum SittingOutcome { first, found, noneFound, unknown }

SittingOutcome _outcomeFrom(String? s) => switch (s) {
  'first' => SittingOutcome.first,
  'found' => SittingOutcome.found,
  'none_found' => SittingOutcome.noneFound,
  _ => SittingOutcome.unknown,
};

/// One row of `GET /api/memory/students` — the identity list screen.
@immutable
class MemoryIdentitySummary {
  const MemoryIdentitySummary({
    required this.studentId,
    required this.name,
    required this.department,
    required this.sittings,
    required this.foundARepeat,
    required this.awaitingHuman,
  });

  final String studentId;
  final String? name;
  final String? department;
  final int sittings;
  final bool foundARepeat;
  final bool awaitingHuman;

  factory MemoryIdentitySummary.fromJson(Map<String, dynamic> j) =>
      MemoryIdentitySummary(
        studentId: j['student_id'] as String,
        name: j['name'] as String?,
        department: j['department'] as String?,
        sittings: (j['sittings'] as num?)?.toInt() ?? 0,
        foundARepeat: j['found_a_repeat'] as bool? ?? false,
        awaitingHuman: j['awaiting_human'] as bool? ?? false,
      );
}

/// The finding an agent produced on a sitting, when it produced one at all.
@immutable
class MemoryFinding {
  const MemoryFinding({
    this.status,
    this.statement,
    this.uncertainty,
    this.nextStep,
    this.cites = const [],
  });

  final String? status;
  final String? statement;
  final String? uncertainty;
  final String? nextStep;
  final List<String> cites;

  factory MemoryFinding.fromJson(Map<String, dynamic> j) => MemoryFinding(
    status: j['status'] as String?,
    statement: j['statement'] as String?,
    uncertainty: j['uncertainty'] as String?,
    nextStep: j['next_step'] as String?,
    cites: (j['cites'] as List?)?.cast<String>() ?? const [],
  );
}

/// One sitting, as returned inside `student/{id}` or on its own from
/// `sitting/{run_id}`.
@immutable
class Sitting {
  const Sitting({
    required this.sittingNumber,
    required this.runId,
    this.date,
    this.assignmentId,
    this.score,
    this.asked,
    required this.outcome,
    this.label,
    this.explanation,
    this.citedAnswers = const [],
    required this.priorSittingsVisible,
    this.finding,
    this.checked,
    required this.awaitingHuman,
    this.state,
    this.realAnswersFrom,
    this.realStudentId,
    this.synthenticTimeline = true,
  });

  final int? sittingNumber;
  final String runId;
  final String? date;
  final String? assignmentId;
  final int? score;
  final int? asked;

  /// Key the UI off this, not [label].
  final SittingOutcome outcome;

  /// The agent's own word: recurring, similar, not_enough_evidence, improving.
  final String? label;

  /// The agent's own sentences — render verbatim, never summarise.
  final String? explanation;
  final List<String> citedAnswers;

  /// How many earlier sittings this one could see. 0 on sitting 1.
  final int priorSittingsVisible;
  final MemoryFinding? finding;
  final String? checked;

  /// True = the agent stopped and handed the decision to a professor.
  final bool awaitingHuman;
  final String? state;
  final String? realAnswersFrom;
  final String? realStudentId;
  final bool synthenticTimeline;

  factory Sitting.fromJson(Map<String, dynamic> j) => Sitting(
    sittingNumber: (j['sitting'] as num?)?.toInt(),
    runId: j['run_id'] as String,
    date: j['date'] as String?,
    assignmentId: j['assignment_id'] as String?,
    score: (j['score'] as num?)?.toInt(),
    asked: (j['asked'] as num?)?.toInt(),
    outcome: _outcomeFrom(j['outcome'] as String?),
    label: j['label'] as String?,
    explanation: j['explanation'] as String?,
    citedAnswers: (j['cited_answers'] as List?)?.cast<String>() ?? const [],
    priorSittingsVisible: (j['prior_sittings_visible'] as num?)?.toInt() ?? 0,
    finding: j['finding'] == null
        ? null
        : MemoryFinding.fromJson(j['finding'] as Map<String, dynamic>),
    checked: j['checked'] as String?,
    awaitingHuman: j['awaiting_human'] as bool? ?? false,
    state: j['state'] as String?,
    realAnswersFrom: j['real_answers_from'] as String?,
    realStudentId: j['real_student_id'] as String?,
    synthenticTimeline: j['synthetic_timeline'] as bool? ?? true,
  );
}

/// One cited-or-not answer, part of a sitting's full detail
/// (`GET /api/memory/sitting/{run_id}`).
@immutable
class MemoryAnswer {
  const MemoryAnswer({
    this.ref,
    this.concept,
    this.kind,
    this.detail,
    required this.citedHere,
  });

  final String? ref;
  final String? concept;

  /// "strength" | "difficulty"
  final String? kind;
  final String? detail;

  /// True when the agent's claim on this sitting actually cites this answer.
  final bool citedHere;

  factory MemoryAnswer.fromJson(Map<String, dynamic> j) => MemoryAnswer(
    ref: j['ref'] as String?,
    concept: j['concept'] as String?,
    kind: j['kind'] as String?,
    detail: j['detail'] as String?,
    citedHere: j['cited_here'] as bool? ?? false,
  );
}

/// `summary` block on `GET /api/memory/student/{id}`.
@immutable
class MemorySummary {
  const MemorySummary({
    required this.totalSittings,
    required this.repeatsFound,
    required this.noRepeatClaimed,
    required this.awaitingHuman,
  });

  final int totalSittings;
  final int repeatsFound;
  final int noRepeatClaimed;
  final int awaitingHuman;

  factory MemorySummary.fromJson(Map<String, dynamic> j) => MemorySummary(
    totalSittings: (j['total_sittings'] as num?)?.toInt() ?? 0,
    repeatsFound: (j['repeats_found'] as num?)?.toInt() ?? 0,
    noRepeatClaimed: (j['no_repeat_claimed'] as num?)?.toInt() ?? 0,
    awaitingHuman: (j['awaiting_human'] as num?)?.toInt() ?? 0,
  );
}

/// `GET /api/memory/student/{id}` in full — the timeline screen.
@immutable
class MemoryIdentityDetail {
  const MemoryIdentityDetail({
    required this.studentId,
    this.name,
    this.department,
    required this.sittings,
    required this.summary,
    required this.disclosure,
  });

  final String studentId;
  final String? name;
  final String? department;

  /// Oldest first — render as a vertical timeline in this order.
  final List<Sitting> sittings;
  final MemorySummary summary;
  final String disclosure;

  factory MemoryIdentityDetail.fromJson(Map<String, dynamic> j) =>
      MemoryIdentityDetail(
        studentId: j['student_id'] as String,
        name: j['name'] as String?,
        department: j['department'] as String?,
        sittings: (j['sittings'] as List? ?? const [])
            .map((e) => Sitting.fromJson(e as Map<String, dynamic>))
            .toList(),
        summary: MemorySummary.fromJson(
          j['summary'] as Map<String, dynamic>? ?? const {},
        ),
        disclosure: j['disclosure'] as String? ?? '',
      );
}

/// `GET /api/memory/sitting/{run_id}` in full — the sitting detail screen.
@immutable
class SittingDetail {
  const SittingDetail({
    required this.sitting,
    required this.answers,
    this.prompt,
    required this.disclosure,
  });

  final Sitting sitting;
  final List<MemoryAnswer> answers;
  final String? prompt;
  final String disclosure;

  factory SittingDetail.fromJson(Map<String, dynamic> j) => SittingDetail(
    sitting: Sitting.fromJson(j),
    answers: (j['answers'] as List? ?? const [])
        .map((e) => MemoryAnswer.fromJson(e as Map<String, dynamic>))
        .toList(),
    prompt: j['prompt'] as String?,
    disclosure: j['disclosure'] as String? ?? '',
  );
}
