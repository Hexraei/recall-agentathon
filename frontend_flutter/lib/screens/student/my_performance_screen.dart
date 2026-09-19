import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/repositories.dart';
import '../../models/models.dart';
import '../../routes.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/charts.dart';
import '../../widgets/shared/misc.dart';
import '../../widgets/shared/page_scaffold.dart';

/// Screen 19 — My Performance.
///
/// The longitudinal view: the student's own percentage per quiz with a dash
/// for one not taken, topics split into "Steady" and "To work on" with
/// correct-out-of-total across quizzes, and the list of past results.
///
/// Both topic headings describe the work, never the student. Nothing on this
/// screen compares them to anyone.
///
/// States: populated; one quiz only, which explains there is nothing to
/// compare against yet and shows two stat tiles instead of a trend.
class MyPerformanceScreen extends StatefulWidget {
  const MyPerformanceScreen({super.key});

  @override
  State<MyPerformanceScreen> createState() => _MyPerformanceScreenState();
}

class _MyPerformanceScreenState extends State<MyPerformanceScreen> {
  late Future<_PerformanceData> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_PerformanceData> _load() async {
    final r = context.read<ResultsRepository>();
    return _PerformanceData(
      averages: await r.myAverages(),
      topics: await r.myTopicScores(),
      attempts: await r.myAttempts(),
    );
  }

  void _reload() => setState(() => _future = _load());

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<_PerformanceData>(
      future: _future,
      builder: (context, snap) {
        final d = snap.data;
        final done = snap.connectionState == ConnectionState.done;

        return PageScaffold(
          title: 'My performance',
          subtitle: 'Performance across all attempted quizzes',
          backLabel: 'Back to home',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 18),
              if (!done)
                const LoadingState()
              else if (snap.hasError || d == null)
                ErrorState(
                  message: "We couldn't load your performance.",
                  onRetry: _reload,
                )
              else
                ..._content(context, d),
            ],
          ),
        );
      },
    );
  }

  List<Widget> _content(BuildContext context, _PerformanceData d) {
    // "Steady" and "To work on" split at half: answered correctly most times
    // these came up, against answered wrongly more often than not.
    final steady = d.topics.where((t) => t.fraction >= 0.5).toList()
      ..sort((a, b) => b.fraction.compareTo(a.fraction));
    final toWorkOn = d.topics.where((t) => t.fraction < 0.5).toList()
      ..sort((a, b) => a.fraction.compareTo(b.fraction));
    final taken = d.averages.where((a) => !a.absent).toList();

    return [
      const SectionLabel('Score on each quiz', top: 0),
      if (taken.length < 2)
        _OneQuizOnly(average: taken.isEmpty ? null : taken.first)
      else
        AppCard(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('A dash means you did not take that one.',
                  style: AppText.bodySmall),
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
              ChartAxisLabels(labels: [for (final a in d.averages) a.shortLabel]),
            ],
          ),
        ),

      if (steady.isNotEmpty) ...[
        const SectionLabel('Steady'),
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Text('Answered correctly most times these came up.',
              style: AppText.bodySmall),
        ),
        RowCard(
          children: [
            for (final t in steady)
              FactRow(
                label: t.topic,
                value: '',
                secondary: '${t.label} across quizzes',
              ),
          ],
        ),
      ],

      if (toWorkOn.isNotEmpty) ...[
        const SectionLabel('To work on'),
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Text('Answered wrongly more often than not.',
              style: AppText.bodySmall),
        ),
        RowCard(
          children: [
            for (final t in toWorkOn)
              FactRow(
                label: t.topic,
                value: '',
                secondary: '${t.label} across quizzes',
              ),
          ],
        ),
      ],

      const SectionLabel('Your quizzes'),
      RowCard(
        children: [
          for (final a in d.attempts)
            FactRow(
              label: a.quiz.title,
              secondary: a.quiz.week == null
                  ? _longDate(a.takenOn)
                  : '${a.quiz.week} · ${_longDate(a.takenOn)}',
              value: '${a.correct} of ${a.total}',
              chevron: true,
              onTap: () => Navigator.of(context).pushNamed(
                Routes.quizResult,
                arguments: QuizResultArgs(quizId: a.quiz.id),
              ),
            ),
        ],
      ),
    ];
  }

  static String _longDate(DateTime d) {
    const months = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December',
    ];
    return '${d.day} ${months[d.month - 1]}';
  }
}

class _OneQuizOnly extends StatelessWidget {
  const _OneQuizOnly({required this.average});

  final QuizAverage? average;

  @override
  Widget build(BuildContext context) {
    if (average == null) {
      return const InfoBand(
        text: 'Your results appear here after your first quiz closes.',
      );
    }
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: StatTile(
                  figure: '${average!.percent}%', label: average!.quizTitle),
            ),
            const SizedBox(width: 8),
            const Expanded(
              child: StatTile(figure: '1', label: 'Quiz taken'),
            ),
          ],
        ),
        const SizedBox(height: 10),
        const InfoBand(
          text: 'One quiz so far, so there is nothing to compare it against '
              'yet. A trend appears once you have taken a second.',
        ),
      ],
    );
  }
}

class _PerformanceData {
  const _PerformanceData({
    required this.averages,
    required this.topics,
    required this.attempts,
  });

  final List<QuizAverage> averages;
  final List<TopicScore> topics;
  final List<AttemptSummary> attempts;
}
