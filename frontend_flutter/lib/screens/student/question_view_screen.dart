import 'package:flutter/material.dart';

import '../../data/controllers.dart';
import '../../models/models.dart';
import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/buttons.dart';
import '../../widgets/shared/countdown.dart';
import '../../widgets/shared/misc.dart';
import '../../widgets/shared/option_card.dart';
import '../../widgets/shared/page_scaffold.dart';

/// Screen 15 — Question View.
///
/// One header holding the countdown and the position; the question in the
/// serif; four option cards; Previous and Next as equal-width buttons with a
/// quieter "Review & submit" link beneath.
///
/// Absent by design: per-question countdown, right/wrong feedback, points,
/// score, any indication of how others are doing.
///
/// States: unanswered; answered; first question, with Previous greyed; last
/// question, where Next becomes "Review & submit"; deadline near, where the
/// header turns red-tinted; auto-submitting, an overlay stating the time is
/// up and naming how many answers are being submitted.
class QuestionViewScreen extends StatefulWidget {
  const QuestionViewScreen({super.key, required this.controller});

  /// Created by the lobby, or by Join on late entry, and handed over here.
  /// Ownership comes with it: this screen sits under Review & Submit for the
  /// whole attempt, so it is what outlives the flow and disposes it. Without
  /// that the one-second ticker would keep running for the life of the app.
  final AttemptController controller;

  @override
  State<QuestionViewScreen> createState() => _QuestionViewScreenState();
}

class _QuestionViewScreenState extends State<QuestionViewScreen> {
  AttemptController get controller => widget.controller;

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  void _openReview(BuildContext context) => Navigator.of(
    context,
  ).pushNamed(Routes.reviewSubmit, arguments: controller);

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: controller,
      builder: (context, _) {
        final q = controller.current;
        final chosen = controller.attempt.answers[q.id];

        return PopScope(
          // There is no way out of an attempt but through it.
          canPop: false,
          child: TakeoverScaffold(
            actionLabel: 'Exit quiz',
            onAction: () => _openReview(context),
            scrollable: true,
            overlay: controller.autoSubmitting
                ? NoticeOverlay(
                    title: 'Time is up',
                    message:
                        'Submitting the ${controller.answeredCount} '
                        'answer${controller.answeredCount == 1 ? '' : 's'} you have.',
                  )
                : null,
            bottomBar: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: OutlinedAction(
                        label: 'Previous',
                        // Greys out on question 1 rather than disappearing,
                        // so the pair keeps its shape.
                        onPressed: controller.isFirst
                            ? null
                            : controller.previous,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledAction(
                        label: controller.isLast ? 'Review & submit' : 'Next',
                        onPressed: controller.isLast
                            ? () => _openReview(context)
                            : controller.next,
                      ),
                    ),
                  ],
                ),
                if (!controller.isLast)
                  TextAction(
                    label: 'Review & submit',
                    onPressed: () => _openReview(context),
                  ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 4),
                Countdown(
                  remaining: controller.remaining,
                  trailing: Text(
                    'Question ${controller.index + 1} of ${controller.total}',
                    style: AppText.rowTitle.copyWith(
                      fontSize: 13,
                      color: AppColors.grey1,
                    ),
                  ),
                ),
                const SizedBox(height: 26),
                Text(q.text, style: AppText.questionStem),
                const SizedBox(height: 22),
                for (var i = 0; i < 4; i++) ...[
                  if (i > 0) const SizedBox(height: 10),
                  OptionCard(
                    letter: Question.letters[i],
                    text: q.options[i],
                    state: chosen == i
                        ? OptionState.selected
                        : OptionState.unselected,
                    // Answers stay editable until submit or auto-submit.
                    onTap: controller.autoSubmitting
                        ? null
                        : () => controller.choose(i),
                  ),
                ],
                const SizedBox(height: 20),
              ],
            ),
          ),
        );
      },
    );
  }
}
