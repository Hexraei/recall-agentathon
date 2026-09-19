import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/text_styles.dart';

/// One bar of a [ColumnChart].
class ColumnDatum {
  const ColumnDatum({
    required this.label,
    required this.value,
    this.absent = false,
  });

  final String label;
  final double value;

  /// A quiz the student did not take: drawn as a dash, not a zero bar.
  final bool absent;
}

/// A single-series column chart: no legend, one hue, zero baseline, every bar
/// labelled. Bars cap at 24px with a 4px rounded data end, and text never
/// wears the data colour.
class ColumnChart extends StatelessWidget {
  const ColumnChart({
    super.key,
    required this.data,
    this.height = 134,
    this.maxValue,
    this.valueFormatter,
  });

  final List<ColumnDatum> data;
  final double height;
  final double? maxValue;
  final String Function(double)? valueFormatter;

  @override
  Widget build(BuildContext context) {
    final peak =
        maxValue ?? data.fold<double>(1, (m, d) => d.value > m ? d.value : m);

    return SizedBox(
      height: height,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          for (final d in data)
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 1),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Text(
                      d.absent
                          ? '—'
                          : (valueFormatter?.call(d.value) ??
                                d.value.toStringAsFixed(0)),
                      style: AppText.caption.copyWith(
                        fontWeight: FontWeight.w600,
                        color: d.absent ? AppColors.grey4 : AppColors.grey1,
                      ),
                    ),
                    const SizedBox(height: 6),
                    if (!d.absent)
                      Container(
                        width: 24,
                        height: (d.value / peak * (height - 40)).clamp(
                          3.0,
                          height,
                        ),
                        decoration: const BoxDecoration(
                          color: AppColors.accent,
                          borderRadius: BorderRadius.vertical(
                            top: Radius.circular(4),
                          ),
                        ),
                      )
                    else
                      Container(
                        width: 24,
                        height: 2,
                        color: AppColors.hairlineStrong,
                      ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// The axis labels beneath a [ColumnChart].
class ChartAxisLabels extends StatelessWidget {
  const ChartAxisLabels({super.key, required this.labels});

  final List<String> labels;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        for (final l in labels)
          Expanded(
            child: Text(
              l,
              textAlign: TextAlign.center,
              style: AppText.captionSmall,
            ),
          ),
      ],
    );
  }
}

/// A horizontal bar for a topic row: length carries the value.
class TopicBar extends StatelessWidget {
  const TopicBar({super.key, required this.fraction, this.width});

  final double fraction;
  final double? width;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, c) {
        final w = width ?? c.maxWidth;
        return Container(
          width: w,
          height: 6,
          decoration: BoxDecoration(
            color: AppColors.accentTintDeep,
            borderRadius: BorderRadius.circular(3),
          ),
          alignment: Alignment.centerLeft,
          child: FractionallySizedBox(
            widthFactor: fraction.clamp(0.0, 1.0),
            child: Container(
              decoration: BoxDecoration(
                color: AppColors.accent,
                borderRadius: BorderRadius.circular(3),
              ),
            ),
          ),
        );
      },
    );
  }
}

/// The segment strip on a student's quiz result: one segment per question,
/// accent for correct and a pale accent for everything else.
class SegmentStrip extends StatelessWidget {
  const SegmentStrip({
    super.key,
    required this.total,
    required this.correct,
    this.height = 8,
  });

  final int total;
  final int correct;
  final double height;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        for (var i = 0; i < total; i++) ...[
          if (i > 0) const SizedBox(width: 3),
          Expanded(
            child: Container(
              height: height,
              decoration: BoxDecoration(
                color: i < correct
                    ? AppColors.accent
                    : AppColors.accentTintDeep,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
        ],
      ],
    );
  }
}
