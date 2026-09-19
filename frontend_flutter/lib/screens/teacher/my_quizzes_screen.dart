import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/repositories.dart';
import '../../models/models.dart';
import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/buttons.dart';
import '../../widgets/shared/misc.dart';
import '../../widgets/shared/page_scaffold.dart';
import '../../widgets/shared/sheets.dart';

/// Screen 04 — My Quizzes.
///
/// States: populated; confirm delete, as a bottom sheet over a dimmed list
/// with a red Delete and an outlined "Keep it"; empty. Loading and error are
/// added, since the screen fetches.
class MyQuizzesScreen extends StatefulWidget {
  const MyQuizzesScreen({super.key, this.hosting = false});

  /// Reached from Host a quiz rather than from My quizzes, so a tap on a row
  /// opens the lobby instead of the builder.
  final bool hosting;

  @override
  State<MyQuizzesScreen> createState() => _MyQuizzesScreenState();
}

class _MyQuizzesScreenState extends State<MyQuizzesScreen> {
  late Future<List<Quiz>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<QuizRepository>().myQuizzes();
  }

  void _reload() => setState(() {
    _future = context.read<QuizRepository>().myQuizzes();
  });

  Future<void> _confirmDelete(Quiz quiz) async {
    final confirmed = await showAppSheet<bool>(
      context: context,
      builder: (context) => ConfirmSheet(
        title: 'Delete “${quiz.title}”?',
        // The cascade is an assumption in the design, so the copy says it
        // out loud rather than deleting quietly.
        body:
            'Its results, and everything the analysis built from it, go with '
            "it. This can't be undone.",
        confirmLabel: 'Delete quiz',
        cancelLabel: 'Keep it',
        destructive: true,
      ),
    );
    if (confirmed != true || !mounted) return;
    await context.read<QuizRepository>().deleteQuiz(quiz.id);
    if (mounted) _reload();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Quiz>>(
      future: _future,
      builder: (context, snap) {
        final quizzes = snap.data ?? const <Quiz>[];
        final done = snap.connectionState == ConnectionState.done;

        return PageScaffold(
          title: 'My quizzes',
          subtitle: done ? '${quizzes.length} saved' : null,
          backLabel: 'Back to dashboard',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 18),
              if (!done)
                const LoadingState()
              else if (snap.hasError)
                ErrorState(
                  message: "We couldn't load your quizzes.",
                  onRetry: _reload,
                )
              else if (quizzes.isEmpty)
                const _EmptyQuizzes()
              else ...[
                _NewQuizButton(onTap: () => _openBuilder(null)),
                const SizedBox(height: 14),
                RowCard(
                  children: [
                    for (final q in quizzes)
                      _QuizRow(
                        quiz: q,
                        onOpen: () =>
                            widget.hosting ? _openLobby(q) : _openBuilder(q),
                        onHost: () => _openLobby(q),
                        onDelete: () => _confirmDelete(q),
                      ),
                  ],
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  void _openBuilder(Quiz? quiz) => Navigator.of(
    context,
  ).pushNamed(Routes.quizBuilder, arguments: quiz).then((_) => _reload());

  void _openLobby(Quiz quiz) =>
      Navigator.of(context).pushNamed(Routes.hostLobby, arguments: quiz);
}

class _NewQuizButton extends StatelessWidget {
  const _NewQuizButton({this.onTap});

  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.white,
      borderRadius: AppRadii.controlR,
      child: InkWell(
        onTap: onTap,
        borderRadius: AppRadii.controlR,
        child: Container(
          height: AppMetrics.control,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            border: Border.all(color: AppColors.hairlineStrong),
            borderRadius: AppRadii.controlR,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.add, size: 18, color: AppColors.accent),
              const SizedBox(width: 8),
              Text(
                'New quiz',
                style: AppText.button.copyWith(
                  fontSize: 15,
                  color: AppColors.accent,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _QuizRow extends StatelessWidget {
  const _QuizRow({
    required this.quiz,
    required this.onOpen,
    required this.onHost,
    required this.onDelete,
  });

  final Quiz quiz;
  final VoidCallback onOpen;
  final VoidCallback onHost;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 13, 10, 13),
      child: Row(
        children: [
          Expanded(
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: onOpen,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    quiz.week == null
                        ? quiz.title
                        : '${quiz.week} · ${quiz.title}',
                    style: AppText.rowTitle.copyWith(fontSize: 15.5),
                  ),
                  const SizedBox(height: 3),
                  Text(quiz.summaryLine, style: AppText.rowSecondary),
                  const SizedBox(height: 2),
                  Text(
                    quiz.hasRun
                        ? 'Ran ${_shortDate(quiz.lastRun!)}'
                        : 'Not run yet',
                    style: AppText.captionSmall.copyWith(
                      color: AppColors.grey4,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 10),
          PillAction(label: 'Host', onPressed: onHost),
          SizedBox(
            width: 44,
            height: 44,
            child: PopupMenuButton<String>(
              tooltip: 'More options for ${quiz.title}',
              icon: const Icon(
                Icons.more_vert,
                size: 20,
                color: AppColors.grey3,
              ),
              color: AppColors.white,
              shape: RoundedRectangleBorder(
                borderRadius: AppRadii.controlR,
                side: const BorderSide(color: AppColors.hairline),
              ),
              onSelected: (v) => v == 'edit' ? onOpen() : onDelete(),
              itemBuilder: (context) => [
                PopupMenuItem(
                  value: 'edit',
                  child: Text('Edit', style: AppText.bodySmall),
                ),
                PopupMenuItem(
                  value: 'delete',
                  child: Text(
                    'Delete',
                    style: AppText.bodySmall.copyWith(color: AppColors.red),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  static String _shortDate(DateTime d) {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
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
    return '${days[d.weekday - 1]} ${d.day} ${months[d.month - 1]}';
  }
}

class _EmptyQuizzes extends StatelessWidget {
  const _EmptyQuizzes();

  static const _steps = [
    'Name the quiz. Set one time limit, in minutes, for the whole quiz.',
    'Add a question with four options. Mark the correct one. Repeat.',
    'Save it. It stays here until you host it.',
  ];

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('No quizzes yet', style: AppText.sheetTitle),
          const SizedBox(height: 8),
          Text(
            'Three steps and the first one is ready to host.',
            style: AppText.bodySmall,
          ),
          const SizedBox(height: 18),
          for (var i = 0; i < _steps.length; i++) ...[
            if (i > 0) const SizedBox(height: 14),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 22,
                  height: 22,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: AppColors.accentTint,
                    borderRadius: BorderRadius.circular(11),
                  ),
                  child: Text(
                    '${i + 1}',
                    style: AppText.captionSmall.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppColors.accent,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(child: Text(_steps[i], style: AppText.bodySmall)),
              ],
            ),
          ],
          const SizedBox(height: 22),
          FilledAction(
            label: 'Create your first quiz',
            onPressed: () =>
                Navigator.of(context).pushNamed(Routes.quizBuilder),
          ),
        ],
      ),
    );
  }
}
