import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import 'buttons.dart';

/// Opens a bottom sheet over a dimmed page, which is how every confirmation
/// in the app is presented.
Future<T?> showAppSheet<T>({
  required BuildContext context,
  required WidgetBuilder builder,
  bool dismissible = true,
}) {
  return showModalBottomSheet<T>(
    context: context,
    isScrollControlled: true,
    isDismissible: dismissible,
    enableDrag: dismissible,
    backgroundColor: AppColors.white,
    barrierColor: AppColors.ink.withValues(alpha: 0.32),
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
    ),
    builder: (context) => SafeArea(
      top: false,
      child: Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.viewInsetsOf(context).bottom,
        ),
        child: builder(context),
      ),
    ),
  );
}

/// The frame every sheet shares: a grab handle, then its contents.
class SheetFrame extends StatelessWidget {
  const SheetFrame({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 10, 24, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Center(
            child: Container(
              width: 36,
              height: 4,
              margin: const EdgeInsets.only(bottom: 18),
              decoration: BoxDecoration(
                color: AppColors.hairline,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          child,
        ],
      ),
    );
  }
}

/// A two-action confirmation. Returns true for confirm, false for cancel.
class ConfirmSheet extends StatelessWidget {
  const ConfirmSheet({
    super.key,
    required this.title,
    required this.body,
    required this.confirmLabel,
    required this.cancelLabel,
    this.destructive = false,
    this.confirmIsFilled = true,
    this.detail,
  });

  final String title;
  final String body;
  final String confirmLabel;
  final String cancelLabel;
  final bool destructive;

  /// Where the safe path is the one being recommended — "Keep editing" is the
  /// filled action, and Discard is the red outline.
  final bool confirmIsFilled;
  final Widget? detail;

  @override
  Widget build(BuildContext context) {
    final confirm = confirmIsFilled
        ? FilledAction(
            label: confirmLabel,
            destructive: destructive,
            onPressed: () => Navigator.of(context).pop(true),
          )
        : OutlinedAction(
            label: confirmLabel,
            destructive: destructive,
            onPressed: () => Navigator.of(context).pop(true),
          );

    final cancel = confirmIsFilled
        ? OutlinedAction(
            label: cancelLabel,
            onPressed: () => Navigator.of(context).pop(false),
          )
        : FilledAction(
            label: cancelLabel,
            onPressed: () => Navigator.of(context).pop(false),
          );

    return SheetFrame(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(title, style: AppText.sheetTitle),
          const SizedBox(height: 10),
          Text(body, style: AppText.bodySmall.copyWith(height: 20 / 13.5)),
          if (detail != null) ...[
            const SizedBox(height: 16),
            detail!,
          ],
          const SizedBox(height: 22),
          confirm,
          const SizedBox(height: 10),
          cancel,
        ],
      ),
    );
  }
}
