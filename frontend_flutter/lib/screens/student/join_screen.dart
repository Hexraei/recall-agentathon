import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../data/controllers.dart';
import '../../data/repositories.dart';
import '../../models/models.dart';
import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/buttons.dart';
import '../../widgets/shared/countdown.dart';
import '../../widgets/shared/page_scaffold.dart';

/// Screen 13 — Join.
///
/// A full-screen takeover: top left is Cancel. One large PIN field on a
/// numeric keyboard, with Join directly beneath it so the keyboard never
/// covers it. No nickname is ever asked for.
///
/// States: idle; PIN typed; checking; PIN not found — the only red state on
/// the screen; quiz closed and already submitted, both in the neutral band
/// because neither is a mistake; quiz already started.
class JoinScreen extends StatefulWidget {
  const JoinScreen({super.key});

  @override
  State<JoinScreen> createState() => _JoinScreenState();
}

class _JoinScreenState extends State<JoinScreen> {
  final _pin = TextEditingController();
  bool _checking = false;
  JoinResult? _result;

  String get _digits => _pin.text.replaceAll(RegExp(r'\D'), '');
  bool get _complete => _digits.length == 6;

  @override
  void dispose() {
    _pin.dispose();
    super.dispose();
  }

  Future<void> _join() async {
    setState(() {
      _checking = true;
      _result = null;
    });
    final r = await context.read<AttemptRepository>().join(_digits);
    if (!mounted) return;
    setState(() {
      _checking = false;
      _result = r;
    });

    if (r.outcome == JoinOutcome.ok && r.quiz != null) {
      Navigator.of(context)
          .pushReplacementNamed(Routes.studentLobby, arguments: r.quiz);
    }
  }

  void _enterLate(Quiz quiz, Duration remaining) {
    // Late entry goes straight to the questions, skipping the lobby: the
    // quiz is already running, so there is nothing to wait for.
    final controller = AttemptController(
      context.read<AttemptRepository>(),
      quiz,
      startingFrom: remaining,
    )..startClock();
    Navigator.of(context)
        .pushReplacementNamed(Routes.questionView, arguments: controller);
  }

  @override
  Widget build(BuildContext context) {
    final r = _result;
    final started = r?.outcome == JoinOutcome.alreadyStarted;

    return TakeoverScaffold(
      actionLabel: 'Cancel',
      actionEnabled: !_checking,
      onAction: () => Navigator.of(context).pop(),
      scrollable: true,
      child: started
          ? _alreadyStarted(r!)
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 10),
                Text('Join a quiz', style: AppText.pageTitle),
                const SizedBox(height: 4),
                Text('Type the PIN to get in.', style: AppText.bodyLarge),
                const SizedBox(height: 28),
                _pinField(),
                const SizedBox(height: 10),
                Text(
                  _helperText(),
                  style: AppText.caption.copyWith(
                    fontSize: 12.5,
                    height: 18 / 12.5,
                    color: r?.outcome == JoinOutcome.notFound
                        ? AppColors.red
                        : AppColors.grey3,
                  ),
                ),
                const SizedBox(height: 22),
                if (r?.outcome == JoinOutcome.closed ||
                    r?.outcome == JoinOutcome.alreadySubmitted) ...[
                  // Neither is a mistake, so both sit in the neutral band with
                  // only a way home — never in red.
                  InfoBand(
                    title: r!.outcome == JoinOutcome.closed
                        ? 'This quiz has closed'
                        : 'You already submitted this quiz',
                    text: r.outcome == JoinOutcome.closed
                        ? 'The deadline has passed, so it can no longer be joined.'
                        : 'Your answers are in. Results appear once the quiz '
                            'closes for everyone.',
                  ),
                  const SizedBox(height: 16),
                  OutlinedAction(
                    label: 'Back to home',
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ] else
                  FilledAction(
                    label: _checking ? 'Checking…' : 'Join',
                    busy: _checking,
                    // Disabled until six digits are entered.
                    onPressed: _complete && !_checking ? _join : null,
                  ),
              ],
            ),
    );
  }

  String _helperText() {
    if (_result?.outcome == JoinOutcome.notFound) {
      return 'No open quiz has this PIN. Check the digits with your teacher.';
    }
    return 'Your teacher reads out a 6-digit PIN and shows it on their screen.';
  }

  Widget _pinField() {
    final invalid = _result?.outcome == JoinOutcome.notFound;

    return Container(
      height: 76,
      decoration: BoxDecoration(
        color: AppColors.white,
        border: Border.all(
          color: invalid ? AppColors.red : AppColors.hairlineStrong,
          width: invalid ? 2 : 1,
        ),
        borderRadius: AppRadii.controlR,
      ),
      child: TextField(
        controller: _pin,
        enabled: !_checking,
        autofocus: true,
        keyboardType: TextInputType.number,
        textAlign: TextAlign.center,
        maxLength: 7,
        inputFormatters: [_PinFormatter()],
        style: AppText.pinInput,
        onChanged: (_) => setState(() => _result = null),
        decoration: InputDecoration(
          counterText: '',
          hintText: '000 000',
          hintStyle: AppText.pinInput.copyWith(color: AppColors.disabledText),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(vertical: 14),
        ),
      ),
    );
  }

  /// Late entry is drawn as allowed: the board shows the time left of the
  /// full duration and says the deadline is the same for everyone.
  Widget _alreadyStarted(JoinResult r) {
    final quiz = r.quiz!;
    final remaining = r.remaining ?? quiz.duration;
    final elapsed = quiz.duration - remaining;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 10),
        Text('Already started', style: AppText.pageTitle),
        const SizedBox(height: 4),
        Text('You can still join, with the time that is left.',
            style: AppText.bodyLarge),
        const SizedBox(height: 24),
        AppCard(
          padding: const EdgeInsets.fromLTRB(20, 18, 20, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                quiz.week == null ? quiz.title : '${quiz.week} · ${quiz.title}',
                style: AppText.sheetTitle,
              ),
              const SizedBox(height: 4),
              Text(
                '${quiz.questionCount} questions · started '
                '${elapsed.inMinutes} minutes ago',
                style: AppText.rowSecondary,
              ),
              const SizedBox(height: 18),
              Countdown(
                remaining: remaining,
                variant: CountdownVariant.hero,
                totalLabel: 'of ${quiz.timeLimitMinutes} minutes',
                nearThreshold: const Duration(minutes: 1),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        Text(
          'The deadline is the same for everyone, so you will have less time '
          'than the rest of the class.',
          style: AppText.bodySmall,
        ),
        const SizedBox(height: 22),
        FilledAction(
          label: 'Join now',
          onPressed: () => _enterLate(quiz, remaining),
        ),
        const SizedBox(height: 10),
        OutlinedAction(
          label: 'Not now',
          onPressed: () => Navigator.of(context).pop(),
        ),
      ],
    );
  }
}

/// Groups the six digits as "000 000" while they are typed.
class _PinFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final digits = newValue.text.replaceAll(RegExp(r'\D'), '');
    final capped = digits.length > 6 ? digits.substring(0, 6) : digits;
    final text = capped.length > 3
        ? '${capped.substring(0, 3)} ${capped.substring(3)}'
        : capped;
    return TextEditingValue(
      text: text,
      selection: TextSelection.collapsed(offset: text.length),
    );
  }
}
