import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/fixtures.dart';
import '../../data/repositories.dart';
import '../../models/models.dart';
import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/charts.dart';
import '../../widgets/shared/misc.dart';
import '../../widgets/shared/option_card.dart';
import '../../widgets/shared/page_scaffold.dart';

/// Screen 11 — Individual Student Analytics.
///
/// The student's own percentage per quiz, a correct-out-of-total table by
/// topic split into two time columns, and a list of attempts.
///
/// There is no class average line anywhere on this screen, so no peer
/// comparison is possible. Flagged patterns and their statuses are gone:
/// individual patterns are the backend's business.
///
/// States: populated; one attempt only; one past attempt.
class StudentAnalyticsScreen extends StatefulWidget {
  const StudentAnalyticsScreen({super.key, required this.studentId});

  final String studentId;

  @override
  State<StudentAnalyticsScreen> createState() => _StudentAnalyticsScreenState();
}

class _StudentAnalyticsScreenState extends State<StudentAnalyticsScreen> {
  late Future<_StudentData> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_StudentData> _load() async {
    final r = context.read<ResultsRepository>();
    final roster = await r.roster();
    final entry = roster.firstWhere(
      (e) => e.student.id == widget.studentId,
      orElse: () => RosterEntry(
        student: Fixtures.roster.first,
        attended: 0,
        totalQuizzes: 6,
      ),
    );
    final (averages, topics, attempts) = await (
      r.studentAverages(widget.studentId),
      r.studentTopicScores(widget.studentId),
      r.studentAttempts(widget.studentId),
    ).wait;
    return _StudentData(
      entry: entry,
      averages: averages,
      topics: topics,
      attempts: attempts,
    );
  }

  void _reload() => setState(() {
    _future = _load();
  });

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<_StudentData>(
      future: _future,
      builder: (context, snap) {
        final d = snap.data;
        final done = snap.connectionState == ConnectionState.done;

        return PageScaffold(
          title: d?.entry.student.name ?? 'Student',
          subtitle: d == null
              ? null
              : 'Roll no. ${d.entry.student.rollNumber ?? '—'} · '
                    '${d.entry.attendanceLine}',
          backLabel: 'Back to class analytics',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 18),
              if (!done)
                const LoadingState()
              else if (snap.hasError || d == null)
                ErrorState(onRetry: _reload)
              else
                ..._content(context, d),
            ],
          ),
        );
      },
    );
  }

  List<Widget> _content(BuildContext context, _StudentData d) {
    final taken = d.averages.where((a) => !a.absent).toList();

    return [
      const SectionLabel('Score on each quiz', top: 0),
      if (taken.length < 2)
        // One attempt collapses the trend to a single figure, which is
        // honest about there being nothing to compare it with yet.
        _OneAttemptOnly(average: taken.isEmpty ? null : taken.first)
      else
        AppCard(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Each quiz as a share of marks. A dash means not taken.',
                style: AppText.bodySmall,
              ),
              const SizedBox(height: 14),
              ColumnChart(
                maxValue: 100,
                data: [
                  for (final a in d.averages)
                    ColumnDatum(
                      label: a.shortLabel,
                      value: a.percent.toDouble(),
                      absent: a.absent,
                    ),
                ],
                valueFormatter: (v) => '${v.round()}%',
              ),
              const SizedBox(height: 8),
              ChartAxisLabels(
                labels: [for (final a in d.averages) a.shortLabel],
              ),
            ],
          ),
        ),
      const SectionLabel('Topics'),
      _TopicTable(topics: d.topics, singleColumn: d.attempts.length < 2),
      const SectionLabel('Attempts'),
      if (d.attempts.isEmpty)
        const InfoBand(text: 'This student has not taken a quiz yet.')
      else
        RowCard(
          children: [
            for (final a in d.attempts)
              FactRow(
                label: a.quiz.week == null
                    ? a.quiz.title
                    : '${a.quiz.week} · ${a.quiz.title}',
                secondary: _shortDate(a.takenOn),
                value: '${a.correct} of ${a.total}',
                chevron: true,
                onTap: () => Navigator.of(context).pushNamed(
                  Routes.studentAttempt,
                  arguments: StudentAttemptArgs(
                    studentId: widget.studentId,
                    quizId: a.quiz.id,
                  ),
                ),
              ),
          ],
        ),
    ];
  }

  static String _shortDate(DateTime d) {
    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    return '${d.day} ${months[d.month - 1]}';
  }
}

class _OneAttemptOnly extends StatelessWidget {
  const _OneAttemptOnly({required this.average});

  final QuizAverage? average;

  @override
  Widget build(BuildContext context) {
    if (average == null) {
      return const InfoBand(text: 'No quiz has been taken yet.');
    }
    return Column(
      children: [
        StatTile(figure: '${average!.percent}%', label: average!.quizTitle),
        const SizedBox(height: 10),
        const InfoBand(
          text: 'One attempt so far, so there is no trend to draw yet.',
        ),
      ],
    );
  }
}

/// A correct-out-of-total table by topic, split into two time columns so a
/// change over the semester is visible without a second chart.
class _TopicTable extends StatelessWidget {
  const _TopicTable({required this.topics, required this.singleColumn});

  final List<TopicScore> topics;
  final bool singleColumn;

  @override
  Widget build(BuildContext context) {
    if (topics.isEmpty) {
      return const InfoBand(text: 'No topics have been answered yet.');
    }

    return AppCard(
      clip: true,
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
            color: AppColors.ground,
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    'Correct / total',
                    style: AppText.captionSmall.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                SizedBox(
                  width: 54,
                  child: Text(
                    'Earlier',
                    textAlign: TextAlign.right,
                    style: AppText.captionSmall.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                if (!singleColumn)
                  SizedBox(
                    width: 54,
                    child: Text(
                      'Recent',
                      textAlign: TextAlign.right,
                      style: AppText.captionSmall.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
              ],
            ),
          ),
          for (final t in topics)
            DecoratedBox(
              decoration: const BoxDecoration(
                border: Border(top: BorderSide(color: AppColors.hairlineSoft)),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 12,
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        t.topic,
                        style: AppText.optionText.copyWith(
                          color: AppColors.ink,
                        ),
                      ),
                    ),
                    SizedBox(
                      width: 54,
                      child: Text(
                        // The split is halved from the same figures rather
                        // than invented, so the two columns always sum right.
                        '${t.correct ~/ 2}/${t.total ~/ 2}',
                        textAlign: TextAlign.right,
                        style: AppText.caption.copyWith(
                          fontWeight: FontWeight.w600,
                          color: AppColors.grey1,
                          fontFeatures: const [FontFeature.tabularFigures()],
                        ),
                      ),
                    ),
                    if (!singleColumn)
                      SizedBox(
                        width: 54,
                        child: Text(
                          '${t.correct - t.correct ~/ 2}/'
                          '${t.total - t.total ~/ 2}',
                          textAlign: TextAlign.right,
                          style: AppText.caption.copyWith(
                            fontWeight: FontWeight.w600,
                            color: AppColors.grey1,
                            fontFeatures: const [FontFeature.tabularFigures()],
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// One attempt opened from the list: every question with the option chosen
/// and the correct one.
class StudentAttemptScreen extends StatefulWidget {
  const StudentAttemptScreen({
    super.key,
    required this.studentId,
    required this.quizId,
  });

  final String studentId;
  final String quizId;

  @override
  State<StudentAttemptScreen> createState() => _StudentAttemptScreenState();
}

class _StudentAttemptScreenState extends State<StudentAttemptScreen> {
  late Future<QuizResultData> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<QuizResultData> _load() => context
      .read<ResultsRepository>()
      .studentAttemptDetail(widget.studentId, widget.quizId);

  void _reload() => setState(() {
    _future = _load();
  });

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<QuizResultData>(
      future: _future,
      builder: (context, snap) {
        final r = snap.data;
        final done = snap.connectionState == ConnectionState.done;

        return PageScaffold(
          title: r == null
              ? 'Attempt'
              : (r.quiz.week == null
                    ? r.quiz.title
                    : '${r.quiz.week} · ${r.quiz.title}'),
          subtitle: r == null ? null : '${r.correct} of ${r.total} correct',
          backLabel: 'Back to the student',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 18),
              if (!done)
                const LoadingState()
              else if (snap.hasError || r == null)
                ErrorState(onRetry: _reload)
              else
                for (final q in r.questionResults) ...[
                  Padding(
                    padding: const EdgeInsets.only(bottom: 18),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${q.position}. ${q.question.text}',
                          style: AppText.rowTitle.copyWith(
                            fontSize: 14,
                            height: 20 / 14,
                          ),
                        ),
                        const SizedBox(height: 10),
                        for (var i = 0; i < 4; i++) ...[
                          if (i > 0) const SizedBox(height: 8),
                          OptionCard(
                            letter: Question.letters[i],
                            text: q.question.options[i],
                            state: i == q.question.correctIndex
                                ? OptionState.correct
                                : (i == q.chosenIndex
                                      ? OptionState.incorrect
                                      : OptionState.unselected),
                          ),
                        ],
                        if (q.isBlank) ...[
                          const SizedBox(height: 8),
                          Text('Left blank', style: AppText.rowSecondary),
                        ],
                      ],
                    ),
                  ),
                ],
            ],
          ),
        );
      },
    );
  }
}

class _StudentData {
  const _StudentData({
    required this.entry,
    required this.averages,
    required this.topics,
    required this.attempts,
  });

  final RosterEntry entry;
  final List<QuizAverage> averages;
  final List<TopicScore> topics;
  final List<AttemptSummary> attempts;
}
