import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/text_styles.dart';

/// Which meaning a band carries.
enum BandTone {
  /// A condition that is nobody's fault — a closed quiz, too few quizzes
  /// for a trend, a network failure.
  neutral,

  /// Affirmative state — a decision saved, a finding accepted.
  accent,

  /// Reserved for destructive actions, user error and time running out.
  danger,
}

/// The band that explains a condition instead of drawing an empty frame.
class InfoBand extends StatelessWidget {
  const InfoBand({
    super.key,
    required this.text,
    this.title,
    this.tone = BandTone.neutral,
    this.icon,
    this.action,
  });

  final String text;
  final String? title;
  final BandTone tone;
  final IconData? icon;
  final Widget? action;

  Color get _bg => switch (tone) {
        BandTone.neutral => AppColors.neutralBand,
        BandTone.accent => AppColors.accentTint,
        BandTone.danger => AppColors.redTint,
      };

  Color get _border => switch (tone) {
        BandTone.neutral => AppColors.neutralBandBorder,
        BandTone.accent => AppColors.accentBorder,
        BandTone.danger => AppColors.redBorder,
      };

  Color get _fg => switch (tone) {
        BandTone.neutral => AppColors.grey1,
        BandTone.accent => AppColors.accentDeep,
        BandTone.danger => AppColors.red,
      };

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: _bg,
        border: Border.all(color: _border),
        borderRadius: AppRadii.containerR,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 18, color: _fg),
            const SizedBox(width: 12),
          ],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                if (title != null) ...[
                  Text(title!,
                      style: AppText.rowTitle.copyWith(fontSize: 14, color: _fg)),
                  const SizedBox(height: 4),
                ],
                Text(text,
                    style: AppText.bodySmall.copyWith(
                        color: tone == BandTone.neutral ? AppColors.grey1 : _fg)),
                if (action != null) ...[
                  const SizedBox(height: 10),
                  action!,
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// A white card bounded by a hairline — the default container everywhere.
class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.clip = false,
  });

  final Widget child;
  final EdgeInsets padding;

  /// Set when the card holds full-bleed divided rows.
  final bool clip;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: clip ? EdgeInsets.zero : padding,
      clipBehavior: clip ? Clip.antiAlias : Clip.none,
      decoration: BoxDecoration(
        color: AppColors.white,
        border: Border.all(color: AppColors.hairline),
        borderRadius: AppRadii.containerR,
      ),
      child: child,
    );
  }
}

/// The uppercase label that sits above a card group.
class SectionLabel extends StatelessWidget {
  const SectionLabel(this.text, {super.key, this.top = 26, this.bottom = 10});

  final String text;
  final double top;
  final double bottom;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(top: top, bottom: bottom),
      child: Text(text.toUpperCase(), style: AppText.sectionLabel),
    );
  }
}

/// One of the small figure-over-label tiles used in rows of two or three.
class StatTile extends StatelessWidget {
  const StatTile({
    super.key,
    required this.figure,
    required this.label,
    this.tone,
  });

  final String figure;
  final String label;
  final Color? tone;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.white,
        border: Border.all(color: AppColors.hairline),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            figure,
            textAlign: TextAlign.center,
            style: AppText.tileFigure
                .copyWith(fontSize: 24, color: tone ?? AppColors.ink),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            textAlign: TextAlign.center,
            style: AppText.caption.copyWith(color: AppColors.grey2),
          ),
        ],
      ),
    );
  }
}

/// A dashed-outline placeholder standing in for content that does not exist
/// yet — an empty question slot, a lobby with nobody joined.
class DashedSlot extends StatelessWidget {
  const DashedSlot({super.key, required this.text, this.height = 88});

  final String text;
  final double height;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _DashedBorderPainter(),
      child: Container(
        width: double.infinity,
        height: height,
        alignment: Alignment.center,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Text(
          text,
          textAlign: TextAlign.center,
          style: AppText.bodySmall.copyWith(color: AppColors.grey3),
        ),
      ),
    );
  }
}

class _DashedBorderPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppColors.hairlineStrong
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    final rrect = RRect.fromRectAndRadius(
      Offset.zero & size,
      const Radius.circular(AppRadii.container),
    );

    // Walk the rounded rect and draw 5px on, 4px off.
    for (final metric in (Path()..addRRect(rrect)).computeMetrics()) {
      var d = 0.0;
      while (d < metric.length) {
        final end = (d + 5).clamp(0.0, metric.length);
        canvas.drawPath(metric.extractPath(d, end), paint);
        d += 9;
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
