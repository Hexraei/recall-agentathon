import 'package:flutter/material.dart';

import '../../data/controllers.dart';
import '../../models/models.dart';
import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/buttons.dart';
import '../../widgets/shared/countdown.dart';
import '../../widgets/shared/live_dot.dart';
import '../../widgets/shared/misc.dart';
import '../../widgets/shared/page_scaffold.dart';
import '../../widgets/shared/sheets.dart';

/// Screen 07 — Live Monitor.
///
/// Top left is "Exit quiz", which opens the end-quiz confirmation,
/// auto-submits every open attempt and closes the window. There is
/// deliberately no way to leave the monitor with the quiz still running.
///
/// States: running; deadline near; everyone submitted; confirm ending early;
/// closed.
class LiveMonitorScreen extends StatelessWidget {
  const LiveMonitorScreen({super.key, required this.controller});

  final HostSessionController controller;

  Future<void> _confirmEnd(BuildContext context, int openAttempts) async {
    final end = await showAppSheet<bool>(
      context: context,
      builder: (context) => ConfirmSheet(
        title: 'End the quiz now?',
        body: '$openAttempts attempt${openAttempts == 1 ? ' is' : 's are'} '
            'still open. Ending now submits each of them exactly as '
            'it stands, unanswered questions included.',
        confirmLabel: 'End it now',
        cancelLabel: 'Keep it running',
        destructive: true,
      ),
    );
    if (end == true) await controller.close();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: controller,
      builder: (context, _) {
        final quiz = controller.quiz;
        final rows = controller.rows;
        final closed = controller.phase == HostPhase.closed;
        final everyone = controller.phase == HostPhase.everyoneSubmitted;
        final openAttempts = rows.length - controller.submitted;

        return PopScope(
          // Leaving is only possible by ending the quiz, so the system back
          // gesture routes into the same confirmation as Exit quiz.
          canPop: closed,
          onPopInvokedWithResult: (didPop, _) {
            if (!didPop && !closed) _confirmEnd(context, openAttempts);
          },
          child: TakeoverScaffold(
            actionLabel: closed ? 'Done' : 'Exit quiz',
            onAction: closed
                ? () => Navigator.of(context)
                    .popUntil(ModalRoute.withName(Routes.teacherHome))
                : () => _confirmEnd(context, openAttempts),
            scrollable: true,
            bottomBar: _bottomBar(context, closed, everyone, openAttempts),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 10),
                Text(
                  quiz.week == null ? quiz.title : '${quiz.week} · ${quiz.title}',
                  style: AppText.sectionTitle,
                ),
                const SizedBox(height: 6),
                Row(
                  children: [
                    if (!closed) ...[
                      const LiveDot(),
                      const SizedBox(width: 7),
                      Text('Running', style: AppText.bodySmall),
                    ] else ...[
                      Container(
                        width: 7,
                        height: 7,
                        decoration: const BoxDecoration(
                          color: AppColors.grey4,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 7),
                      Text('Closed at ${_hhmm(DateTime.now())}',
                          style: AppText.bodySmall),
                    ],
                  ],
                ),
                const SizedBox(height: 18),
                if (closed)
                  _ClosedCard(minutes: quiz.timeLimitMinutes)
                else
                  Countdown(
                    remaining: controller.remaining,
                    variant: CountdownVariant.hero,
                    totalLabel: 'of ${quiz.timeLimitMinutes} minutes',
                    nearThreshold: const Duration(minutes: 2),
                  ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: StatTile(
                          figure: '${rows.length}', label: 'Joined'),
                    ),
                    const SizedBox(width: 8),
                    if (closed)
                      Expanded(
                        child: StatTile(
                            figure: '${controller.submitted}',
                            label: 'Submitted'),
                      )
                    else
                      Expanded(
                        child: StatTile(
                            figure: '${controller.answering}',
                            label: 'Answering'),
                      ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: closed
                          ? StatTile(
                              figure: '${controller.autoSubmitted}',
                              label: 'Auto-submitted')
                          : StatTile(
                              figure: '${controller.submitted}',
                              label: 'Submitted'),
                    ),
                  ],
                ),
                const SectionLabel('Students', top: 20, bottom: 8),
                if (rows.isEmpty)
                  const DashedSlot(
                    text: 'Progress appears here as students start answering.',
                    height: 88,
                  )
                else
                  RowCard(
                    children: [for (final r in rows) _ProgressRow(row: r)],
                  ),
                const SizedBox(height: 12),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _bottomBar(
      BuildContext context, bool closed, bool everyone, int openAttempts) {
    if (closed) {
      return FilledAction(
        label: 'See class results',
        onPressed: () => Navigator.of(context)
            .pushReplacementNamed(Routes.quizResults, arguments: controller.quiz.id),
      );
    }
    if (everyone) {
      // Once everyone is in, the end-early button is replaced: there is
      // nothing left to interrupt.
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'All ${controller.rows.length} students have submitted. Closing '
            'now releases results to everyone.',
            textAlign: TextAlign.center,
            style: AppText.caption.copyWith(fontSize: 12.5),
          ),
          const SizedBox(height: 10),
          FilledAction(
            label: 'Close the quiz now',
            onPressed: controller.close,
          ),
          TextAction(
            label: 'Let it run to 0:00',
            color: AppColors.grey2,
            onPressed: () {},
          ),
        ],
      );
    }
    return OutlinedAction(
      label: 'End the quiz now',
      destructive: true,
      onPressed: () => _confirmEnd(context, openAttempts),
    );
  }

  static String _hhmm(DateTime d) =>
      '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
}

class _ClosedCard extends StatelessWidget {
  const _ClosedCard({required this.minutes});

  final int minutes;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 20),
      child: Column(
        children: [
          Text('WINDOW CLOSED', style: AppText.sectionLabel),
          const SizedBox(height: 8),
          Text('Ran $minutes minutes', style: AppText.resultFigure),
          const SizedBox(height: 6),
          Text(
            'Results are now visible to every student who took it.',
            textAlign: TextAlign.center,
            style: AppText.caption.copyWith(fontSize: 12.5),
          ),
        ],
      ),
    );
  }
}

class _ProgressRow extends StatelessWidget {
  const _ProgressRow({required this.row});

  final StudentProgress row;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
      child: Row(
        children: [
          InitialsChip(initials: row.student.initials),
          const SizedBox(width: 11),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(row.student.name,
                    style: AppText.optionText.copyWith(
                        fontWeight: FontWeight.w500, color: AppColors.ink)),
                const SizedBox(height: 1),
                Text(row.progressLine, style: AppText.rowSecondary),
              ],
            ),
          ),
          if (row.stage == AttemptStage.submitted) ...[
            const SizedBox(width: 10),
            const Icon(Icons.check, size: 17, color: AppColors.accent),
          ],
        ],
      ),
    );
  }
}
