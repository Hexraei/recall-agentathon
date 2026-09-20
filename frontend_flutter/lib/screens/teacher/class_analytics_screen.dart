import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/fixtures.dart';
import '../../data/repositories.dart';
import '../../models/models.dart';
import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/buttons.dart';
import '../../widgets/shared/charts.dart';
import '../../widgets/shared/misc.dart';
import '../../widgets/shared/page_scaffold.dart';
import '../../widgets/shared/sheets.dart';
import '../../widgets/shared/topic_row.dart';

/// Screen 09 — Class Analytics.
///
/// Order on screen: filter, class average per quiz, topics across quizzes,
/// students. The roster carries attendance and never a score, so it cannot
/// read as a ranking.
///
/// States: populated; filter open; too few quizzes for a trend; no quizzes
/// closed yet; the topic pages. Loading and error are added.
class ClassAnalyticsScreen extends StatefulWidget {
  const ClassAnalyticsScreen({super.key});

  @override
  State<ClassAnalyticsScreen> createState() => _ClassAnalyticsScreenState();
}

class _ClassAnalyticsScreenState extends State<ClassAnalyticsScreen> {
  late Future<_AnalyticsData> _future;
  bool _showAllTopics = false;
  bool _showAllStudents = false;
  String _search = '';

  /// How many of the most recent quizzes are in view. The filter narrows it.
  int _quizzesInView = 6;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_AnalyticsData> _load() async {
    final r = context.read<ResultsRepository>();
    final (averages, topics, roster) = await (
      r.classAverages(),
      r.topicAggregates(),
      r.roster(),
    ).wait;
    return _AnalyticsData(averages: averages, topics: topics, roster: roster);
  }

  void _reload() => setState(() {
    _future = _load();
  });

  Future<void> _openFilter(int available) async {
    final picked = await showAppSheet<int>(
      context: context,
      builder: (context) =>
          _FilterSheet(available: available, selected: _quizzesInView),
    );
    if (picked != null) setState(() => _quizzesInView = picked);
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<_AnalyticsData>(
      future: _future,
      builder: (context, snap) {
        final d = snap.data;
        final done = snap.connectionState == ConnectionState.done;
        final averages = d == null
            ? const <QuizAverage>[]
            : d.averages.sublist(
                (d.averages.length - _quizzesInView).clamp(
                  0,
                  d.averages.length,
                ),
              );

        return PageScaffold(
          title: 'Class analytics',
          subtitle: d == null
              ? null
              : '${averages.length} quizzes · ${Fixtures.classSize} students',
          backLabel: 'Back to dashboard',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 18),
              if (!done)
                const LoadingState()
              else if (snap.hasError || d == null)
                ErrorState(
                  message: "We couldn't load class analytics.",
                  onRetry: _reload,
                )
              else if (d.averages.isEmpty)
                const InfoBand(
                  title: 'No quizzes have closed yet',
                  text:
                      'Once a quiz you hosted closes, its results feed the '
                      'trend, the topics and the roster here.',
                )
              else
                ..._content(context, d, averages),
            ],
          ),
        );
      },
    );
  }

  List<Widget> _content(
    BuildContext context,
    _AnalyticsData d,
    List<QuizAverage> averages,
  ) {
    final topics = _showAllTopics ? d.topics : d.topics.take(5).toList();
    final roster = d.roster
        .where(
          (e) =>
              _search.isEmpty ||
              e.student.name.toLowerCase().contains(_search.toLowerCase()),
        )
        .toList();
    final shownRoster = _showAllStudents ? roster : roster.take(5).toList();

    return [
      _FilterRow(
        label: _quizzesInView >= d.averages.length
            ? 'All quizzes'
            : 'Last $_quizzesInView quizzes',
        detail: averages.isEmpty
            ? ''
            : '${averages.first.quizTitle} to ${averages.last.quizTitle}',
        onTap: () => _openFilter(d.averages.length),
      ),
      const SectionLabel('Class average'),
      // Under three quizzes in view a trend would be a line through noise,
      // so the chart is replaced by two tiles and a note.
      if (averages.length < 3)
        _TooFewForTrend(averages: averages)
      else
        AppCard(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Average score on each quiz, in order run.',
                style: AppText.bodySmall,
              ),
              const SizedBox(height: 14),
              ColumnChart(
                maxValue: 100,
                data: [
                  for (final a in averages)
                    ColumnDatum(
                      label: a.shortLabel,
                      value: a.percent.toDouble(),
                    ),
                ],
                valueFormatter: (v) => '${v.round()}%',
              ),
              const SizedBox(height: 8),
              ChartAxisLabels(labels: [for (final a in averages) a.shortLabel]),
            ],
          ),
        ),
      const SectionLabel('Topics — worst answered first'),
      RowCard(
        children: [
          for (final t in topics)
            TopicRow(
              topic: t.topic,
              percent: t.percent,
              secondary: '${t.questionCount} questions',
              tag: t.gapsAwaitingReview > 0
                  ? '${t.gapsAwaitingReview} to review'
                  : null,
              onTap: () => Navigator.of(context)
                  .pushNamed(Routes.classTopic, arguments: t.topic)
                  .then((_) => _reload()),
            ),
        ],
      ),
      if (!_showAllTopics && d.topics.length > 5) ...[
        const SizedBox(height: 10),
        TextAction(
          label: 'Show all ${d.topics.length} topics',
          onPressed: () => setState(() => _showAllTopics = true),
        ),
      ],
      const SectionLabel('Students'),
      _SearchField(onChanged: (v) => setState(() => _search = v)),
      const SizedBox(height: 10),
      RowCard(
        children: [
          for (final e in shownRoster)
            // Attendance, never a score: a roster that carried scores would
            // read as a ranking.
            FactRow(
              label: e.student.name,
              secondary: e.attendanceLine,
              value: '',
              chevron: true,
              onTap: () => Navigator.of(
                context,
              ).pushNamed(Routes.studentAnalytics, arguments: e.student.id),
            ),
        ],
      ),
      if (!_showAllStudents && roster.length > 5) ...[
        const SizedBox(height: 10),
        TextAction(
          label: 'Show all ${roster.length} students',
          onPressed: () => setState(() => _showAllStudents = true),
        ),
      ],
    ];
  }
}

class _FilterRow extends StatelessWidget {
  const _FilterRow({required this.label, required this.detail, this.onTap});

  final String label;
  final String detail;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.white,
      borderRadius: AppRadii.containerR,
      child: InkWell(
        onTap: onTap,
        borderRadius: AppRadii.containerR,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
          decoration: BoxDecoration(
            border: Border.all(color: AppColors.hairline),
            borderRadius: AppRadii.containerR,
          ),
          child: Row(
            children: [
              const Icon(Icons.tune, size: 18, color: AppColors.grey1),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(label, style: AppText.rowTitle.copyWith(fontSize: 14)),
                    if (detail.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(detail, style: AppText.rowSecondary),
                    ],
                  ],
                ),
              ),
              const Icon(Icons.expand_more, size: 18, color: AppColors.grey4),
            ],
          ),
        ),
      ),
    );
  }
}

class _FilterSheet extends StatelessWidget {
  const _FilterSheet({required this.available, required this.selected});

  final int available;
  final int selected;

  @override
  Widget build(BuildContext context) {
    final options = <int>{3, 6, available}.where((n) => n <= available).toList()
      ..sort();
    return SheetFrame(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('Which quizzes?', style: AppText.sheetTitle),
          const SizedBox(height: 6),
          Text(
            'Everything on the screen is recalculated from what you pick.',
            style: AppText.bodySmall,
          ),
          const SizedBox(height: 18),
          RowCard(
            children: [
              for (final n in options)
                FactRow(
                  label: n == available ? 'All quizzes' : 'Last $n quizzes',
                  value: n == selected ? '✓' : '',
                  onTap: () => Navigator.of(context).pop(n),
                ),
            ],
          ),
          const SizedBox(height: 18),
          OutlinedAction(
            label: 'Close',
            onPressed: () => Navigator.of(context).pop(),
          ),
        ],
      ),
    );
  }
}

class _TooFewForTrend extends StatelessWidget {
  const _TooFewForTrend({required this.averages});

  final List<QuizAverage> averages;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            for (var i = 0; i < averages.length; i++) ...[
              if (i > 0) const SizedBox(width: 8),
              Expanded(
                child: StatTile(
                  figure: '${averages[i].percent}%',
                  label: averages[i].quizTitle,
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: 10),
        const InfoBand(
          text:
              'A trend needs at least three quizzes in view. These are the '
              'averages so far.',
        ),
      ],
    );
  }
}

class _SearchField extends StatelessWidget {
  const _SearchField({required this.onChanged});

  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: AppMetrics.control,
      decoration: BoxDecoration(
        color: AppColors.white,
        border: Border.all(color: AppColors.hairlineStrong),
        borderRadius: AppRadii.controlR,
      ),
      child: Row(
        children: [
          const SizedBox(width: 14),
          const Icon(Icons.search, size: 18, color: AppColors.grey4),
          Expanded(
            child: TextField(
              onChanged: onChanged,
              style: AppText.bodyLarge.copyWith(color: AppColors.ink),
              decoration: InputDecoration(
                hintText: 'Search students',
                hintStyle: AppText.bodyLarge.copyWith(
                  color: AppColors.disabledText,
                ),
                border: InputBorder.none,
                isDense: true,
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 15,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AnalyticsData {
  const _AnalyticsData({
    required this.averages,
    required this.topics,
    required this.roster,
  });

  final List<QuizAverage> averages;
  final List<TopicAggregate> topics;
  final List<RosterEntry> roster;
}
