import 'package:flutter/material.dart';

import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/buttons.dart';
import '../../widgets/shared/misc.dart';

/// Screen 17 — Submitted Confirmation.
///
/// A receipt, not a score: what was answered, when it was submitted, when the
/// quiz closes. Absent by design: score, correctness, rank.
///
/// States: submitted by the student; auto-submitted at the deadline, which
/// says "Time ran out" rather than blaming the student and confirms
/// everything answered was saved.
class SubmittedScreen extends StatelessWidget {
  const SubmittedScreen({super.key, required this.args});

  final SubmittedArgs args;

  @override
  Widget build(BuildContext context) {
    final total = args.quiz.questionCount;
    final blank = total - args.answered;
    final closesIn = _closesIn();

    return Scaffold(
      backgroundColor: AppColors.ground,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 40, 24, 26),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 52,
                height: 52,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: AppColors.accentTint,
                  borderRadius: BorderRadius.circular(26),
                ),
                child: Icon(
                  args.auto ? Icons.schedule : Icons.check,
                  size: 26,
                  color: AppColors.accent,
                ),
              ),
              const SizedBox(height: 22),
              Text(args.auto ? 'Time ran out' : 'Submitted',
                  style: AppText.pageTitle),
              const SizedBox(height: 6),
              Text(
                args.auto
                    ? 'The deadline passed, so your attempt was submitted for you.'
                    : 'Your answers are in for ${args.quiz.title}.',
                style: AppText.bodyLarge,
              ),
              const SizedBox(height: 26),
              RowCard(
                children: [
                  FactRow(
                    label: 'Questions answered',
                    value: '${args.answered} of $total',
                  ),
                  if (args.auto)
                    FactRow(label: 'Left blank', value: '$blank'),
                  FactRow(
                    label: 'Submitted at',
                    value: args.auto
                        ? '${_hhmm(args.submittedAt)} · deadline'
                        : _hhmm(args.submittedAt),
                  ),
                  if (!args.auto)
                    FactRow(label: 'Quiz closes in', value: closesIn),
                ],
              ),
              const SizedBox(height: 18),
              Text(
                args.auto
                    ? 'Everything you had answered was saved. Your result '
                        'appears once the quiz closes for everyone.'
                    : 'Your result appears once the quiz closes for everyone. '
                        'Nothing is marked before then.',
                style: AppText.bodySmall,
              ),
              const Spacer(),
              FilledAction(
                label: 'Back to home',
                onPressed: () => Navigator.of(context)
                    .popUntil(ModalRoute.withName(Routes.studentHome)),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// The window closes at the deadline, whether or not this student is done.
  String _closesIn() {
    final closes = args.submittedAt.add(const Duration(minutes: 4));
    final left = closes.difference(args.submittedAt);
    return '${left.inMinutes} min';
  }

  static String _hhmm(DateTime d) =>
      '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
}
