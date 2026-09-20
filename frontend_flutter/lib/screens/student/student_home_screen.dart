import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/controllers.dart';
import '../../data/repositories.dart';
import '../../models/models.dart';
import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/dashboard.dart';
import '../../widgets/shared/misc.dart';
import '../../widgets/shared/nav_list.dart';

/// Screen 12 — Student Home Dashboard.
///
/// Mirrors the teacher's so the two read as one app. The Latest result card
/// carries no rank, no comparison and no next step.
///
/// States: default; a quiz open, which adds a pulsing banner above the Join
/// card; first run, where an invitation card explains the steps and the two
/// rows grey out.
class StudentHomeScreen extends StatefulWidget {
  const StudentHomeScreen({super.key});

  @override
  State<StudentHomeScreen> createState() => _StudentHomeScreenState();
}

class _StudentHomeScreenState extends State<StudentHomeScreen> {
  late Future<_StudentHomeData> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_StudentHomeData> _load() async {
    final r = context.read<ResultsRepository>();
    final attempts = context.read<AttemptRepository>();

    // The banner no longer decides for itself what is open. It asks, so it
    // cannot advertise a quiz that has closed or one already submitted.
    final (history, open) = await (r.myAttempts(), attempts.openQuiz()).wait;

    return _StudentHomeData(
      attempts: history,
      latest: history.isEmpty ? null : history.first,
      openQuiz: open,
    );
  }

  void _reload() => setState(() {
    _future = _load();
  });

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthController>().user;

    return Scaffold(
      backgroundColor: AppColors.ground,
      body: SafeArea(
        child: RefreshIndicator(
          color: AppColors.accent,
          onRefresh: () async => _reload(),
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DashboardHeader(
                  greeting: DashboardHeader.greetingForHour(
                    DateTime.now().hour,
                  ),
                  name: user?.name ?? 'Student',
                  onSignOut: () async {
                    await context.read<AuthController>().signOut();
                    if (context.mounted) {
                      Navigator.of(
                        context,
                      ).pushNamedAndRemoveUntil(Routes.auth, (_) => false);
                    }
                  },
                ),
                const SizedBox(height: 24),
                FutureBuilder<_StudentHomeData>(
                  future: _future,
                  builder: (context, snap) {
                    if (snap.connectionState != ConnectionState.done) {
                      return const LoadingState();
                    }
                    if (snap.hasError) {
                      return ErrorState(
                        message: "We couldn't load your home screen.",
                        onRetry: _reload,
                      );
                    }
                    final d = snap.data!;
                    return d.attempts.isEmpty
                        ? _firstRun(context)
                        : _populated(context, d);
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _firstRun(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        InvitationCard(
          title: 'Join your first quiz',
          body:
              'Your teacher will share a PIN. Type it in, wait for them to '
              'start, then answer in any order and submit before time runs out.',
          actionLabel: 'Join a quiz',
          onAction: () => Navigator.of(context).pushNamed(Routes.join),
        ),
        const SizedBox(height: 20),
        const NavList(
          rows: [
            NavRow(
              icon: Icons.assignment_outlined,
              title: 'My results',
              secondary: 'Appear after your first quiz closes',
              enabled: false,
            ),
            NavRow(
              icon: Icons.trending_up,
              title: 'My performance',
              secondary: 'Builds up as you take quizzes',
              enabled: false,
            ),
          ],
        ),
      ],
    );
  }

  Widget _populated(BuildContext context, _StudentHomeData d) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (d.openQuiz != null) ...[
          LiveBanner(
            title: 'Open now · ${d.openQuiz!.quiz.title}',
            detail: d.openQuiz!.quiz.summaryLine,
            // The PIN travels with the banner, so tapping something that
            // says "Open now" does not ask for it all over again.
            onTap: () => Navigator.of(context)
                .pushNamed(Routes.join, arguments: d.openQuiz!.pin)
                .then((_) => _reload()),
          ),
          const SizedBox(height: 12),
        ],
        PrimaryActionCard(
          icon: Icons.login,
          title: 'Join a quiz',
          subtitle: 'Type the PIN your teacher reads out',
          onTap: () => Navigator.of(context).pushNamed(Routes.join),
        ),
        const SizedBox(height: 16),
        NavList(
          rows: [
            NavRow(
              icon: Icons.assignment_outlined,
              title: 'My results',
              secondary: d.attempts.length == 1
                  ? '1 quiz taken'
                  : '${d.attempts.length} quizzes taken',
              // The list comes first, so any past quiz can be reached from
              // here and not only the most recent one.
              onTap: () => Navigator.of(context).pushNamed(Routes.myResults),
            ),
            NavRow(
              icon: Icons.trending_up,
              title: 'My performance',
              secondary: 'Across ${d.attempts.length} quizzes',
              onTap: () =>
                  Navigator.of(context).pushNamed(Routes.myPerformance),
            ),
          ],
        ),
        if (d.latest != null) ...[
          const SectionLabel('Latest result'),
          _LatestResult(attempt: d.latest!),
        ],
      ],
    );
  }
}

class _LatestResult extends StatelessWidget {
  const _LatestResult({required this.attempt});

  final AttemptSummary attempt;

  @override
  Widget build(BuildContext context) {
    final quiz = attempt.quiz;
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Expanded(
                child: Text(
                  quiz.week == null
                      ? quiz.title
                      : '${quiz.week} · ${quiz.title}',
                  style: AppText.rowTitle.copyWith(
                    fontSize: 16,
                    letterSpacing: -0.1,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Text(_shortDate(attempt.takenOn), style: AppText.rowSecondary),
            ],
          ),
          const SizedBox(height: 8),
          // A count, not a rank: nothing here compares this student to anyone.
          Text(
            '${attempt.correct} of ${attempt.total} answered correctly.',
            style: AppText.bodySmall,
          ),
          const SizedBox(height: 10),
          GestureDetector(
            onTap: () => Navigator.of(context).pushNamed(
              Routes.quizResult,
              arguments: QuizResultArgs(quizId: quiz.id),
            ),
            child: Text(
              'See full result',
              style: AppText.rowTitle.copyWith(
                fontSize: 13.5,
                color: AppColors.accent,
              ),
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
    return '${days[d.weekday - 1]}, ${d.day} ${months[d.month - 1]}';
  }
}

class _StudentHomeData {
  const _StudentHomeData({
    required this.attempts,
    required this.latest,
    required this.openQuiz,
  });

  final List<AttemptSummary> attempts;
  final AttemptSummary? latest;
  final OpenQuiz? openQuiz;
}
