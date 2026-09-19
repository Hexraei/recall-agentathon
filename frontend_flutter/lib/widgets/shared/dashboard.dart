import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import 'live_dot.dart';

/// The greeting-and-sign-out header both dashboards open with.
class DashboardHeader extends StatelessWidget {
  const DashboardHeader({
    super.key,
    required this.greeting,
    required this.name,
    this.onSignOut,
  });

  final String greeting;
  final String name;
  final VoidCallback? onSignOut;

  static String greetingForHour(int hour) {
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                greeting,
                style: AppText.bodySmall.copyWith(color: AppColors.grey2),
              ),
              const SizedBox(height: 2),
              Text(name, style: AppText.pageTitle),
            ],
          ),
        ),
        Semantics(
          button: true,
          label: 'Sign out',
          child: SizedBox(
            width: 44,
            height: 44,
            child: Material(
              color: Colors.transparent,
              shape: const CircleBorder(),
              child: InkWell(
                customBorder: const CircleBorder(),
                onTap: onSignOut,
                child: const Icon(
                  Icons.logout,
                  size: 20,
                  color: AppColors.grey2,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// The filled accent card that carries the one action each role's dashboard
/// is really for: Host a quiz, Join a quiz.
class PrimaryActionCard extends StatelessWidget {
  const PrimaryActionCard({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    this.onTap,
    this.enabled = true,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    if (!enabled) {
      // On first run the entry points grey out and say what unlocks them,
      // rather than disappearing.
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        decoration: BoxDecoration(
          color: AppColors.white,
          border: Border.all(color: AppColors.hairline),
          borderRadius: AppRadii.containerR,
        ),
        child: Row(
          children: [
            Icon(icon, size: 22, color: AppColors.disabled),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    title,
                    style: AppText.rowTitle.copyWith(
                      color: AppColors.disabledText,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: AppText.rowSecondary.copyWith(
                      color: AppColors.disabledText,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }

    return Material(
      color: AppColors.accent,
      borderRadius: AppRadii.containerR,
      child: InkWell(
        onTap: onTap,
        borderRadius: AppRadii.containerR,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
          child: Row(
            children: [
              Icon(icon, size: 24, color: AppColors.white),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      title,
                      style: AppText.button.copyWith(
                        fontSize: 17,
                        color: AppColors.white,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      subtitle,
                      style: AppText.rowSecondary.copyWith(
                        color: AppColors.white.withValues(alpha: 0.82),
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, size: 20, color: AppColors.white),
            ],
          ),
        ),
      ),
    );
  }
}

/// The invitation card that becomes the primary on a first run.
class InvitationCard extends StatelessWidget {
  const InvitationCard({
    super.key,
    required this.title,
    required this.body,
    required this.actionLabel,
    this.onAction,
  });

  final String title;
  final String body;
  final String actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 18),
      decoration: BoxDecoration(
        color: AppColors.accentTint,
        border: Border.all(color: AppColors.accentBorder),
        borderRadius: AppRadii.containerR,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            title,
            style: AppText.sheetTitle.copyWith(color: AppColors.accentDeep),
          ),
          const SizedBox(height: 8),
          Text(body, style: AppText.bodySmall.copyWith(color: AppColors.grey1)),
          const SizedBox(height: 16),
          Align(
            alignment: Alignment.centerLeft,
            child: Material(
              color: AppColors.accent,
              borderRadius: AppRadii.controlR,
              child: InkWell(
                onTap: onAction,
                borderRadius: AppRadii.controlR,
                child: Container(
                  height: 46,
                  alignment: Alignment.center,
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Text(
                    actionLabel,
                    style: AppText.button.copyWith(
                      fontSize: 15,
                      color: AppColors.white,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// The pulsing banner that surfaces a quiz open right now.
class LiveBanner extends StatelessWidget {
  const LiveBanner({
    super.key,
    required this.title,
    required this.detail,
    this.onTap,
  });

  final String title;
  final String detail;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.accentTint,
      borderRadius: AppRadii.containerR,
      child: InkWell(
        onTap: onTap,
        borderRadius: AppRadii.containerR,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          decoration: BoxDecoration(
            border: Border.all(color: AppColors.accentBorder),
            borderRadius: AppRadii.containerR,
          ),
          child: Row(
            children: [
              const LiveDot(),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      title,
                      style: AppText.rowTitle.copyWith(
                        fontSize: 14,
                        color: AppColors.accentDeep,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      detail,
                      style: AppText.rowSecondary.copyWith(
                        color: AppColors.grey1,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(
                Icons.chevron_right,
                size: 18,
                color: AppColors.accent,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
