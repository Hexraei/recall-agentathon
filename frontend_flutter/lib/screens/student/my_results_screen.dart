import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/repositories.dart';
import '../../models/models.dart';
import '../../routes.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/misc.dart';
import '../../widgets/shared/page_scaffold.dart';

/// My results — the index in front of screen 18.
///
/// "My results" used to open the most recent quiz directly, which left no way
/// of reaching any of the others from the dashboard. This lists every quiz
/// that has closed, newest first, and the result screen opens from a row.
///
/// It carries a count and a date per row but no score comparison of any kind,
/// the same rule the result screen itself follows.
class MyResultsScreen extends StatefulWidget {
  const MyResultsScreen({super.key});

  @override
  State<MyResultsScreen> createState() => _MyResultsScreenState();
}

class _MyResultsScreenState extends State<MyResultsScreen> {
  late Future<List<AttemptSummary>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<AttemptSummary>> _load() =>
      context.read<ResultsRepository>().myAttempts();

  void _reload() => setState(() {
    _future = _load();
  });

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<AttemptSummary>>(
      future: _future,
      builder: (context, snap) {
        final attempts = snap.data;
        final done = snap.connectionState == ConnectionState.done;

        return PageScaffold(
          title: 'My results',
          subtitle: attempts == null ? null : _countLine(attempts.length),
          backLabel: 'Back to home',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 18),
              if (!done)
                const LoadingState()
              else if (snap.hasError || attempts == null)
                ErrorState(
                  message: "We couldn't load your results.",
                  onRetry: _reload,
                )
              else if (attempts.isEmpty)
                const InfoBand(
                  text:
                      'Your results appear here once a quiz you took has '
                      'closed.',
                )
              else
                ..._list(context, attempts),
            ],
          ),
        );
      },
    );
  }

  List<Widget> _list(BuildContext context, List<AttemptSummary> attempts) {
    return [
      const SectionLabel('Pick a quiz', top: 0),
      Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Text(
          'Most recent first. Open one to see every question.',
          style: AppText.bodySmall,
        ),
      ),
      RowCard(
        children: [
          for (final a in attempts)
            FactRow(
              label: a.quiz.title,
              secondary: a.quiz.week == null
                  ? _longDate(a.takenOn)
                  : '${a.quiz.week} · ${_longDate(a.takenOn)}',
              value: '${a.correct} of ${a.total}',
              chevron: true,
              onTap: () => Navigator.of(context).pushNamed(
                Routes.quizResult,
                arguments: QuizResultArgs(
                  quizId: a.quiz.id,
                  backLabel: 'Back to results',
                ),
              ),
            ),
        ],
      ),
    ];
  }

  static String _countLine(int n) =>
      n == 1 ? '1 quiz taken' : '$n quizzes taken';

  static String _longDate(DateTime d) {
    const months = [
      'January',
      'February',
      'March',
      'April',
      'May',
      'June',
      'July',
      'August',
      'September',
      'October',
      'November',
      'December',
    ];
    return '${d.day} ${months[d.month - 1]}';
  }
}
