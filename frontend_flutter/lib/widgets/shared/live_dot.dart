import 'package:flutter/material.dart';

import '../../theme/colors.dart';

/// The pulsing accent dot that marks anything updating in real time: the
/// joined-students count, the monitor's status line, the open-quiz banner,
/// and the lobby's waiting state.
class LiveDot extends StatefulWidget {
  const LiveDot({super.key, this.size = 7, this.color = AppColors.accent});

  final double size;
  final Color color;

  @override
  State<LiveDot> createState() => _LiveDotState();
}

class _LiveDotState extends State<LiveDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1600),
  )..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: widget.size,
      height: widget.size,
      child: AnimatedBuilder(
        animation: _c,
        builder: (context, child) {
          // Opacity eases down and back so the dot reads as breathing
          // rather than blinking.
          final t = (1 - (_c.value * 2 - 1).abs());
          return Opacity(opacity: 0.45 + 0.55 * t, child: child);
        },
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: widget.color,
            shape: BoxShape.circle,
          ),
        ),
      ),
    );
  }
}
