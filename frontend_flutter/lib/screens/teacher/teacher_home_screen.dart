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

/// Screen 03 — Teacher Home Dashboard.
///
/// The hub: every flow is entered from here and returns to it. The Review
/// findings badge is an accent pill, not red — it is a queue count, not an
/// error.
///
/// States: default; nothing to review, with the badge gone; first run, where
/// the invitation card becomes the primary and all four entry points grey out
/// with a line saying what unlocks them. Loading and error are added here:
/// the canvas never drew them, but the screen fetches data.
class TeacherHomeScreen extends StatefulWidget {
  const TeacherHomeScreen({super.key});

  @override
  State<TeacherHomeScreen> createState() => _TeacherHomeScreenState();
}

class _TeacherHomeScreenState extends State<TeacherHomeScreen> {
  late Future<_HomeData> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_HomeData> _load() async {
    // Both repositories are read before the first await, so nothing touches
    // the BuildContext once this has gone asynchronous.
    final quizRepo = context.read<QuizRepository>();
    final results = context.read<ResultsRepository>();

    // These three do not depend on one another, so they are fetched
    // together rather than one after the next.
    final (quizzes, findings, averages) = await (
      quizRepo.myQuizzes(),
      results.findings(),
      results.classAverages(),
    ).wait;

    ClassQuizResult? recent;
    final lastRun = quizzes.where((q) => q.hasRun).toList()
      ..sort((a, b) => b.lastRun!.compareTo(a.lastRun!));
    if (lastRun.isNotEmpty) {
      recent = await results.classResult(lastRun.first.id);
    }

    return _HomeData(
      quizzes: quizzes,
      pendingFindings: findings
          .where((f) => f.status == FindingStatus.awaitingReview)
          .length,
      quizzesClosed: averages.length,
      recent: recent,
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
                  name: user?.name ?? 'Teacher',
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
                FutureBuilder<_HomeData>(
                  future: _future,
                  builder: (context, snap) {
                    if (snap.connectionState != ConnectionState.done) {
                      return const LoadingState(message: 'Loading your class');
                    }
                    if (snap.hasError) {
                      return ErrorState(
                        message:
                            "We couldn't load your dashboard. Nothing has changed.",
                        onRetry: _reload,
                      );
                    }
                    final d = snap.data!;
                    return d.quizzes.isEmpty
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
          title: 'Build your first quiz',
          body:
              'Write four-option questions, set one deadline for the whole '
              'attempt, then host it and read the class PIN aloud.',
          actionLabel: 'Create a quiz',
          onAction: () => Navigator.of(
            context,
          ).pushNamed(Routes.quizBuilder).then((_) => _reload()),
        ),
        const SizedBox(height: 20),
        const PrimaryActionCard(
          icon: Icons.play_circle_outline,
          title: 'Host a quiz',
          subtitle: 'Nothing saved to host yet',
          enabled: false,
        ),
        const SizedBox(height: 10),
        const NavList(
          rows: [
            NavRow(
              icon: Icons.description_outlined,
              title: 'My quizzes',
              secondary: 'Empty',
              enabled: false,
            ),
            NavRow(
              icon: Icons.bar_chart,
              title: 'Class analytics',
              secondary: 'Opens once a quiz has run',
              enabled: false,
            ),
            NavRow(
              icon: Icons.check_circle_outline,
              title: 'Review findings',
              secondary: 'Needs a few quizzes before patterns appear',
              enabled: false,
            ),
          ],
        ),
      ],
    );
  }

  Widget _populated(BuildContext context, _HomeData d) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        PrimaryActionCard(
          icon: Icons.play_circle_outline,
          title: 'Host a quiz',
          subtitle: 'Open a lobby and share the PIN',
          onTap: () => Navigator.of(context).pushNamed(
            Routes.myQuizzes,
            arguments: const MyQuizzesArgs(hosting: true),
          ),
        ),
        const SizedBox(height: 16),
        NavList(
          rows: [
            NavRow(
              icon: Icons.description_outlined,
              title: 'My quizzes',
              secondary: '${d.quizzes.length} saved',
              onTap: () => Navigator.of(
                context,
              ).pushNamed(Routes.myQuizzes).then((_) => _reload()),
            ),
            NavRow(
              icon: Icons.bar_chart,
              title: 'Class analytics',
              secondary: 'Trends across ${d.quizzesClosed} quizzes',
              onTap: () =>
                  Navigator.of(context).pushNamed(Routes.classAnalytics),
            ),
            NavRow(
              icon: Icons.check_circle_outline,
              title: 'Review findings',
              secondary: 'Confirm before students see them',
              // The badge disappears entirely when the queue is empty.
              badge: d.pendingFindings > 0 ? '${d.pendingFindings}' : null,
              onTap: () => Navigator.of(
                context,
              ).pushNamed(Routes.reviewFindings).then((_) => _reload()),
            ),
          ],
        ),
        if (d.recent != null) ...[
          const SectionLabel('Recent activity'),
          _RecentActivity(result: d.recent!),
        ],
      ],
    );
  }
}

class _RecentActivity extends StatelessWidget {
  const _RecentActivity({required this.result});

  final ClassQuizResult result;

  @override
  Widget build(BuildContext context) {
    final quiz = result.quiz;
    final worst = result.breakdowns.isEmpty ? null : result.breakdowns.first;
    final ran = quiz.lastRun;

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
              Text(
                ran == null ? '' : _shortDate(ran),
                style: AppText.rowSecondary,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '${result.tookIt} of ${result.classSize} students took it.'
            '${worst == null ? '' : ' Lowest-scoring question: ${_lower(worst.question.text)}'}',
            style: AppText.bodySmall,
          ),
          const SizedBox(height: 10),
          GestureDetector(
            onTap: () => Navigator.of(
              context,
            ).pushNamed(Routes.quizResults, arguments: quiz.id),
            child: Text(
              'See full results',
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

  static String _lower(String s) =>
      s.isEmpty ? s : s[0].toLowerCase() + s.substring(1);

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

class _HomeData {
  const _HomeData({
    required this.quizzes,
    required this.pendingFindings,
    required this.quizzesClosed,
    required this.recent,
  });

  final List<Quiz> quizzes;
  final int pendingFindings;
  final int quizzesClosed;
  final ClassQuizResult? recent;
}
