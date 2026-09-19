import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/text_styles.dart';

/// One row of a [NavList]: icon, title, one line of live secondary text,
/// an optional badge, and a chevron.
class NavRow {
  const NavRow({
    required this.icon,
    required this.title,
    this.secondary,
    this.badge,
    this.onTap,
    this.enabled = true,
  });

  final IconData icon;
  final String title;
  final String? secondary;

  /// A queue count, rendered as an accent pill — never red, because it
  /// counts work waiting, not an error.
  final String? badge;
  final VoidCallback? onTap;
  final bool enabled;
}

/// The navigation list set on Teacher Home and reused by every list in the
/// app: a white card with a hairline border and 14px radius, rows divided by
/// a softer hairline.
class NavList extends StatelessWidget {
  const NavList({super.key, required this.rows});

  final List<NavRow> rows;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.white,
        border: Border.all(color: AppColors.hairline),
        borderRadius: AppRadii.containerR,
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          for (var i = 0; i < rows.length; i++)
            _Row(row: rows[i], showDivider: i > 0),
        ],
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row({required this.row, required this.showDivider});

  final NavRow row;
  final bool showDivider;

  @override
  Widget build(BuildContext context) {
    final on = row.enabled;
    final titleColor = on ? AppColors.ink : AppColors.disabledText;
    final secondaryColor = on ? AppColors.grey3 : AppColors.disabledText;

    return DecoratedBox(
      decoration: BoxDecoration(
        border: showDivider
            ? const Border(top: BorderSide(color: AppColors.hairlineSoft))
            : null,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: on ? row.onTap : null,
          child: Container(
            constraints: const BoxConstraints(minHeight: 44),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            child: Row(
              children: [
                Icon(
                  row.icon,
                  size: 21,
                  color: on ? AppColors.grey1 : AppColors.disabled,
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        row.title,
                        style: AppText.rowTitle.copyWith(color: titleColor),
                      ),
                      if (row.secondary != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          row.secondary!,
                          style: AppText.rowSecondary.copyWith(
                            color: secondaryColor,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                if (row.badge != null) ...[
                  const SizedBox(width: 10),
                  Container(
                    constraints: const BoxConstraints(minWidth: 24),
                    height: 24,
                    alignment: Alignment.center,
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    decoration: BoxDecoration(
                      color: on ? AppColors.accent : AppColors.disabled,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      row.badge!,
                      style: AppText.rowTitle.copyWith(
                        fontSize: 13,
                        color: AppColors.white,
                      ),
                    ),
                  ),
                ],
                const SizedBox(width: 10),
                Icon(
                  Icons.chevron_right,
                  size: 20,
                  color: on ? AppColors.grey4 : AppColors.disabled,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
