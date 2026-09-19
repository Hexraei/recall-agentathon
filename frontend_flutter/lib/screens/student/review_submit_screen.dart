import 'package:flutter/material.dart';

import '../../data/controllers.dart';
import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/buttons.dart';
import '../../widgets/shared/countdown.dart';
import '../../widgets/shared/page_scaffold.dart';
import '../../widgets/shared/sheets.dart';

/// Screen 16 — Review & Submit.
///
/// Top left is "Back to questions". A five-by-three grid of 52px question
/// cells — answered in accent tint with an accent border, unanswered as a
/// dashed outline on the ground colour — with a legend, one line stating the
/// count in words, and Submit, which is never disabled.
///
/// States: all answered; three unanswered; the confirmation sheet; submitting.
class ReviewSubmitScreen extends StatefulWidget {
  const ReviewSubmitScreen({super.key, required this.controller});

  final AttemptController controller;

  @override
  State<ReviewSubmitScreen> createState() => _ReviewSubmitScreenState();
}

class _ReviewSubmitScreenState extends State<ReviewSubmitScreen> {
  AttemptController get _c => widget.controller;

  Future<void> _submit() async {
    final blanks = _c.unansweredPositions;

    if (blanks.isNotEmpty) {
      final go = await showAppSheet<bool>(
        context: context,
        builder: (context) => ConfirmSheet(
          title: 'Submit with ${blanks.length} blank?',
          body:
              'Question${blanks.length == 1 ? '' : 's'} ${_listWords(blanks)} '
              'ha${blanks.length == 1 ? 's' : 've'} no answer. They will be '
              'counted as unanswered, and you cannot reopen the quiz after '
              'submitting.',
          confirmLabel: 'Submit anyway',
          cancelLabel: 'Go back and finish them',
        ),
      );
      if (go != true) return;
    }

    await _c.submit();
    if (!mounted) return;

    Navigator.of(context).pushNamedAndRemoveUntil(
      Routes.submitted,
      ModalRoute.withName(Routes.studentHome),
      arguments: SubmittedArgs(
        quiz: _c.quiz,
        answered: _c.answeredCount,
        submittedAt: _c.attempt.submittedAt ?? DateTime.now(),
      ),
    );
  }

  /// "3, 9 and 14" — the sheet names the blanks rather than just counting them.
  static String _listWords(List<int> ns) {
    if (ns.length == 1) return '${ns.first}';
    return '${ns.sublist(0, ns.length - 1).join(', ')} and ${ns.last}';
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _c,
      builder: (context, _) {
        final quiz = _c.quiz;
        final blanks = _c.unansweredPositions;
        final answered = _c.total - blanks.length;

        return TakeoverScaffold(
          actionLabel: 'Back to questions',
          actionEnabled: !_c.submitting,
          onAction: () => Navigator.of(context).pop(),
          scrollable: true,
          bottomBar: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                blanks.isEmpty
                    ? 'All ${_c.total} questions have an answer.'
                    : '${blanks.length} question${blanks.length == 1 ? ' has' : 's have'} '
                          'no answer yet. Tap a number to go back to it.',
                textAlign: TextAlign.center,
                style: AppText.bodySmall,
              ),
              const SizedBox(height: 12),
              // Never disabled: submitting with blanks is allowed, and the
              // sheet is where the warning belongs.
              FilledAction(
                label: _c.submitting ? 'Submitting…' : 'Submit',
                busy: _c.submitting,
                onPressed: _c.submitting ? null : _submit,
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 10),
              Text('Review & submit', style: AppText.pageTitle),
              const SizedBox(height: 3),
              Text(
                '${quiz.title}${quiz.week == null ? '' : ' · ${quiz.week}'} · '
                '${quiz.questionCount} questions',
                style: AppText.bodySmall.copyWith(color: AppColors.grey2),
              ),
              const SizedBox(height: 20),
              Countdown(remaining: _c.remaining),
              const SectionLabel('Your answers'),
              _Grid(
                total: _c.total,
                isAnswered: (i) => _c.answerFor(i) != null,
                onTap: (i) {
                  _c.goTo(i);
                  Navigator.of(context).pop();
                },
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  _LegendSwatch(answered: true, label: 'Answered ($answered)'),
                  const SizedBox(width: 20),
                  _LegendSwatch(
                    answered: false,
                    label: 'Not answered (${blanks.length})',
                  ),
                ],
              ),
              const SizedBox(height: 12),
            ],
          ),
        );
      },
    );
  }
}

class _Grid extends StatelessWidget {
  const _Grid({
    required this.total,
    required this.isAnswered,
    required this.onTap,
  });

  final int total;
  final bool Function(int) isAnswered;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      padding: EdgeInsets.zero,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 5,
        mainAxisSpacing: 10,
        crossAxisSpacing: 10,
        childAspectRatio: 1,
      ),
      itemCount: total,
      itemBuilder: (context, i) =>
          _Cell(number: i + 1, answered: isAnswered(i), onTap: () => onTap(i)),
    );
  }
}

class _Cell extends StatelessWidget {
  const _Cell({
    required this.number,
    required this.answered,
    required this.onTap,
  });

  final int number;
  final bool answered;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    if (answered) {
      return Material(
        color: AppColors.accentTint,
        borderRadius: AppRadii.controlR,
        child: InkWell(
          onTap: onTap,
          borderRadius: AppRadii.controlR,
          child: Container(
            alignment: Alignment.center,
            decoration: BoxDecoration(
              border: Border.all(color: AppColors.accent),
              borderRadius: AppRadii.controlR,
            ),
            child: Text(
              '$number',
              style: AppText.rowTitle.copyWith(
                fontSize: 15,
                color: AppColors.accentDeep,
              ),
            ),
          ),
        ),
      );
    }

    return Material(
      color: AppColors.ground,
      borderRadius: AppRadii.controlR,
      child: InkWell(
        onTap: onTap,
        borderRadius: AppRadii.controlR,
        child: CustomPaint(
          painter: _DashedCellPainter(),
          child: Center(
            child: Text(
              '$number',
              style: AppText.rowTitle.copyWith(
                fontSize: 15,
                color: AppColors.grey3,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _DashedCellPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppColors.hairlineStrong
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    final rrect = RRect.fromRectAndRadius(
      Offset.zero & size,
      const Radius.circular(AppRadii.control),
    );
    for (final metric in (Path()..addRRect(rrect)).computeMetrics()) {
      var d = 0.0;
      while (d < metric.length) {
        final end = (d + 4).clamp(0.0, metric.length);
        canvas.drawPath(metric.extractPath(d, end), paint);
        d += 8;
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _LegendSwatch extends StatelessWidget {
  const _LegendSwatch({required this.answered, required this.label});

  final bool answered;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 14,
          height: 14,
          decoration: BoxDecoration(
            color: answered ? AppColors.accentTint : AppColors.ground,
            border: Border.all(
              color: answered ? AppColors.accent : AppColors.hairlineStrong,
            ),
            borderRadius: BorderRadius.circular(4),
          ),
        ),
        const SizedBox(width: 8),
        Text(label, style: AppText.caption.copyWith(fontSize: 12.5)),
      ],
    );
  }
}
