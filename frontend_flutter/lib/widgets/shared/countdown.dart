import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/text_styles.dart';

/// Where a countdown is being shown, which sets its size and chrome.
enum CountdownVariant {
  /// Live Monitor — the hero figure, 58px, centred in its own card.
  hero,

  /// Question View and Review & Submit — 26px, inline in the header row.
  header,
}

/// The one countdown component, used on Live Monitor, Question View and
/// Review & Submit.
///
/// It counts one deadline for the whole quiz in tabular numerals and is never
/// presented in a way that could read as a per-question timer. In the final
/// minutes it turns red-tinted and says attempts submit themselves at 0:00.
class Countdown extends StatelessWidget {
  const Countdown({
    super.key,
    required this.remaining,
    this.variant = CountdownVariant.header,
    this.totalLabel,
    this.trailing,
    this.nearThreshold = const Duration(minutes: 1),
  });

  final Duration remaining;
  final CountdownVariant variant;

  /// e.g. "of 20 minutes" under the hero figure.
  final String? totalLabel;

  /// e.g. "Question 4 of 15" at the right of the header variant.
  final Widget? trailing;

  /// Below this, the countdown turns red-tinted.
  final Duration nearThreshold;

  bool get isNear => remaining <= nearThreshold;

  static String format(Duration d) {
    final clamped = d.isNegative ? Duration.zero : d;
    final m = clamped.inMinutes;
    final s = clamped.inSeconds % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return variant == CountdownVariant.hero ? _buildHero() : _buildHeader();
  }

  Widget _buildHero() {
    final color = isNear ? AppColors.red : AppColors.ink;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 20),
      decoration: BoxDecoration(
        color: isNear ? AppColors.redTintSoft : AppColors.white,
        border: Border.all(
          color: isNear ? AppColors.redBorder : AppColors.hairline,
        ),
        borderRadius: AppRadii.containerR,
      ),
      child: Column(
        children: [
          Text(
            'TIME LEFT',
            style: AppText.sectionLabel.copyWith(
              color: isNear ? AppColors.red : AppColors.grey3,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            format(remaining),
            style: AppText.countdown(
              size: 58,
              color: color,
            ).copyWith(height: 64 / 58, letterSpacing: -1),
          ),
          if (isNear)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                'Attempts submit themselves at 0:00',
                style: AppText.rowSecondary.copyWith(color: AppColors.red),
              ),
            )
          else if (totalLabel != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(totalLabel!, style: AppText.rowSecondary),
            ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: isNear ? const Color(0xFFF7ECEA) : AppColors.white,
        border: Border.all(
          color: isNear ? AppColors.redBorder : AppColors.hairline,
        ),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                format(remaining),
                style: AppText.countdown(
                  size: 26,
                  color: isNear ? AppColors.red : AppColors.ink,
                ).copyWith(height: 30 / 26),
              ),
              const SizedBox(height: 1),
              Text(
                isNear ? 'Answers submit themselves at 0:00' : 'Time left',
                style: AppText.captionSmall.copyWith(
                  fontSize: 11.5,
                  color: isNear ? AppColors.red : AppColors.grey3,
                ),
              ),
            ],
          ),
          const Spacer(),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}
