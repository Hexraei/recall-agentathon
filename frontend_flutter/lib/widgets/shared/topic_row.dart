import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import 'charts.dart';
import 'misc.dart';

/// A topic row with its bar and percentage, used on Quiz Results, Class
/// Analytics and the class-level topic pages.
class TopicRow extends StatelessWidget {
  const TopicRow({
    super.key,
    required this.topic,
    required this.percent,
    this.secondary,
    this.tag,
    this.onTap,
  });

  final String topic;
  final int percent;
  final String? secondary;

  /// "1 to review" on a topic with a gap waiting.
  final String? tag;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 13, 16, 13),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(topic,
                              style: AppText.optionText
                                  .copyWith(color: AppColors.ink)),
                        ),
                        if (tag != null) ...[
                          const SizedBox(width: 8),
                          TagPill(text: tag!),
                        ],
                      ],
                    ),
                    if (secondary != null) ...[
                      const SizedBox(height: 2),
                      Text(secondary!, style: AppText.rowSecondary),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 12),
              SizedBox(
                width: 86,
                child: Row(
                  children: [
                    Expanded(child: TopicBar(fraction: percent / 100)),
                    const SizedBox(width: 10),
                    SizedBox(
                      width: 34,
                      child: Text('$percent%',
                          textAlign: TextAlign.right,
                          style: AppText.body.copyWith(
                            fontWeight: FontWeight.w600,
                            // Text never wears the data colour.
                            color: AppColors.grey1,
                          )),
                    ),
                  ],
                ),
              ),
              if (onTap != null) ...[
                const SizedBox(width: 6),
                const Icon(Icons.chevron_right,
                    size: 18, color: AppColors.grey4),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
