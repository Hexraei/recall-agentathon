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
import '../../widgets/shared/page_scaffold.dart';

/// Screen 18 — Quiz Result (student).
///
/// The score as a count in the serif over a segment strip, one segment per
/// question; a correct-out-of-total breakdown by topic; and every question
/// with the stem, what was chosen, and — only when wrong — the correct
/// answer. Correct is an accent check, wrong a grey cross; red is not used,
/// because a wrong answer is not an error state.
///
/// Absent by design: class rank, percentile, comparison to named peers.
///
/// States: available; auto-submitted; not yet available.
class StudentQuizResultScreen extends StatefulWidget {
  const StudentQuizResultScreen({super.key, required this.args});

  final QuizResultArgs args;

  @override
  State<StudentQuizResultScreen> createState() =>
      _StudentQuizResultScreenState();
}

class _StudentQuizResultScreenState extends State<StudentQuizResultScreen> {
  late Future<QuizResultData?> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<QuizResultData?> _load() =>
      context.read<ResultsRepository>().myResult(widget.args.quizId);

  void _reload() => setState(() => _future = _load());

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<QuizResultData?>(
      future: _future,
      builder: (context, snap) {
        final r = snap.data;
        final done = snap.connectionState == ConnectionState.done;
        final quiz = r?.quiz;

        return PageScaffold(
          title: quiz?.title ?? 'Result',
          subtitle: r == null ? null : _meta(r),
          backLabel: 'Back to home',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 20),
              if (!done)
                const LoadingState()
              else if (snap.hasError || r == null)
                ErrorState(
                  message: "We couldn't load this result.",
                  onRetry: _reload,
                )
              else if (widget.args.stillOpen)
                ..._notYetAvailable(context, r)
              else
                ..._available(context, r),
            ],
          ),
        );
      },
    );
  }

  String _meta(QuizResultData r) {
    final quiz = r.quiz;
    final week = quiz.week == null ? '' : '${quiz.week} · ';
    if (widget.args.stillOpen) {
      return '${week}Submitted ${_hhmm(r.submittedAt)} · still open';
    }
    return '${week}Ran ${_longDate(r.submittedAt)} · '
        'closed ${_hhmm(quiz.closedAt ?? r.submittedAt)}';
  }

  /// While the quiz is still open, the screen shows what was submitted rather
  /// than an empty chart, and says when the result lands.
  List<Widget> _notYetAvailable(BuildContext context, QuizResultData r) {
    return [
      const InfoBand(
        title: 'Not marked yet',
        text: 'The quiz is still open for the rest of the class. Your result '
            'appears once it closes.',
      ),
      const SizedBox(height: 16),
      RowCard(
        children: [
          FactRow(
            label: 'Questions answered',
            value: '${r.total - r.blanks} of ${r.total}',
          ),
          FactRow(label: 'Submitted at', value: _hhmm(r.submittedAt)),
        ],
      ),
      const SizedBox(height: 20),
      OutlinedAction(
        label: 'Back to home',
        onPressed: () => Navigator.of(context).pop(),
      ),
    ];
  }

  List<Widget> _available(BuildContext context, QuizResultData r) {
    return [
      AppCard(
        padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // The score is a count first; the percentage is the quieter
            // second line.
            Text('${r.correct} of ${r.total}', style: AppText.displayResult),
            const SizedBox(height: 2),
            Text('answered correctly · ${r.percent}%',
                style: AppText.body.copyWith(color: AppColors.grey1)),
            if (r.autoSubmitted && r.blanks > 0) ...[
              const SizedBox(height: 6),
              Text('${r.blanks} left blank when time ran out',
                  style: AppText.rowSecondary),
            ],
            const SizedBox(height: 16),
            SegmentStrip(total: r.total, correct: r.correct),
          ],
        ),
      ),
      const SectionLabel('By topic'),
      RowCard(
        children: [
          for (final t in r.topicScores)
            FactRow(label: t.topic, value: t.label),
        ],
      ),
      const SectionLabel('Every question'),
      RowCard(
        children: [
          for (final q in r.questionResults) _QuestionResultRow(result: q),
        ],
      ),
      const SizedBox(height: 18),
      OutlinedAction(
        label: 'See my performance',
        onPressed: () => Navigator.of(context).pushNamed(Routes.myPerformance),
      ),
    ];
  }

  static String _hhmm(DateTime d) =>
      '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';

  static String _longDate(DateTime d) {
    const months = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December',
    ];
    return '${d.day} ${months[d.month - 1]}';
  }
}

class _QuestionResultRow extends StatelessWidget {
  const _QuestionResultRow({required this.result});

  final QuestionResult result;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // An accent check or a grey cross. Never red: getting a question
          // wrong is not an error state.
          Icon(
            result.isCorrect ? Icons.check : Icons.close,
            size: 18,
            color: result.isCorrect ? AppColors.accent : AppColors.grey4,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('${result.position}. ${result.question.text}',
                    style: AppText.rowTitle
                        .copyWith(fontSize: 14, height: 20 / 14)),
                const SizedBox(height: 6),
                Text(
                  result.isBlank
                      ? 'You left this blank'
                      : 'You chose ${result.chosenLetter} · ${result.chosenOption}',
                  style: AppText.caption
                      .copyWith(fontSize: 13, height: 19 / 13, color: AppColors.grey2),
                ),
                // The correct answer is shown only when the student got it
                // wrong; naming it on a correct answer would be noise.
                if (!result.isCorrect) ...[
                  const SizedBox(height: 3),
                  Text(
                    'Correct answer ${result.question.correctLetter} · '
                    '${result.question.correctOption}',
                    style: AppText.caption.copyWith(
                        fontSize: 13, height: 19 / 13, color: AppColors.ink),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
