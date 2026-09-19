import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/text_styles.dart';

/// Filled means commit; outlined means a repeatable step. That distinction
/// holds app-wide, so the two are separate widgets rather than one flag.
class FilledAction extends StatelessWidget {
  const FilledAction({
    super.key,
    required this.label,
    this.onPressed,
    this.busy = false,
    this.destructive = false,
    this.height = AppMetrics.control,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool busy;
  final bool destructive;
  final double height;

  @override
  Widget build(BuildContext context) {
    final enabled = onPressed != null && !busy;
    final fill = destructive ? AppColors.red : AppColors.accent;

    return SizedBox(
      height: height,
      width: double.infinity,
      child: Material(
        color: enabled ? fill : AppColors.disabled,
        borderRadius: AppRadii.controlR,
        child: InkWell(
          onTap: enabled ? onPressed : null,
          borderRadius: AppRadii.controlR,
          child: Center(
            child: busy
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor:
                          AlwaysStoppedAnimation<Color>(AppColors.white),
                    ),
                  )
                : Text(
                    label,
                    style: AppText.button.copyWith(
                      color: enabled ? AppColors.white : AppColors.groundRaised,
                    ),
                  ),
          ),
        ),
      ),
    );
  }
}

class OutlinedAction extends StatelessWidget {
  const OutlinedAction({
    super.key,
    required this.label,
    this.onPressed,
    this.destructive = false,
    this.height = AppMetrics.control,
    this.expand = true,
  });

  final String label;
  final VoidCallback? onPressed;

  /// A red outline, used for Discard — destructive but not the primary path.
  final bool destructive;
  final double height;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    final enabled = onPressed != null;
    final line = destructive
        ? AppColors.redBorder
        : (enabled ? AppColors.disabledDeep : AppColors.hairline);
    final text = destructive
        ? AppColors.red
        : (enabled ? AppColors.ink : AppColors.disabledText);

    return SizedBox(
      height: height,
      width: expand ? double.infinity : null,
      child: Material(
        color: AppColors.white,
        borderRadius: AppRadii.controlR,
        child: InkWell(
          onTap: onPressed,
          borderRadius: AppRadii.controlR,
          child: Container(
            alignment: Alignment.center,
            padding: expand ? null : const EdgeInsets.symmetric(horizontal: 16),
            decoration: BoxDecoration(
              border: Border.all(color: line),
              borderRadius: AppRadii.controlR,
            ),
            child: Text(
              label,
              style: AppText.button.copyWith(fontSize: 15.5, color: text),
            ),
          ),
        ),
      ),
    );
  }
}

/// The quieter link beneath a pair of actions — "Review & submit",
/// "Let it run to 0:00", "Skip for now".
class TextAction extends StatelessWidget {
  const TextAction({
    super.key,
    required this.label,
    this.onPressed,
    this.color = AppColors.accent,
    this.height = 46,
  });

  final String label;
  final VoidCallback? onPressed;
  final Color color;
  final double height;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: height,
      width: double.infinity,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onPressed,
          borderRadius: AppRadii.controlR,
          child: Center(
            child: Text(
              label,
              style: AppText.rowTitle.copyWith(fontSize: 14.5, color: color),
            ),
          ),
        ),
      ),
    );
  }
}

/// The small outlined pill used for Host on a quiz row.
class PillAction extends StatelessWidget {
  const PillAction({super.key, required this.label, this.onPressed});

  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.white,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          height: 34,
          alignment: Alignment.center,
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            border: Border.all(color: AppColors.hairlineStrong),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            label,
            style: AppText.rowTitle.copyWith(fontSize: 13.5, color: AppColors.accent),
          ),
        ),
      ),
    );
  }
}
