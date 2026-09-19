import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/repositories.dart';
import '../../models/models.dart';
import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/charts.dart';
import '../../widgets/shared/live_dot.dart';
import '../../widgets/shared/misc.dart';
import '../../widgets/shared/page_scaffold.dart';

/// A class-level topic page, reached from Class Analytics.
///
/// It holds the topic's percentage and its gaps: status, a statement like
/// "19 of 42 students chose…", and evidence as quiz plus question. No student
/// names appear on a gap, ever.
class ClassTopicScreen extends StatefulWidget {
  const ClassTopicScreen({super.key, required this.topic});

  final String topic;

  @override
  State<ClassTopicScreen> createState() => _ClassTopicScreenState();
}

class _ClassTopicScreenState extends State<ClassTopicScreen> {
  late Future<TopicAggregate?> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<TopicAggregate?> _load() async {
    final all = await context.read<ResultsRepository>().topicAggregates();
    for (final t in all) {
      if (t.topic == widget.topic) return t;
    }
    return null;
  }

  void _reload() => setState(() => _future = _load());

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<TopicAggregate?>(
      future: _future,
      builder: (context, snap) {
        final t = snap.data;
        final done = snap.connectionState == ConnectionState.done;

        return PageScaffold(
          title: widget.topic,
          subtitle: t == null ? null : '${t.questionCount} questions across quizzes',
          backLabel: 'Back to class analytics',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 18),
              if (!done)
                const LoadingState()
              else if (snap.hasError)
                ErrorState(onRetry: _reload)
              else if (t == null)
                const InfoBand(text: 'This topic is no longer in view.')
              else ...[
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text('Answered correctly across the class.',
                          style: AppText.bodySmall),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(child: TopicBar(fraction: t.percent / 100)),
                          const SizedBox(width: 12),
                          Text('${t.percent}%',
                              style: AppText.rowTitle.copyWith(fontSize: 15)),
                        ],
                      ),
                    ],
                  ),
                ),
                const SectionLabel('Class gaps'),
                if (t.gaps.isEmpty)
                  const InfoBand(text: 'Nothing flagged.')
                else
                  Column(
                    children: [
                      for (var i = 0; i < t.gaps.length; i++) ...[
                        if (i > 0) const SizedBox(height: 10),
                        _GapCard(
                          finding: t.gaps[i],
                          onTap: () => Navigator.of(context)
                              .pushNamed(Routes.reviewFindings)
                              .then((_) => _reload()),
                        ),
                      ],
                    ],
                  ),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _GapCard extends StatelessWidget {
  const _GapCard({required this.finding, this.onTap});

  final Finding finding;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.white,
      borderRadius: AppRadii.containerR,
      child: InkWell(
        onTap: onTap,
        borderRadius: AppRadii.containerR,
        child: Container(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
          decoration: BoxDecoration(
            border: Border.all(color: AppColors.hairline),
            borderRadius: AppRadii.containerR,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  _StatusTag(status: finding.status),
                  const Spacer(),
                  const Icon(Icons.chevron_right,
                      size: 18, color: AppColors.grey4),
                ],
              ),
              const SizedBox(height: 10),
              Text('${finding.statement}.',
                  style: AppText.bodySmall.copyWith(color: AppColors.ink)),
              const SizedBox(height: 8),
              Text(
                // Evidence is quiz plus question. No student names.
                '${finding.quizTitle} · ${finding.chosenCount} of '
                '${finding.classSize} students',
                style: AppText.rowSecondary,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusTag extends StatelessWidget {
  const _StatusTag({required this.status});

  final FindingStatus status;

  @override
  Widget build(BuildContext context) {
    final (label, color, bg) = switch (status) {
      FindingStatus.awaitingReview =>
        ('Awaiting review', AppColors.accent, AppColors.accentTint),
      FindingStatus.accepted =>
        ('Accepted', AppColors.accentDeep, AppColors.accentTint),
      FindingStatus.rejected =>
        ('Rejected', AppColors.grey2, AppColors.neutralBand),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(11),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (status == FindingStatus.awaitingReview) ...[
            const LiveDot(size: 6),
            const SizedBox(width: 6),
          ],
          Text(label,
              style: AppText.captionSmall
                  .copyWith(fontWeight: FontWeight.w600, color: color)),
        ],
      ),
    );
  }
}
