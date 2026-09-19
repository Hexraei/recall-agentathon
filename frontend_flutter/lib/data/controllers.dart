import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/models.dart';
import 'repositories.dart';

/// Who is signed in, and which role the app is running as.
class AuthController extends ChangeNotifier {
  AuthController(this._repo);

  final AuthRepository _repo;

  AppUser? _user;
  AppUser? get user => _user;
  bool get isSignedIn => _user != null;

  Future<AppUser?> restore() async {
    _user = await _repo.restoreSession();
    notifyListeners();
    return _user;
  }

  Future<AppUser> signIn(String identifier, String password) async {
    _user = await _repo.signIn(identifier: identifier, password: password);
    notifyListeners();
    return _user!;
  }

  Future<AppUser> signUp({
    required String name,
    required String identifier,
    required String password,
    required UserRole role,
  }) async {
    _user = await _repo.signUp(
      name: name,
      identifier: identifier,
      password: password,
      role: role,
    );
    notifyListeners();
    return _user!;
  }

  Future<void> signOut() async {
    await _repo.signOut();
    _user = null;
    notifyListeners();
  }
}

/// The quiz being composed in the builder.
///
/// Validation is per field, and Add question stays disabled until the
/// question, its options and its correct answer are all resolved.
class QuizBuilderController extends ChangeNotifier {
  QuizBuilderController(this._repo, {Quiz? existing})
      : _questions = [...?existing?.questions],
        title = existing?.title ?? '',
        timeLimit = existing?.timeLimitMinutes.toString() ?? '',
        _existing = existing;

  final QuizRepository _repo;
  final Quiz? _existing;

  String title;
  String timeLimit;

  String questionText = '';
  String topic = '';
  final List<String> options = ['', '', '', ''];
  int? correctIndex;

  final List<Question> _questions;
  List<Question> get questions => List.unmodifiable(_questions);

  bool _saving = false;
  bool get saving => _saving;

  /// Set once the teacher has tried to add a question, so errors do not
  /// appear before they have done anything.
  bool _showErrors = false;
  bool get showErrors => _showErrors;

  bool _dirty = false;
  bool get dirty => _dirty;

  List<String> _topicSuggestions = [];
  List<String> get topicSuggestions => _topicSuggestions;

  Future<void> loadTopics() async {
    _topicSuggestions = await _repo.knownTopics();
    notifyListeners();
  }

  /// Topic matching is a case-insensitive substring, and the combobox is the
  /// only way a topic is entered, so "Hash table" and "Hash tables" cannot
  /// split into two.
  List<String> filteredTopics() {
    final q = topic.trim().toLowerCase();
    if (q.isEmpty) return _topicSuggestions;
    return _topicSuggestions
        .where((t) => t.toLowerCase().contains(q))
        .toList();
  }

  void touch() {
    _dirty = true;
    notifyListeners();
  }

  // ------------------------------------------------------------- validation
  String? get titleError =>
      _showErrors && title.trim().isEmpty ? 'Give the quiz a name.' : null;

  String? get timeLimitError {
    if (!_showErrors) return null;
    final n = int.tryParse(timeLimit.trim());
    if (n == null || n <= 0) return 'Set a whole number of minutes.';
    return null;
  }

  String? get questionError => _showErrors && questionText.trim().isEmpty
      ? 'Write the question.'
      : null;

  String? get topicError =>
      _showErrors && topic.trim().isEmpty ? 'Choose a topic.' : null;

  String? optionError(int i) => _showErrors && options[i].trim().isEmpty
      ? 'Fill this option in.'
      : null;

  String? get correctError => _showErrors && correctIndex == null
      ? 'Mark which option is correct.'
      : null;

  bool get canAddQuestion =>
      questionText.trim().isNotEmpty &&
      topic.trim().isNotEmpty &&
      options.every((o) => o.trim().isNotEmpty) &&
      correctIndex != null;

  bool get canSave =>
      title.trim().isNotEmpty &&
      (int.tryParse(timeLimit.trim()) ?? 0) > 0 &&
      _questions.isNotEmpty;

  bool addQuestion() {
    if (!canAddQuestion) {
      _showErrors = true;
      notifyListeners();
      return false;
    }
    _questions.add(Question(
      id: 'q${DateTime.now().microsecondsSinceEpoch}',
      text: questionText.trim(),
      topic: topic.trim(),
      options: [for (final o in options) o.trim()],
      correctIndex: correctIndex!,
    ));

    // The composer carries the last topic forward, since consecutive
    // questions usually share one.
    questionText = '';
    for (var i = 0; i < 4; i++) {
      options[i] = '';
    }
    correctIndex = null;
    _showErrors = false;
    _dirty = true;
    notifyListeners();
    return true;
  }

  void removeQuestion(String id) {
    _questions.removeWhere((q) => q.id == id);
    _dirty = true;
    notifyListeners();
  }

  Future<Quiz?> save() async {
    if (!canSave) {
      _showErrors = true;
      notifyListeners();
      return null;
    }
    _saving = true;
    notifyListeners();

    final quiz = (_existing ??
            Quiz(
              id: 'q${DateTime.now().microsecondsSinceEpoch}',
              title: '',
              questions: const [],
              timeLimitMinutes: 20,
            ))
        .copyWith(
      title: title.trim(),
      timeLimitMinutes: int.parse(timeLimit.trim()),
      questions: _questions,
    );
    await _repo.saveQuiz(quiz);

    _saving = false;
    _dirty = false;
    notifyListeners();
    return quiz;
  }
}

/// The teacher's live session: the lobby, then the monitor.
enum HostPhase { lobby, starting, running, deadlineNear, everyoneSubmitted, closed }

class HostSessionController extends ChangeNotifier {
  HostSessionController(this._repo, this.quiz);

  final SessionRepository _repo;
  final Quiz quiz;

  String pin = '';
  HostPhase phase = HostPhase.lobby;
  List<AppUser> joined = const [];
  List<StudentProgress> rows = const [];
  Duration remaining = Duration.zero;

  StreamSubscription<List<AppUser>>? _joinSub;
  StreamSubscription<List<StudentProgress>>? _progressSub;
  Timer? _ticker;

  int get answering =>
      rows.where((r) => r.stage == AttemptStage.answering).length;
  int get submitted =>
      rows.where((r) => r.stage == AttemptStage.submitted).length;
  int get autoSubmitted => rows.where((r) => r.autoSubmitted).length;

  Future<void> open() async {
    pin = await _repo.host(quiz);
    notifyListeners();
    _joinSub = _repo.joinedStudents().listen((s) {
      joined = s;
      notifyListeners();
    });
  }

  Future<void> start() async {
    phase = HostPhase.starting;
    notifyListeners();

    await _repo.start();
    await _joinSub?.cancel();

    remaining = quiz.duration;
    phase = HostPhase.running;
    notifyListeners();

    _progressSub = _repo.progress().listen((r) {
      rows = r;
      if (rows.isNotEmpty &&
          rows.every((x) => x.stage == AttemptStage.submitted) &&
          phase != HostPhase.closed) {
        phase = HostPhase.everyoneSubmitted;
      }
      notifyListeners();
    });

    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      remaining -= const Duration(seconds: 1);
      if (remaining <= Duration.zero) {
        remaining = Duration.zero;
        close();
        return;
      }
      if (remaining <= const Duration(minutes: 2) &&
          phase == HostPhase.running) {
        phase = HostPhase.deadlineNear;
      }
      notifyListeners();
    });
  }

  /// Exiting the monitor ends the quiz: it auto-submits every open attempt
  /// and closes the window. There is deliberately no way to leave with the
  /// quiz still running.
  Future<void> close() async {
    _ticker?.cancel();
    await _progressSub?.cancel();
    await _repo.endQuiz();
    phase = HostPhase.closed;
    notifyListeners();
  }

  /// A short demo cadence, so the monitor's later states are reachable
  /// without waiting twenty minutes.
  void jumpToDeadlineNear() {
    remaining = const Duration(seconds: 48);
    phase = HostPhase.deadlineNear;
    notifyListeners();
  }

  @override
  void dispose() {
    _ticker?.cancel();
    _joinSub?.cancel();
    _progressSub?.cancel();
    super.dispose();
  }
}

/// A student's attempt: the lobby, the questions, and the submission.
class AttemptController extends ChangeNotifier {
  AttemptController(this._repo, this.quiz, {Duration? startingFrom})
      : remaining = startingFrom ?? quiz.duration,
        attempt = Attempt(quizId: quiz.id, studentId: 'me');

  final AttemptRepository _repo;
  final Quiz quiz;
  final Attempt attempt;

  Duration remaining;
  int index = 0;
  bool autoSubmitting = false;
  bool submitting = false;

  Timer? _ticker;

  Question get current => quiz.questions[index];
  int get answeredCount => attempt.answeredCount;
  int get total => quiz.questionCount;
  bool get isFirst => index == 0;
  bool get isLast => index == total - 1;
  bool get deadlineNear => remaining <= const Duration(minutes: 1);

  List<int> get unansweredPositions => [
        for (var i = 0; i < quiz.questions.length; i++)
          if (!attempt.answers.containsKey(quiz.questions[i].id)) i + 1,
      ];

  int? answerFor(int i) => attempt.answers[quiz.questions[i].id];

  void startClock() {
    _ticker?.cancel();
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      remaining -= const Duration(seconds: 1);
      if (remaining <= Duration.zero) {
        remaining = Duration.zero;
        _ticker?.cancel();
        autoSubmit();
        return;
      }
      notifyListeners();
    });
  }

  void choose(int optionIndex) {
    attempt.answers[current.id] = optionIndex;
    notifyListeners();
  }

  void goTo(int i) {
    index = i.clamp(0, total - 1);
    notifyListeners();
  }

  void next() => goTo(index + 1);
  void previous() => goTo(index - 1);

  Future<void> submit() async {
    submitting = true;
    notifyListeners();
    await _repo.submit(attempt);
    submitting = false;
    notifyListeners();
  }

  /// At the deadline the attempt submits itself with whatever is answered.
  Future<void> autoSubmit() async {
    autoSubmitting = true;
    notifyListeners();
    await _repo.submit(attempt, auto: true);
    notifyListeners();
  }

  /// A short demo cadence, so the red header and the overlay are reachable.
  void jumpToDeadlineNear() {
    remaining = const Duration(seconds: 48);
    notifyListeners();
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }
}
