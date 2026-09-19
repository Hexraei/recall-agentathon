import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/controllers.dart';
import '../../data/repositories.dart';
import '../../models/models.dart';
import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/buttons.dart';
import '../../widgets/shared/live_dot.dart';
import '../../widgets/shared/page_scaffold.dart';

/// The lobby's three states. One status block carries all of them; it is the
/// only thing that differs between the boards.
enum LobbyState { waiting, starting, connectionLost }

/// Screen 14 — Student Lobby.
///
/// A full-screen takeover: top left is Leave, with no confirmation, greyed
/// out while starting.
class StudentLobbyScreen extends StatefulWidget {
  const StudentLobbyScreen({super.key, required this.quiz});

  final Quiz quiz;

  @override
  State<StudentLobbyScreen> createState() => _StudentLobbyScreenState();
}

class _StudentLobbyScreenState extends State<StudentLobbyScreen> {
  LobbyState _state = LobbyState.waiting;
  int _others = 0;
  StreamSubscription<int>? _sub;
  Timer? _startTimer;

  @override
  void initState() {
    super.initState();
    _watch();
    // The teacher starts the quiz; this stands in for that push arriving.
    _startTimer = Timer(const Duration(seconds: 8), _start);
  }

  void _watch() {
    _sub?.cancel();
    _sub = context.read<AttemptRepository>().othersWaiting().listen(
      (n) => setState(() {
        _others = n;
        if (_state == LobbyState.connectionLost) _state = LobbyState.waiting;
      }),
      onError: (_) => setState(() => _state = LobbyState.connectionLost),
    );
  }

  Future<void> _start() async {
    if (!mounted) return;
    setState(() => _state = LobbyState.starting);
    await Future<void>.delayed(const Duration(milliseconds: 900));
    if (!mounted) return;

    final controller = AttemptController(
      context.read<AttemptRepository>(),
      widget.quiz,
    )..startClock();
    Navigator.of(context)
        .pushReplacementNamed(Routes.questionView, arguments: controller);
  }

  @override
  void dispose() {
    _sub?.cancel();
    _startTimer?.cancel();
    super.dispose();
  }

  static const _howItWorks = [
    'Answer the {n} questions in any order',
    'Change any answer until you submit',
    'No timer on individual questions',
  ];

  @override
  Widget build(BuildContext context) {
    final quiz = widget.quiz;
    final starting = _state == LobbyState.starting;

    return TakeoverScaffold(
      actionLabel: 'Leave',
      // Greyed out while starting: there is nothing to go back to mid-launch.
      actionEnabled: !starting,
      onAction: () => Navigator.of(context).pop(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 10),
          Text(
            quiz.week == null ? quiz.title : '${quiz.week} · ${quiz.title}',
            style: AppText.pageTitle,
          ),
          const SizedBox(height: 4),
          Text('${quiz.questionCount} questions · ${quiz.timeLimitMinutes} minutes',
              style: AppText.bodyLarge),
          const SizedBox(height: 26),
          _statusBlock(),
          const Spacer(),
          Text('HOW IT WORKS', style: AppText.sectionLabel),
          const SizedBox(height: 12),
          for (final line in _howItWorks) ...[
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.check, size: 17, color: AppColors.accent),
                  const SizedBox(width: 11),
                  Expanded(
                    child: Text(
                      line.replaceAll('{n}', '${quiz.questionCount}'),
                      style: AppText.bodySmall,
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _statusBlock() {
    switch (_state) {
      case LobbyState.waiting:
        return _Status(
          leading: const LiveDot(size: 9),
          title: 'Waiting to start',
          // A count only, never names.
          detail: '$_others others here too',
          background: AppColors.white,
          border: AppColors.hairline,
        );

      case LobbyState.starting:
        return const _Status(
          leading: SizedBox(
            width: 18,
            height: 18,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation<Color>(AppColors.accent),
            ),
          ),
          title: 'Starting',
          detail: 'Question 1 is loading',
          background: AppColors.accentTint,
          border: AppColors.accentBorder,
        );

      case LobbyState.connectionLost:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const _Status(
              leading: Icon(Icons.cloud_off_outlined,
                  size: 18, color: AppColors.grey1),
              title: 'Connection lost',
              detail: 'Trying again on its own',
              background: AppColors.neutralBand,
              border: AppColors.neutralBandBorder,
            ),
            const SizedBox(height: 12),
            OutlinedAction(label: 'Try again now', onPressed: _watch),
          ],
        );
    }
  }
}

class _Status extends StatelessWidget {
  const _Status({
    required this.leading,
    required this.title,
    required this.detail,
    required this.background,
    required this.border,
  });

  final Widget leading;
  final String title;
  final String detail;
  final Color background;
  final Color border;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 20),
      decoration: BoxDecoration(
        color: background,
        border: Border.all(color: border),
        borderRadius: AppRadii.containerR,
      ),
      child: Row(
        children: [
          SizedBox(width: 20, child: Center(child: leading)),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(title, style: AppText.rowTitle.copyWith(fontSize: 15.5)),
                const SizedBox(height: 3),
                Text(detail, style: AppText.rowSecondary),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
