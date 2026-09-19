import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/controllers.dart';
import '../../models/models.dart';
import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/buttons.dart';
import '../../widgets/shared/misc.dart';

/// Screen 01 — Splash.
///
/// States: loading while the session restores; cannot connect, with a retry.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  bool _failed = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _restore());
  }

  Future<void> _restore() async {
    setState(() => _failed = false);
    try {
      final user = await context.read<AuthController>().restore();
      if (!mounted) return;
      if (user == null) {
        Navigator.of(context).pushReplacementNamed(Routes.auth);
      } else {
        Navigator.of(context).pushReplacementNamed(
          user.role == UserRole.teacher
              ? Routes.teacherHome
              : Routes.studentHome,
        );
      }
    } catch (_) {
      if (mounted) setState(() => _failed = true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.ground,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Column(
            children: [
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    RecallMark(
                      color: _failed
                          ? AppColors.disabledText
                          : AppColors.accent,
                    ),
                    const SizedBox(height: 22),
                    Text(
                      'Recall',
                      style: AppText.lockup.copyWith(
                        color: _failed ? AppColors.disabledText : AppColors.ink,
                      ),
                    ),
                  ],
                ),
              ),
              if (_failed) ..._cannotConnect() else ..._restoring(),
            ],
          ),
        ),
      ),
    );
  }

  List<Widget> _restoring() => [
    Padding(
      padding: const EdgeInsets.only(bottom: 72),
      child: Column(
        children: [
          const _IndeterminateBar(),
          const SizedBox(height: 18),
          Text(
            'Restoring your session',
            style: AppText.caption.copyWith(
              fontSize: 13,
              fontWeight: FontWeight.w500,
              letterSpacing: 0.3,
              color: AppColors.grey2,
            ),
          ),
        ],
      ),
    ),
  ];

  List<Widget> _cannotConnect() => [
    Padding(
      padding: const EdgeInsets.only(bottom: 28),
      child: Column(
        children: [
          Text("Can't reach Recall", style: AppText.dialogTitle),
          const SizedBox(height: 10),
          SizedBox(
            width: 280,
            child: Text(
              'Check your connection and try again.',
              textAlign: TextAlign.center,
              style: AppText.bodyLarge,
            ),
          ),
        ],
      ),
    ),
    Padding(
      padding: const EdgeInsets.only(bottom: 56),
      child: FilledAction(label: 'Try again', onPressed: _restore),
    ),
  ];
}

/// The 96px hairline bar under the lockup, with a fill that slides.
class _IndeterminateBar extends StatefulWidget {
  const _IndeterminateBar();

  @override
  State<_IndeterminateBar> createState() => _IndeterminateBarState();
}

class _IndeterminateBarState extends State<_IndeterminateBar>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 96,
      height: 3,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: AppColors.hairline,
          borderRadius: BorderRadius.circular(2),
        ),
        child: AnimatedBuilder(
          animation: _c,
          builder: (context, _) => Align(
            alignment: Alignment(_c.value * 2 - 1, 0),
            child: FractionallySizedBox(
              widthFactor: 0.4,
              child: Container(
                height: 3,
                decoration: BoxDecoration(
                  color: AppColors.accent,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
