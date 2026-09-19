import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/repositories.dart';
import '../../models/models.dart';
import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/buttons.dart';
import '../../widgets/shared/charts.dart';
import '../../widgets/shared/misc.dart';
import '../../widgets/shared/nav_list.dart';
import '../../widgets/shared/page_scaffold.dart';
import '../../widgets/shared/sheets.dart';
import '../../widgets/shared/topic_row.dart';

/// Screen 08 — Quiz Results.
///
/// Participation and median as two tiles, a score distribution column chart,
/// then topics worst-first. The screen does not list loose questions:
/// ordering questions says which question went badly, ordering topics says
/// what to reteach.
///
/// States: full participation; partial participation; topic opened; one
/// question opened. Loading and error are added, since the screen fetches.
class QuizResultsScreen extends StatefulWidget {
  const QuizResultsScreen({super.key, required this.quizId});

  final String quizId;

  @override
  State<QuizResultsScreen> createState() => _QuizResultsScreenState();
}

class _QuizResultsScreenState extends State<QuizResultsScreen> {
  late Future<ClassQuizResult> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<ClassQuizResult> _load() =>
      context.read<ResultsRepository>().classResult(widget.quizId);

  void _reload() => setState(() => _future = _load());

  static const _bands = ['0–3', '4–6', '7–9', '10–12', '13–15'];

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<ClassQuizResult>(
      future: _future,
      builder: (context, snap) {
        final r = snap.data;
        final quiz = r?.quiz;

        return PageScaffold(
          title: quiz == null
              ? 'Quiz results'
              : (quiz.week == null ? quiz.title : '${quiz.week} · ${quiz.title}'),
          subtitle: quiz?.lastRun == null
              ? null
              : 'Ran ${_range(quiz!.lastRun!, quiz.closedAt)}',
          backLabel: 'Back to dashboard',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (snap.connectionState != ConnectionState.done)
                const LoadingState()
              else if (snap.hasError || r == null)
                ErrorState(
                  message: "We couldn't load these results.",
                  onRetry: _reload,
                )
              else
                ..._content(context, r),
            ],
          ),
        );
      },
    );
  }

  List<Widget> _content(BuildContext context, ClassQuizResult r) {
    final denominator = r.tookIt;
    return [
      const SizedBox(height: 18),
      Row(
        children: [
          Expanded(
            child: _WideTile(
              figure: '${r.tookIt} of ${r.classSize}',
              label: 'Took the quiz',
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _WideTile(
              // Median survives the long tail of low scores that a mean
              // does not, so it sits beside participation.
              figure: '${r.medianScore} of ${r.quiz.questionCount}',
              label: 'Median score',
            ),
          ),
        ],
      ),
      if (!r.fullParticipation) ...[
        const SizedBox(height: 12),
        InfoBand(
          icon: Icons.info_outline,
          text: '${r.neverOpened} students never opened this quiz. Everything '
              'below counts only the ${r.tookIt} who did.',
        ),
      ],
      const SectionLabel('How the class scored', top: 24),
      AppCard(
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              r.fullParticipation
                  ? 'Students in each score band, out of ${r.quiz.questionCount}.'
                  : 'The $denominator students who took it, by score band, '
                      'out of ${r.quiz.questionCount}.',
              style: AppText.bodySmall.copyWith(height: 19 / 13.5),
            ),
            const SizedBox(height: 14),
            ColumnChart(
              data: [
                for (var i = 0; i < r.distribution.length; i++)
                  ColumnDatum(
                      label: _bands[i], value: r.distribution[i].toDouble()),
              ],
            ),
            const SizedBox(height: 8),
            const ChartAxisLabels(labels: _bands),
          ],
        ),
      ),
      const SectionLabel('Topics — worst answered first', top: 26),
      RowCard(
        children: [
          for (final t in r.topicScores)
            TopicRow(
              topic: t.topic,
              secondary:
                  '${t.total} question${t.total == 1 ? '' : 's'}',
              percent: t.percent,
              onTap: () => _openTopic(context, r, t),
            ),
        ],
      ),
      const SizedBox(height: 16),
      NavList(rows: [
        NavRow(
          icon: Icons.person_outline,
          title: 'Open a student',
          secondary: '${r.tookIt} took it',
          onTap: () => Navigator.of(context).pushNamed(
              Routes.studentAnalytics,
              arguments: 's1'),
        ),
        NavRow(
          icon: Icons.bar_chart,
          title: 'Class analytics',
          secondary: 'All quizzes',
          onTap: () =>
              Navigator.of(context).pushNamed(Routes.classAnalytics),
        ),
      ]),
    ];
  }

  void _openTopic(BuildContext context, ClassQuizResult r, TopicScore t) {
    Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => _QuizTopicScreen(result: r, topic: t),
    ));
  }

  static String _range(DateTime from, DateTime? to) {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
    ];
    final d = '${days[from.weekday - 1]} ${from.day} ${months[from.month - 1]}';
    final f = _hhmm(from);
    return to == null ? '$d, from $f' : '$d, $f to ${_hhmm(to)}';
  }

  static String _hhmm(DateTime d) =>
      '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
}

class _WideTile extends StatelessWidget {
  const _WideTile({required this.figure, required this.label});

  final String figure;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
      decoration: BoxDecoration(
        color: AppColors.white,
        border: Border.all(color: AppColors.hairline),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Text(figure,
                style: AppText.tileFigure
                    .copyWith(fontSize: 26, letterSpacing: -0.5)),
          ),
          const SizedBox(height: 3),
          Text(label, style: AppText.caption.copyWith(color: AppColors.grey2)),
        ],
      ),
    );
  }
}

/// A topic opened from Quiz Results: its percentage, a line naming what is
/// wrong, and its questions worst-first.
class _QuizTopicScreen extends StatelessWidget {
  const _QuizTopicScreen({required this.result, required this.topic});

  final ClassQuizResult result;
  final TopicScore topic;

  @override
  Widget build(BuildContext context) {
    final quiz = result.quiz;
    final questions = result.breakdowns
        .where((b) => b.question.topic == topic.topic)
        .toList();
    final belowHalf = questions.where((q) => q.correctPercent < 50).length;
    final worst = result.topicScores.isNotEmpty &&
        result.topicScores.first.topic == topic.topic;

    return PageScaffold(
      title: topic.topic,
      subtitle: '${questions.length} question${questions.length == 1 ? '' : 's'} '
          'in ${quiz.week == null ? quiz.title : '${quiz.week} · ${quiz.title}'}',
      backLabel: 'Back to quiz results',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 18),
          AppCard(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('Answered correctly across the topic',
                    style: AppText.caption.copyWith(fontSize: 12.5)),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(child: TopicBar(fraction: topic.fraction)),
                    const SizedBox(width: 12),
                    Text('${topic.percent}%',
                        style: AppText.rowTitle.copyWith(fontSize: 15)),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          InfoBand(
            text: '${worst ? 'The weakest topic in this quiz. ' : ''}'
                '$belowHalf of its ${questions.length} question'
                '${questions.length == 1 ? '' : 's'} '
                '${belowHalf == 1 ? 'was' : 'were'} answered correctly by fewer '
                'than half the class.',
          ),
          const SectionLabel('Questions in this topic — worst first'),
          RowCard(
            children: [
              for (final b in questions)
                _QuestionRow(
                  breakdown: b,
                  position: quiz.questions.indexOf(b.question) + 1,
                  onTap: () => showAppSheet<void>(
                    context: context,
                    builder: (_) => _QuestionSheet(breakdown: b),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _QuestionRow extends StatelessWidget {
  const _QuestionRow({
    required this.breakdown,
    required this.position,
    this.onTap,
  });

  final QuestionBreakdown breakdown;
  final int position;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 13, 16, 13),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                width: 30,
                child: Text('Q$position',
                    style: AppText.captionSmall
                        .copyWith(fontWeight: FontWeight.w600)),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(breakdown.question.text,
                        style: AppText.bodySmall.copyWith(color: AppColors.ink)),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: TopicBar(
                              fraction: breakdown.correctPercent / 100),
                        ),
                        const SizedBox(width: 10),
                        Text('${breakdown.correctPercent}%',
                            style: AppText.rowTitle.copyWith(fontSize: 13)),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// The sheet showing the split across all four options. The correct one is
/// accent-filled; the three wrong ones are neutral grey, so the distractor
/// that beat the answer is visible without being flattered.
class _QuestionSheet extends StatelessWidget {
  const _QuestionSheet({required this.breakdown});

  final QuestionBreakdown breakdown;

  @override
  Widget build(BuildContext context) {
    final q = breakdown.question;
    return SheetFrame(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(q.text, style: AppText.sheetTitle),
          const SizedBox(height: 6),
          Text('${breakdown.respondents} answered', style: AppText.rowSecondary),
          const SizedBox(height: 18),
          for (var i = 0; i < 4; i++) ...[
            if (i > 0) const SizedBox(height: 10),
            _OptionShare(
              letter: Question.letters[i],
              text: q.options[i],
              percent: breakdown.respondents == 0
                  ? 0
                  : (breakdown.shares[i] / breakdown.respondents * 100).round(),
              isCorrect: i == q.correctIndex,
            ),
          ],
          const SizedBox(height: 22),
          OutlinedAction(
            label: 'Close',
            onPressed: () => Navigator.of(context).pop(),
          ),
        ],
      ),
    );
  }
}

class _OptionShare extends StatelessWidget {
  const _OptionShare({
    required this.letter,
    required this.text,
    required this.percent,
    required this.isCorrect,
  });

  final String letter;
  final String text;
  final int percent;
  final bool isCorrect;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 24,
              height: 24,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: isCorrect ? AppColors.accent : AppColors.ground,
                border:
                    isCorrect ? null : Border.all(color: AppColors.hairlineStrong),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(letter,
                  style: AppText.captionSmall.copyWith(
                    fontWeight: FontWeight.w600,
                    color: isCorrect ? AppColors.white : AppColors.grey2,
                  )),
            ),
            const SizedBox(width: 11),
            Expanded(
              child: Text(text,
                  style: AppText.optionText.copyWith(
                    color: AppColors.ink,
                    fontWeight: isCorrect ? FontWeight.w600 : FontWeight.w400,
                  )),
            ),
            if (isCorrect) ...[
              const SizedBox(width: 8),
              const Icon(Icons.check, size: 16, color: AppColors.accent),
            ],
          ],
        ),
        const SizedBox(height: 7),
        Padding(
          padding: const EdgeInsets.only(left: 35),
          child: Row(
            children: [
              Expanded(
                child: Container(
                  height: 6,
                  decoration: BoxDecoration(
                    color: AppColors.hairlineSoft,
                    borderRadius: BorderRadius.circular(3),
                  ),
                  alignment: Alignment.centerLeft,
                  child: FractionallySizedBox(
                    widthFactor: (percent / 100).clamp(0.0, 1.0),
                    child: Container(
                      decoration: BoxDecoration(
                        // Colour carries nothing here beyond correctness:
                        // the wrong options are neutral, never red.
                        color: isCorrect ? AppColors.accent : AppColors.grey4,
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              SizedBox(
                width: 38,
                child: Text('$percent%',
                    textAlign: TextAlign.right,
                    style: AppText.caption.copyWith(
                        fontWeight: FontWeight.w600, color: AppColors.grey1)),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
