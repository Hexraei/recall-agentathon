import 'dart:convert';
import 'dart:math';

import 'package:http/http.dart' as http;

import '../models/memory_models.dart';
import '../models/models.dart';
import '../models/student_report_models.dart';
import 'api_config.dart';
import 'fixtures.dart';

/// The boundary between the UI and wherever data actually comes from.
///
/// Everything below is in-memory: no backend is wired yet. Swapping in real
/// API calls later means writing new implementations of these interfaces,
/// not touching a single screen.

abstract class AuthRepository {
  Future<AppUser> signIn({
    required String identifier,
    required String password,
  });
  Future<AppUser> signUp({
    required String name,
    required String identifier,
    required String password,
    required UserRole role,
  });

  /// Restores a session on launch, or null when there is none.
  Future<AppUser?> restoreSession();
  Future<void> signOut();

  /// Whoever is signed in right now, or null. The other repositories read
  /// this so that "my quizzes" and "my results" mean the signed-in account
  /// and not a fixed fixture.
  AppUser? get currentUser;
}

abstract class QuizRepository {
  Future<List<Quiz>> myQuizzes();
  Future<Quiz> quizById(String id);
  Future<void> saveQuiz(Quiz quiz);
  Future<void> deleteQuiz(String id);
  Future<List<String>> knownTopics();
}

abstract class SessionRepository {
  /// Opens a host lobby and returns the PIN students will type.
  Future<String> host(Quiz quiz);

  /// Students appearing as they join.
  Stream<List<AppUser>> joinedStudents();

  Future<void> start();

  /// Per-student progress while the quiz runs.
  Stream<List<StudentProgress>> progress();

  Future<void> endQuiz();
}

/// What a PIN turned out to be.
enum JoinOutcome { ok, notFound, closed, alreadySubmitted, alreadyStarted }

class JoinResult {
  const JoinResult(this.outcome, {this.quiz, this.remaining});

  final JoinOutcome outcome;
  final Quiz? quiz;

  /// Set on [JoinOutcome.alreadyStarted]: the time left of the full duration.
  final Duration? remaining;
}

/// A quiz the backend says is open for this student's class right now.
///
/// It carries the PIN so the open-quiz banner can hand it to the join flow
/// rather than making the student read it off the board a second time.
class OpenQuiz {
  const OpenQuiz({required this.quiz, required this.pin});

  final Quiz quiz;
  final String pin;
}

abstract class AttemptRepository {
  /// The quiz open right now, or null when nothing is running.
  ///
  /// This is the one place that decides a quiz is open. The dashboard banner
  /// used to assert it on its own, which let it advertise a quiz that had
  /// already closed.
  Future<OpenQuiz?> openQuiz();

  Future<JoinResult> join(String pin);

  /// The lobby waits until the teacher starts.
  Stream<int> othersWaiting();
  Future<void> submit(Attempt attempt, {bool auto = false});
}

abstract class ResultsRepository {
  Future<ClassQuizResult> classResult(String quizId);
  Future<List<QuizAverage>> classAverages();
  Future<List<TopicAggregate>> topicAggregates();
  Future<List<RosterEntry>> roster();
  Future<List<Finding>> findings();
  Future<void> decideFinding(String id, FindingStatus status, {String? reason});

  Future<QuizResultData?> myResult(String quizId);

  /// Whether a quiz's window has shut. Until it has, no result is released.
  bool isClosed(String quizId);

  Future<List<AttemptSummary>> myAttempts();
  Future<List<QuizAverage>> myAverages();
  Future<List<TopicScore>> myTopicScores();

  Future<List<QuizAverage>> studentAverages(String studentId);
  Future<List<TopicScore>> studentTopicScores(
    String studentId, {
    bool recent = true,
  });
  Future<List<AttemptSummary>> studentAttempts(String studentId);
  Future<QuizResultData> studentAttemptDetail(String studentId, String quizId);
}

/// The persistent-memory demo (`GET /api/memory/*`, app/memory_api.py).
///
/// Read-only, backed by the real `memory.db` the demo tooling built — there
/// is no mock implementation of this one, because the whole point is that a
/// person in the room is looking at real recorded agent output, not a
/// plausible stand-in for it.
abstract class MemoryRepository {
  /// The identity list screen.
  Future<List<MemoryIdentitySummary>> students();

  /// One identity's full timeline, oldest sitting first.
  Future<MemoryIdentityDetail> student(String studentId);

  /// One sitting in full, including which cited answers back the claim.
  Future<SittingDetail> sitting(String runId);
}

/// Thrown by [MemoryRepository] when `memory.db` has not been built yet
/// (the API's own 503) — kept distinct from a plain network failure so the
/// screen can say something more useful than "could not load".
class MemoryNotBuiltException implements Exception {
  const MemoryNotBuiltException(this.message);
  final String message;
  @override
  String toString() => message;
}

/// The individual student report (`GET /api/report/{id}`, app/report_api.py)
/// — the JSON wrapper around the same agent pipeline
/// (`report.for_student()`) the web app's `/report/{sid}` page renders.
abstract class StudentReportRepository {
  /// `force: true` asks the server to regenerate rather than serve the
  /// cached report — the same escape hatch the web page's "Regenerate it"
  /// link uses.
  Future<StudentReport> report(String studentId, {bool force = false});
}

/// Thrown when the report could not be generated because the model that
/// writes it is unreachable — the API's own 503. Distinct from a 404 (no
/// such student, or they have not answered anything yet).
class ReportUnavailableException implements Exception {
  const ReportUnavailableException(this.message);
  final String message;
  @override
  String toString() => message;
}

/// No such student, or they have not answered anything yet.
class ReportNotFoundException implements Exception {
  const ReportNotFoundException(this.message);
  final String message;
  @override
  String toString() => message;
}

// ---------------------------------------------------------------- mock impls

/// A short pause, so loading states are real rather than theoretical.
Future<T> _latency<T>(T value, [int ms = 420]) =>
    Future.delayed(Duration(milliseconds: ms), () => value);

class MockAuthRepository implements AuthRepository {
  AppUser? _current;

  @override
  Future<AppUser> signIn({
    required String identifier,
    required String password,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 700));
    if (password.length < 4) {
      throw const AuthException('Those details did not match an account.');
    }
    // The identifier decides which role signs in, so both paths are reachable
    // in a build with no backend behind it.
    final isStudent = identifier.toLowerCase().startsWith('s');
    _current = isStudent ? Fixtures.student : Fixtures.teacher;
    return _current!;
  }

  @override
  Future<AppUser> signUp({
    required String name,
    required String identifier,
    required String password,
    required UserRole role,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 700));
    _current = AppUser(
      id: 'new',
      name: name.isEmpty ? 'New user' : name,
      role: role,
      rollNumber: role == UserRole.student ? identifier : null,
    );
    return _current!;
  }

  @override
  Future<AppUser?> restoreSession() => _latency(_current, 900);

  @override
  Future<void> signOut() async => _current = null;

  @override
  AppUser? get currentUser => _current;
}

class AuthException implements Exception {
  const AuthException(this.message);
  final String message;
  @override
  String toString() => message;
}

class MockQuizRepository implements QuizRepository {
  MockQuizRepository(this._auth);

  final AuthRepository _auth;

  /// The demo teacher's library, already full of term's work.
  final List<Quiz> _quizzes = [...Fixtures.allQuizzes];

  /// Anyone who signs up gets their own, which starts empty, so a new
  /// account opens on the invitation rather than on somebody else's term.
  final List<Quiz> _ownQuizzes = [];

  List<Quiz> get _library =>
      _auth.currentUser?.id == Fixtures.teacher.id ? _quizzes : _ownQuizzes;

  @override
  Future<List<Quiz>> myQuizzes() => _latency(List.unmodifiable(_library));

  @override
  Future<Quiz> quizById(String id) => _latency(
    [..._library, ...Fixtures.allQuizzes].firstWhere((q) => q.id == id),
  );

  @override
  Future<void> saveQuiz(Quiz quiz) async {
    await Future<void>.delayed(const Duration(milliseconds: 600));
    final library = _library;
    final i = library.indexWhere((q) => q.id == quiz.id);
    if (i == -1) {
      library.insert(0, quiz);
    } else {
      library[i] = quiz;
    }
  }

  @override
  Future<void> deleteQuiz(String id) async {
    await Future<void>.delayed(const Duration(milliseconds: 400));
    _library.removeWhere((q) => q.id == id);
  }

  @override
  Future<List<String>> knownTopics() async {
    final fromQuizzes = <String>{
      for (final q in _quizzes) ...q.topics,
      ...Fixtures.knownTopics,
    }.toList()..sort();
    return fromQuizzes;
  }
}

class MockSessionRepository implements SessionRepository {
  Quiz? _quiz;
  final _joined = <AppUser>[];
  bool _started = false;

  @override
  Future<String> host(Quiz quiz) async {
    _quiz = quiz;
    _joined.clear();
    _started = false;
    await Future<void>.delayed(const Duration(milliseconds: 300));
    return quiz.pin ?? '408 217';
  }

  @override
  Stream<List<AppUser>> joinedStudents() {
    // Students arrive a second or so apart, so the lobby is a live list
    // rather than a static snapshot. Stream.periodic is used rather than an
    // async* loop because cancelling it cancels the underlying timer, which
    // an in-flight Future.delayed would not.
    return Stream<void>.periodic(
      const Duration(milliseconds: 1100),
    ).take(Fixtures.roster.length).map((_) {
      if (!_started && _joined.length < Fixtures.roster.length) {
        _joined.add(Fixtures.roster[_joined.length]);
      }
      return List<AppUser>.unmodifiable(_joined);
    });
  }

  @override
  Future<void> start() async {
    await Future<void>.delayed(const Duration(milliseconds: 800));
    _started = true;
  }

  @override
  Stream<List<StudentProgress>> progress() {
    final total = _quiz?.questionCount ?? 15;
    final students = List<AppUser>.from(
      _joined.isEmpty ? Fixtures.roster : _joined,
    );
    final rnd = Random(7);
    final answered = [for (final _ in students) rnd.nextInt(total ~/ 2)];

    List<StudentProgress> tick() {
      final rows = <StudentProgress>[];
      for (var i = 0; i < students.length; i++) {
        if (answered[i] < total && rnd.nextDouble() < 0.45) answered[i]++;
        final a = answered[i];
        final stage = a >= total
            ? (i.isEven ? AttemptStage.submitted : AttemptStage.allAnswered)
            : AttemptStage.answering;
        rows.add(
          StudentProgress(
            student: students[i],
            stage: stage,
            answered: a,
            total: total,
            submittedAt: stage == AttemptStage.submitted
                ? DateTime.now()
                : null,
          ),
        );
      }
      return rows;
    }

    // The first frame is immediate so the monitor is never briefly empty;
    // the rest tick on a cancellable periodic timer.
    return Stream<List<StudentProgress>>.multi((controller) {
      controller.add(tick());
      final sub = Stream<void>.periodic(
        const Duration(milliseconds: 1500),
      ).listen((_) => controller.add(tick()));
      controller.onCancel = sub.cancel;
    });
  }

  @override
  Future<void> endQuiz() async =>
      Future<void>.delayed(const Duration(milliseconds: 600));
}

/// One quiz running right now, behind the PIN students type for it.
class _LiveSession {
  const _LiveSession({
    required this.quiz,
    required this.pin,
    required this.started,
  });

  final Quiz quiz;
  final String pin;

  /// Already under way, so joining it is a late entry straight into the
  /// questions rather than a wait in the lobby.
  final bool started;
}

class MockAttemptRepository implements AttemptRepository {
  /// The quizzes actually running, each behind its own PIN. They lead
  /// somewhere different on purpose: one opens a lobby, the other is already
  /// under way.
  static final _live = <String, _LiveSession>{
    '408217': _LiveSession(
      quiz: Fixtures.hashTables,
      pin: '408 217',
      started: false,
    ),
    '333333': _LiveSession(quiz: Fixtures.trees, pin: '333 333', started: true),
  };

  /// PINs that resolve to something other than a live quiz.
  static const _settled = {
    '111111': JoinOutcome.closed,
    '222222': JoinOutcome.alreadySubmitted,
  };

  /// Quiz ids this student has submitted during this run.
  final _submitted = <String>{};

  /// The last live quiz this student actually found by typing its PIN.
  ///
  /// The banner follows it, so backing out of one quiz and returning to the
  /// dashboard offers that quiz again rather than resetting to whichever
  /// session happens to be listed first.
  String? _lastSeenPin;

  Iterable<_LiveSession> get _available =>
      _live.values.where((s) => !_submitted.contains(s.quiz.id));

  @override
  Future<OpenQuiz?> openQuiz() async {
    await Future<void>.delayed(const Duration(milliseconds: 200));

    final seen = _lastSeenPin == null ? null : _live[_lastSeenPin];
    if (seen != null && !_submitted.contains(seen.quiz.id)) {
      return OpenQuiz(quiz: seen.quiz, pin: seen.pin);
    }

    // Nothing found by PIN yet, or that one has been handed in: fall back to
    // any session still running.
    if (_available.isEmpty) return null;
    final first = _available.first;
    return OpenQuiz(quiz: first.quiz, pin: first.pin);
  }

  @override
  Future<JoinResult> join(String pin) async {
    await Future<void>.delayed(const Duration(milliseconds: 900));
    final digits = pin.replaceAll(' ', '');

    final session = _live[digits];
    if (session != null) {
      if (_submitted.contains(session.quiz.id)) {
        return JoinResult(JoinOutcome.alreadySubmitted, quiz: session.quiz);
      }
      // Remember it even if they back out without joining.
      _lastSeenPin = digits;
      return JoinResult(
        session.started ? JoinOutcome.alreadyStarted : JoinOutcome.ok,
        quiz: session.quiz,
        remaining: session.started
            ? session.quiz.duration - const Duration(minutes: 6)
            : null,
      );
    }

    final settled = _settled[digits];
    if (settled != null) {
      return JoinResult(settled, quiz: Fixtures.hashTables);
    }
    return const JoinResult(JoinOutcome.notFound);
  }

  @override
  Stream<int> othersWaiting() {
    var n = 6;
    return Stream<int>.multi((controller) {
      controller.add(n);
      final sub = Stream<void>.periodic(const Duration(milliseconds: 1800))
          .listen((_) {
            n = min(n + 1, Fixtures.classSize - 1);
            controller.add(n);
          });
      controller.onCancel = sub.cancel;
    });
  }

  @override
  Future<void> submit(Attempt attempt, {bool auto = false}) async {
    await Future<void>.delayed(const Duration(milliseconds: 900));
    attempt.submittedAt = DateTime.now();
    attempt.autoSubmitted = auto;

    // Recording it is what stops the banner offering the quiz again.
    _submitted.add(attempt.quizId);
    if (_lastSeenPin != null &&
        _live[_lastSeenPin]?.quiz.id == attempt.quizId) {
      _lastSeenPin = null;
    }
  }
}

class MockResultsRepository implements ResultsRepository {
  MockResultsRepository(this._auth);

  final AuthRepository _auth;

  /// "My" means the signed-in account. An account created in this build has
  /// sat no quiz, so it has no history — it must not be handed the demo
  /// student's.
  String get _meId => _auth.currentUser?.id ?? Fixtures.student.id;

  /// Only the roster has a past. Everyone else starts empty.
  bool _hasHistory(String studentId) =>
      Fixtures.roster.any((s) => s.id == studentId);

  /// Results exist only after the window closes for everyone, so every
  /// student-facing history is built from closed quizzes alone. A quiz that
  /// is still open has no result to show yet, not even to whoever has
  /// already handed theirs in.
  List<Quiz> get _closed =>
      Fixtures.allQuizzes.where((q) => q.closedAt != null).toList();

  final _findings = <Finding>[
    const Finding(
      id: 'f1',
      topic: 'Collisions',
      statement:
          '19 of 42 students chose an answer that assumes no two keys share a slot',
      quizTitle: 'Hash tables',
      questionStem:
          'Two distinct keys hash to the same slot. What has happened?',
      chosenCount: 19,
      classSize: 42,
      uncertainty:
          'The same distractor also reads as correct if the question is taken '
          'to be about a perfect hash, which the stem does not rule out.',
      nextStep:
          'Work through a table where two keys collide, and show what separate '
          'chaining stores in that slot.',
    ),
    const Finding(
      id: 'f2',
      topic: 'Shortest paths',
      statement:
          '16 of 42 students chose Bellman-Ford where weights were stated to be '
          'non-negative',
      quizTitle: 'Graphs',
      questionStem:
          'Which algorithm finds shortest paths with non-negative weights?',
      chosenCount: 16,
      classSize: 42,
      uncertainty:
          'Bellman-Ford is not wrong, only slower, so some of these may be '
          'reading the question as "which would work" rather than "which is used".',
      nextStep:
          'Put the two algorithms side by side on the same graph and compare '
          'what each one assumes about the weights.',
    ),
    const Finding(
      id: 'f3',
      topic: 'Call stack',
      statement:
          '14 of 42 students chose the outermost frame as the first to return',
      quizTitle: 'Recursion',
      questionStem:
          'Tracing a recursive call stack, which frame returns first?',
      chosenCount: 14,
      classSize: 42,
      uncertainty:
          'This may be a reading of "first" as "first called" rather than '
          '"first to return".',
      nextStep:
          'Trace a three-deep call on the board, marking the order frames are '
          'pushed and the order they pop.',
    ),
  ];

  @override
  Future<ClassQuizResult> classResult(String quizId) async {
    final quiz = Fixtures.allQuizzes.firstWhere((q) => q.id == quizId);
    // The distribution and the median are derived from one another so the
    // two tiles cannot disagree, which they did on the canvas.
    const dist = [1, 4, 11, 17, 9];
    final topics = _topicScoresFor(quiz);
    return _latency(
      ClassQuizResult(
        quiz: quiz,
        tookIt: quizId == 'q-recursion' ? 38 : 42,
        classSize: Fixtures.classSize,
        medianScore: 11,
        distribution: dist,
        topicScores: topics,
        breakdowns: _breakdownsFor(quiz),
      ),
    );
  }

  List<TopicScore> _topicScoresFor(Quiz quiz) {
    final rnd = Random(quiz.id.hashCode);
    final scores = <TopicScore>[];
    for (final t in quiz.topics) {
      final total = quiz.questions.where((q) => q.topic == t).length;
      final correct = (total * (0.42 + rnd.nextDouble() * 0.45)).round();
      scores.add(TopicScore(topic: t, correct: correct, total: total));
    }
    scores.sort((a, b) => a.fraction.compareTo(b.fraction));
    return scores;
  }

  List<QuestionBreakdown> _breakdownsFor(Quiz quiz) {
    final rnd = Random(quiz.id.hashCode + 1);
    final out = <QuestionBreakdown>[];
    for (final q in quiz.questions) {
      const respondents = 42;
      final correctShare = 8 + rnd.nextInt(26);
      var left = respondents - correctShare;
      final shares = List<int>.filled(4, 0);
      shares[q.correctIndex] = correctShare;
      for (var i = 0; i < 4; i++) {
        if (i == q.correctIndex) continue;
        final take = left > 0 ? rnd.nextInt(left + 1) : 0;
        shares[i] = take;
        left -= take;
      }
      if (left > 0) {
        final spill = (q.correctIndex + 1) % 4;
        shares[spill] += left;
      }
      out.add(
        QuestionBreakdown(
          question: q,
          shares: shares,
          respondents: respondents,
        ),
      );
    }
    out.sort((a, b) => a.correctPercent.compareTo(b.correctPercent));
    return out;
  }

  @override
  Future<List<QuizAverage>> classAverages() => _latency(const [
    QuizAverage(quizTitle: 'Arrays', shortLabel: 'W4', percent: 71),
    QuizAverage(quizTitle: 'Linked lists', shortLabel: 'W5', percent: 66),
    QuizAverage(quizTitle: 'Recursion', shortLabel: 'W6', percent: 58),
    QuizAverage(quizTitle: 'Trees', shortLabel: 'W7', percent: 69),
    QuizAverage(quizTitle: 'Hash tables', shortLabel: 'W8', percent: 62),
    QuizAverage(quizTitle: 'Graphs', shortLabel: 'W9', percent: 67),
  ]);

  @override
  Future<List<TopicAggregate>> topicAggregates() async {
    final byTopic = <String, List<Finding>>{};
    for (final f in _findings) {
      byTopic.putIfAbsent(f.topic, () => []).add(f);
    }
    final aggregates = [
      TopicAggregate(
        topic: 'Collisions',
        percent: 44,
        questionCount: 7,
        gaps: byTopic['Collisions'] ?? const [],
        gapsAwaitingReview: _awaiting(byTopic['Collisions']),
      ),
      TopicAggregate(
        topic: 'Shortest paths',
        percent: 51,
        questionCount: 5,
        gaps: byTopic['Shortest paths'] ?? const [],
        gapsAwaitingReview: _awaiting(byTopic['Shortest paths']),
      ),
      TopicAggregate(
        topic: 'Call stack',
        percent: 56,
        questionCount: 4,
        gaps: byTopic['Call stack'] ?? const [],
        gapsAwaitingReview: _awaiting(byTopic['Call stack']),
      ),
      const TopicAggregate(
        topic: 'Recurrence',
        percent: 61,
        questionCount: 3,
        gapsAwaitingReview: 0,
      ),
      const TopicAggregate(
        topic: 'Load factor',
        percent: 64,
        questionCount: 4,
        gapsAwaitingReview: 0,
      ),
      const TopicAggregate(
        topic: 'Traversal',
        percent: 72,
        questionCount: 5,
        gapsAwaitingReview: 0,
      ),
      const TopicAggregate(
        topic: 'Representation',
        percent: 74,
        questionCount: 5,
        gapsAwaitingReview: 0,
      ),
      const TopicAggregate(
        topic: 'Hashing',
        percent: 78,
        questionCount: 4,
        gapsAwaitingReview: 0,
      ),
      const TopicAggregate(
        topic: 'Base cases',
        percent: 81,
        questionCount: 3,
        gapsAwaitingReview: 0,
      ),
      const TopicAggregate(
        topic: 'Complexity',
        percent: 83,
        questionCount: 2,
        gapsAwaitingReview: 0,
      ),
    ];
    return _latency(aggregates);
  }

  int _awaiting(List<Finding>? fs) => (fs ?? const [])
      .where((f) => f.status == FindingStatus.awaitingReview)
      .length;

  @override
  Future<List<RosterEntry>> roster() async {
    final rnd = Random(3);
    final entries = [
      for (final s in Fixtures.roster)
        RosterEntry(student: s, attended: 4 + rnd.nextInt(3), totalQuizzes: 6),
    ]..sort((a, b) => a.student.name.compareTo(b.student.name));
    return _latency(entries);
  }

  @override
  Future<List<Finding>> findings() => _latency(List.unmodifiable(_findings));

  @override
  Future<void> decideFinding(
    String id,
    FindingStatus status, {
    String? reason,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 700));
    final i = _findings.indexWhere((f) => f.id == id);
    if (i != -1) {
      _findings[i] = _findings[i].copyWith(
        status: status,
        rejectionReason: reason,
      );
    }
  }

  // ------------------------------------------------------------- student side

  /// A fixed answer key per quiz, so a student's result, their topic
  /// breakdown and their history all agree with one another.
  Map<String, int?> _answersFor(Quiz quiz, String studentId) {
    final rnd = Random(quiz.id.hashCode ^ studentId.hashCode);
    final out = <String, int?>{};
    for (final q in quiz.questions) {
      final roll = rnd.nextDouble();
      if (roll < 0.06) {
        out[q.id] = null; // left blank
      } else if (roll < 0.73) {
        out[q.id] = q.correctIndex;
      } else {
        var wrong = rnd.nextInt(4);
        if (wrong == q.correctIndex) wrong = (wrong + 1) % 4;
        out[q.id] = wrong;
      }
    }
    return out;
  }

  QuizResultData _resultFor(Quiz quiz, String studentId) {
    final answers = _answersFor(quiz, studentId);
    final results = <QuestionResult>[
      for (var i = 0; i < quiz.questions.length; i++)
        QuestionResult(
          question: quiz.questions[i],
          chosenIndex: answers[quiz.questions[i].id],
          position: i + 1,
        ),
    ];
    final topics = <String, List<QuestionResult>>{};
    for (final r in results) {
      topics.putIfAbsent(r.question.topic, () => []).add(r);
    }
    final topicScores = [
      for (final e in topics.entries)
        TopicScore(
          topic: e.key,
          correct: e.value.where((r) => r.isCorrect).length,
          total: e.value.length,
        ),
    ]..sort((a, b) => a.fraction.compareTo(b.fraction));

    final blanks = results.where((r) => r.isBlank).length;
    return QuizResultData(
      quiz: quiz,
      questionResults: results,
      topicScores: topicScores,
      autoSubmitted: blanks > 1,
      submittedAt: quiz.closedAt ?? DateTime.now(),
    );
  }

  @override
  Future<QuizResultData?> myResult(String quizId) async {
    if (!_hasHistory(_meId)) return _latency(null);
    final quiz = Fixtures.allQuizzes.firstWhere((q) => q.id == quizId);
    return _latency(_resultFor(quiz, _meId));
  }

  @override
  bool isClosed(String quizId) {
    final quiz = Fixtures.allQuizzes.firstWhere((q) => q.id == quizId);
    return quiz.closedAt != null;
  }

  @override
  Future<List<AttemptSummary>> myAttempts() => studentAttempts(_meId);

  @override
  Future<List<QuizAverage>> myAverages() => studentAverages(_meId);

  @override
  Future<List<TopicScore>> myTopicScores() => studentTopicScores(_meId);

  /// Two students in the mock are deliberately sparse, so the states that
  /// need a gap in someone's history are reachable rather than theoretical:
  /// the signed-in student misses Recursion, which is what puts a dash on
  /// their own performance chart, and Priya Venkat misses everything but
  /// Graphs, which is what makes "one attempt only" reachable from the
  /// teacher's side without depending on chance across the whole roster.
  bool _missed(String studentId, String quizId) {
    if (studentId == Fixtures.student.id) return quizId == 'q-recursion';
    if (studentId == 's10') return quizId != Fixtures.graphs.id;
    return false;
  }

  @override
  Future<List<QuizAverage>> studentAverages(String studentId) async {
    if (!_hasHistory(studentId)) return _latency(const <QuizAverage>[]);
    final out = <QuizAverage>[];
    for (final q in _closed.reversed) {
      final absent = _missed(studentId, q.id);
      out.add(
        QuizAverage(
          quizTitle: q.title,
          shortLabel: q.week?.replaceAll('Week ', 'W') ?? q.title,
          percent: absent ? 0 : _resultFor(q, studentId).percent,
          absent: absent,
        ),
      );
    }
    return _latency(out);
  }

  @override
  Future<List<TopicScore>> studentTopicScores(
    String studentId, {
    bool recent = true,
  }) async {
    if (!_hasHistory(studentId)) return _latency(const <TopicScore>[]);
    final merged = <String, List<int>>{};
    for (final q in _closed) {
      if (_missed(studentId, q.id)) continue;
      for (final t in _resultFor(q, studentId).topicScores) {
        final m = merged.putIfAbsent(t.topic, () => [0, 0]);
        m[0] += t.correct;
        m[1] += t.total;
      }
    }
    final out = [
      for (final e in merged.entries)
        TopicScore(topic: e.key, correct: e.value[0], total: e.value[1]),
    ]..sort((a, b) => a.fraction.compareTo(b.fraction));
    return _latency(out);
  }

  @override
  Future<List<AttemptSummary>> studentAttempts(String studentId) async {
    if (!_hasHistory(studentId)) return _latency(const <AttemptSummary>[]);
    final out = <AttemptSummary>[];
    for (final q in _closed) {
      if (_missed(studentId, q.id)) continue;
      final r = _resultFor(q, studentId);
      out.add(
        AttemptSummary(
          quiz: q,
          correct: r.correct,
          total: r.total,
          takenOn: q.lastRun ?? DateTime.now(),
        ),
      );
    }
    out.sort((a, b) => b.takenOn.compareTo(a.takenOn));
    return _latency(out);
  }

  @override
  Future<QuizResultData> studentAttemptDetail(
    String studentId,
    String quizId,
  ) async {
    final quiz = Fixtures.allQuizzes.firstWhere((q) => q.id == quizId);
    return _latency(_resultFor(quiz, studentId));
  }
}

// ----------------------------------------------------------------- HTTP impls

/// Real implementation of [MemoryRepository], calling the FastAPI process
/// (`webapp.py`) started separately — see [ApiConfig.baseUrl].
///
/// Responses are cached in memory for the lifetime of this object: the data
/// is static between demo rebuilds (see FLUTTER_CONTEXT.md's "Practical
/// notes"), and a live demo should not depend on the network being good in
/// the room for a second look at the same identity.
class HttpMemoryRepository implements MemoryRepository {
  HttpMemoryRepository({http.Client? client})
    : _client = client ?? http.Client();

  final http.Client _client;
  List<MemoryIdentitySummary>? _studentsCache;
  final _detailCache = <String, MemoryIdentityDetail>{};
  final _sittingCache = <String, SittingDetail>{};

  Uri _uri(String path) => Uri.parse('${ApiConfig.baseUrl}$path');

  Future<Map<String, dynamic>> _getJson(String path) async {
    final http.Response resp;
    try {
      resp = await _client.get(_uri(path));
    } catch (e) {
      throw Exception('Could not reach the server at ${ApiConfig.baseUrl}: $e');
    }
    if (resp.statusCode == 503) {
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      throw MemoryNotBuiltException(
        body['detail'] as String? ?? 'memory.db has not been built yet',
      );
    }
    if (resp.statusCode == 404) {
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      throw Exception(body['detail'] as String? ?? 'Not found');
    }
    if (resp.statusCode != 200) {
      throw Exception('Server returned ${resp.statusCode}');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  @override
  Future<List<MemoryIdentitySummary>> students() async {
    if (_studentsCache != null) return _studentsCache!;
    final j = await _getJson('/api/memory/students');
    final list = (j['students'] as List? ?? const [])
        .map((e) => MemoryIdentitySummary.fromJson(e as Map<String, dynamic>))
        .toList();
    _studentsCache = list;
    return list;
  }

  @override
  Future<MemoryIdentityDetail> student(String studentId) async {
    final cached = _detailCache[studentId];
    if (cached != null) return cached;
    final j = await _getJson('/api/memory/student/$studentId');
    final detail = MemoryIdentityDetail.fromJson(j);
    _detailCache[studentId] = detail;
    return detail;
  }

  @override
  Future<SittingDetail> sitting(String runId) async {
    final cached = _sittingCache[runId];
    if (cached != null) return cached;
    final j = await _getJson('/api/memory/sitting/$runId');
    final detail = SittingDetail.fromJson(j);
    _sittingCache[runId] = detail;
    return detail;
  }
}

/// Real implementation of [StudentReportRepository], calling the same
/// FastAPI process as [HttpMemoryRepository] — see [ApiConfig.baseUrl].
class HttpStudentReportRepository implements StudentReportRepository {
  HttpStudentReportRepository({http.Client? client})
    : _client = client ?? http.Client();

  final http.Client _client;

  Uri _uri(String path) => Uri.parse('${ApiConfig.baseUrl}$path');

  @override
  Future<StudentReport> report(String studentId, {bool force = false}) async {
    final uri = _uri(
      '/api/report/$studentId${force ? '?force=1' : ''}',
    );
    final http.Response resp;
    try {
      resp = await _client.get(uri);
    } catch (e) {
      throw Exception('Could not reach the server at ${ApiConfig.baseUrl}: $e');
    }

    if (resp.statusCode == 404) {
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      throw ReportNotFoundException(
        body['detail'] as String? ?? 'Student not found',
      );
    }
    if (resp.statusCode == 503) {
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      throw ReportUnavailableException(
        body['detail'] as String? ?? 'The report could not be generated',
      );
    }
    if (resp.statusCode != 200) {
      throw Exception('Server returned ${resp.statusCode}');
    }
    return StudentReport.fromJson(jsonDecode(resp.body) as Map<String, dynamic>);
  }
}
