import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/text_styles.dart';

/// Initials for one student, as a chip in the Host Lobby roster or an avatar
/// on a Live Monitor row.
class InitialsChip extends StatelessWidget {
  const InitialsChip({
    super.key,
    required this.initials,
    this.size = 30,
    this.emphasised = false,
  });

  final String initials;
  final double size;

  /// The most recently joined student is tinted more strongly.
  final bool emphasised;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: emphasised ? AppColors.accent : AppColors.accentTint,
        borderRadius: BorderRadius.circular(size / 2),
      ),
      child: Text(
        initials,
        style: AppText.rowTitle.copyWith(
          fontSize: 11,
          color: emphasised ? AppColors.white : AppColors.accent,
        ),
      ),
    );
  }
}

/// A small pill — a topic on a question row, a "1 to review" tag.
class TagPill extends StatelessWidget {
  const TagPill({
    super.key,
    required this.text,
    this.tone = AppColors.accent,
    this.background = AppColors.accentTint,
  });

  final String text;
  final Color tone;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(11),
      ),
      child: Text(
        text,
        style: AppText.captionSmall.copyWith(
          fontWeight: FontWeight.w600,
          color: tone,
        ),
      ),
    );
  }
}

/// A divided list of rows inside a white card.
class RowCard extends StatelessWidget {
  const RowCard({super.key, required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: AppColors.white,
        border: Border.all(color: AppColors.hairline),
        borderRadius: AppRadii.containerR,
      ),
      child: Column(
        children: [
          for (var i = 0; i < children.length; i++)
            DecoratedBox(
              decoration: BoxDecoration(
                border: i == 0
                    ? null
                    : const Border(
                        top: BorderSide(color: AppColors.hairlineSoft),
                      ),
              ),
              child: children[i],
            ),
        ],
      ),
    );
  }
}

/// A "label … value" row, used for topic breakdowns and receipts.
class FactRow extends StatelessWidget {
  const FactRow({
    super.key,
    required this.label,
    required this.value,
    this.onTap,
    this.chevron = false,
    this.secondary,
  });

  final String label;
  final String value;
  final String? secondary;
  final VoidCallback? onTap;
  final bool chevron;

  @override
  Widget build(BuildContext context) {
    final content = Container(
      constraints: const BoxConstraints(minHeight: 44),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  label,
                  style: AppText.optionText.copyWith(color: AppColors.ink),
                ),
                if (secondary != null) ...[
                  const SizedBox(height: 2),
                  Text(secondary!, style: AppText.rowSecondary),
                ],
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text(
            value,
            style: AppText.body.copyWith(
              fontWeight: FontWeight.w600,
              color: AppColors.grey1,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
          if (chevron) ...[
            const SizedBox(width: 8),
            const Icon(Icons.chevron_right, size: 18, color: AppColors.grey4),
          ],
        ],
      ),
    );

    if (onTap == null) return content;
    return Material(
      color: Colors.transparent,
      child: InkWell(onTap: onTap, child: content),
    );
  }
}

/// A labelled text field, 52px tall, with the label above and error below.
class AppField extends StatelessWidget {
  const AppField({
    super.key,
    required this.label,
    this.controller,
    this.hint,
    this.error,
    this.obscure = false,
    this.keyboardType,
    this.onChanged,
    this.enabled = true,
    this.maxLines = 1,
    this.suffix,
    this.autofocus = false,
  });

  final String label;
  final TextEditingController? controller;
  final String? hint;
  final String? error;
  final bool obscure;
  final TextInputType? keyboardType;
  final ValueChanged<String>? onChanged;
  final bool enabled;
  final int maxLines;
  final Widget? suffix;
  final bool autofocus;

  @override
  Widget build(BuildContext context) {
    final hasError = error != null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(label, style: AppText.fieldLabel),
        const SizedBox(height: 7),
        Container(
          constraints: BoxConstraints(
            minHeight: maxLines == 1 ? AppMetrics.control : 0,
          ),
          decoration: BoxDecoration(
            color: enabled ? AppColors.white : AppColors.ground,
            border: Border.all(
              color: hasError ? AppColors.red : AppColors.hairlineStrong,
            ),
            borderRadius: AppRadii.controlR,
          ),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: controller,
                  obscureText: obscure,
                  keyboardType: keyboardType,
                  onChanged: onChanged,
                  enabled: enabled,
                  maxLines: maxLines,
                  autofocus: autofocus,
                  style: AppText.bodyLarge.copyWith(color: AppColors.ink),
                  decoration: InputDecoration(
                    hintText: hint,
                    hintStyle: AppText.bodyLarge.copyWith(
                      color: AppColors.disabledText,
                    ),
                    border: InputBorder.none,
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 15,
                    ),
                  ),
                ),
              ),
              if (suffix != null)
                Padding(
                  padding: const EdgeInsets.only(right: 12),
                  child: suffix!,
                ),
            ],
          ),
        ),
        if (hasError) ...[
          const SizedBox(height: 6),
          Text(
            error!,
            style: AppText.caption.copyWith(
              fontSize: 12.5,
              color: AppColors.red,
            ),
          ),
        ],
      ],
    );
  }
}

/// A centred overlay card — the auto-submit notice, a saving state.
class NoticeOverlay extends StatelessWidget {
  const NoticeOverlay({
    super.key,
    required this.title,
    required this.message,
    this.icon = Icons.schedule,
  });

  final String title;
  final String message;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Positioned.fill(
      child: ColoredBox(
        color: AppColors.ground.withValues(alpha: 0.9),
        child: Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 34),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(22, 26, 22, 24),
              decoration: BoxDecoration(
                color: AppColors.white,
                border: Border.all(color: AppColors.hairline),
                borderRadius: AppRadii.containerR,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(icon, size: 34, color: AppColors.accent),
                  const SizedBox(height: 18),
                  Text(
                    title,
                    textAlign: TextAlign.center,
                    style: AppText.sectionTitle,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    message,
                    textAlign: TextAlign.center,
                    style: AppText.optionText.copyWith(height: 21 / 14.5),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// The loading state for a screen that fetches data.
class LoadingState extends StatelessWidget {
  const LoadingState({super.key, this.message});

  final String? message;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 72),
      child: Column(
        children: [
          const SizedBox(
            width: 22,
            height: 22,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation<Color>(AppColors.accent),
            ),
          ),
          if (message != null) ...[
            const SizedBox(height: 16),
            Text(message!, style: AppText.rowSecondary),
          ],
        ],
      ),
    );
  }
}

/// The error state for a screen that fetches data, with an inline retry.
class ErrorState extends StatelessWidget {
  const ErrorState({
    super.key,
    this.message = 'Could not load this just now.',
    this.onRetry,
  });

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 40),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        decoration: BoxDecoration(
          color: AppColors.neutralBand,
          border: Border.all(color: AppColors.neutralBandBorder),
          borderRadius: AppRadii.containerR,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(message, style: AppText.bodySmall),
            if (onRetry != null) ...[
              const SizedBox(height: 10),
              GestureDetector(
                onTap: onRetry,
                child: Text(
                  'Try again',
                  style: AppText.rowTitle.copyWith(
                    fontSize: 13.5,
                    color: AppColors.accent,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// The Recall lockup: a circular arrow that turns back on itself.
class RecallMark extends StatelessWidget {
  const RecallMark({super.key, this.size = 48, this.color = AppColors.accent});

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(painter: _MarkPainter(color)),
    );
  }
}

class _MarkPainter extends CustomPainter {
  _MarkPainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width / 48;
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.6 * s
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    // An arc from the top of the circle round to its left, leaving the gap
    // the arrowhead sits in.
    final rect = Rect.fromCircle(
      center: Offset(24 * s, 24 * s),
      radius: 15 * s,
    );
    canvas.drawArc(rect, -1.5708, 4.7124, false, paint);

    final head = Path()
      ..moveTo(3.6 * s, 29.4 * s)
      ..lineTo(9 * s, 24 * s)
      ..lineTo(14.4 * s, 29.4 * s);
    canvas.drawPath(head, paint);
  }

  @override
  bool shouldRepaint(covariant _MarkPainter oldDelegate) =>
      oldDelegate.color != color;
}
