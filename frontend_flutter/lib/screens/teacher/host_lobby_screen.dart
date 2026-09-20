import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/controllers.dart';
import '../../data/repositories.dart';
import '../../models/models.dart';
import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/buttons.dart';
import '../../widgets/shared/live_dot.dart';
import '../../widgets/shared/misc.dart';
import '../../widgets/shared/page_scaffold.dart';

/// Screen 06 — Host Lobby.
///
/// A full-screen takeover: top left is Cancel, not a back chevron.
///
/// States: nobody joined, with Start disabled and a dashed placeholder;
/// students joining; starting, with the action busy and a line saying
/// question 1 is being sent.
///
/// The helper line under Start changes with state rather than the button
/// changing label, and avoids mentioning latecomers, since late entry is
/// undecided.
class HostLobbyScreen extends StatefulWidget {
  const HostLobbyScreen({super.key, required this.quiz});

  final Quiz quiz;

  @override
  State<HostLobbyScreen> createState() => _HostLobbyScreenState();
}

class _HostLobbyScreenState extends State<HostLobbyScreen> {
  late final HostSessionController _c;

  /// The monitor takes ownership of the controller when the quiz starts, so
  /// this screen must not dispose it on the way out.
  bool _handedOff = false;

  @override
  void initState() {
    super.initState();
    _c = HostSessionController(context.read<SessionRepository>(), widget.quiz)
      ..open();
  }

  @override
  void dispose() {
    if (!_handedOff) _c.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    await _c.start();
    if (!mounted) return;
    // The monitor takes over the same controller, so the roster and the
    // countdown carry across without a refetch.
    _handedOff = true;
    Navigator.of(
      context,
    ).pushReplacementNamed(Routes.liveMonitor, arguments: _c);
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _c,
      builder: (context, _) {
        final joined = _c.joined;
        final starting = _c.phase == HostPhase.starting;

        return TakeoverScaffold(
          actionLabel: 'Cancel',
          actionEnabled: !starting,
          onAction: () => Navigator.of(context).pop(),
          scrollable: true,
          bottomBar: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              FilledAction(
                label: 'Start the quiz',
                busy: starting,
                onPressed: joined.isEmpty || starting ? null : _start,
              ),
              const SizedBox(height: 10),
              Text(
                starting
                    ? 'Sending question 1 to everyone who joined.'
                    : joined.isEmpty
                    ? 'You can start once at least one student has joined.'
                    : 'The ${widget.quiz.timeLimitMinutes} minutes begins '
                          'for everyone the moment you start.',
                textAlign: TextAlign.center,
                style: AppText.caption.copyWith(fontSize: 12.5),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 10),
              Text(
                widget.quiz.week == null
                    ? widget.quiz.title
                    : '${widget.quiz.week} · ${widget.quiz.title}',
                style: AppText.sectionTitle,
              ),
              const SizedBox(height: 4),
              Text.rich(
                TextSpan(
                  style: AppText.bodySmall.copyWith(color: AppColors.grey2),
                  children: [
                    TextSpan(
                      text: '${widget.quiz.questionCount} questions',
                      style: AppText.bodySmall.copyWith(
                        fontWeight: FontWeight.w600,
                        color: AppColors.grey1,
                      ),
                    ),
                    const TextSpan(text: ' · '),
                    TextSpan(
                      text: '${widget.quiz.timeLimitMinutes} minutes',
                      style: AppText.bodySmall.copyWith(
                        fontWeight: FontWeight.w600,
                        color: AppColors.grey1,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              _PinCard(pin: _c.pin),
              const SizedBox(height: 20),
              Row(
                children: [
                  const LiveDot(),
                  const SizedBox(width: 8),
                  Text(
                    '${joined.length} joined',
                    style: AppText.rowTitle.copyWith(fontSize: 14),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (joined.isEmpty)
                const DashedSlot(
                  text: 'Students who have joined can be seen here.',
                  height: 96,
                )
              else
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (var i = 0; i < joined.length; i++)
                      _StudentChip(
                        student: joined[i],
                        // The most recent arrival is tinted, so a teacher
                        // watching the list sees who just appeared.
                        emphasised: i == joined.length - 1,
                      ),
                  ],
                ),
              const SizedBox(height: 24),
            ],
          ),
        );
      },
    );
  }
}

class _PinCard extends StatelessWidget {
  const _PinCard({required this.pin});

  final String pin;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('JOIN PIN', style: AppText.sectionLabel),
          const SizedBox(height: 10),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            // Set in the sans at 52px: the PIN is read aloud and typed, not
            // read as a heading.
            child: Text(pin.isEmpty ? '— — —' : pin, style: AppText.pinDisplay),
          ),
          const SizedBox(height: 10),
          Text(
            'Students open Recall, tap Join a quiz, and type this.',
            style: AppText.caption.copyWith(fontSize: 12.5),
          ),
        ],
      ),
    );
  }
}

class _StudentChip extends StatelessWidget {
  const _StudentChip({required this.student, required this.emphasised});

  final AppUser student;
  final bool emphasised;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(5, 5, 12, 5),
      decoration: BoxDecoration(
        color: emphasised ? AppColors.accentTint : AppColors.white,
        border: Border.all(
          color: emphasised ? AppColors.accentBorder : AppColors.hairline,
        ),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          InitialsChip(
            initials: student.initials,
            size: 26,
            emphasised: emphasised,
          ),
          const SizedBox(width: 8),
          Text(
            student.name,
            style: AppText.bodySmall.copyWith(color: AppColors.ink),
          ),
        ],
      ),
    );
  }
}
