import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/repositories.dart';
import '../../models/memory_models.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/misc.dart';
import '../../widgets/shared/page_scaffold.dart';

/// Persistent-memory demo — one sitting in full.
///
/// Calls `GET /api/memory/sitting/{run_id}` for real. The point of this
/// screen is putting a claim next to the actual answers it rests on: cited
/// answers are marked, so the claim is checkable by whoever is watching
/// rather than a bare assertion.
class MemorySittingScreen extends StatefulWidget {
  const MemorySittingScreen({super.key, required this.runId});

  final String runId;

  @override
  State<MemorySittingScreen> createState() => _MemorySittingScreenState();
}

class _MemorySittingScreenState extends State<MemorySittingScreen> {
  late Future<SittingDetail> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<SittingDetail> _load() =>
      context.read<MemoryRepository>().sitting(widget.runId);

  void _reload() => setState(() => _future = _load());

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<SittingDetail>(
      future: _future,
      builder: (context, snap) {
        final done = snap.connectionState == ConnectionState.done;
        return PageScaffold(
          title: done && snap.hasData
              ? 'Sitting ${snap.data!.sitting.sittingNumber ?? '?'}'
              : 'Sitting',
          subtitle: done && snap.hasData ? snap.data!.sitting.date : null,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 8),
              if (!done)
                const LoadingState(message: 'Loading sitting')
              else if (snap.hasError)
                ErrorState(
                  message: 'Could not load this sitting.',
                  onRetry: _reload,
                )
              else
                ..._body(snap.data!),
            ],
          ),
        );
      },
    );
  }

  List<Widget> _body(SittingDetail d) {
    final s = d.sitting;
    final citedRefs = s.citedAnswers.toSet();
    return [
      if (s.explanation != null) ...[
        const SectionLabel('What the agent concluded', top: 0),
        AppCard(child: Text(s.explanation!, style: AppText.bodySmall)),
      ],
      if (s.finding != null && s.finding!.statement != null) ...[
        const SectionLabel('Finding'),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(s.finding!.statement!, style: AppText.body),
              if (s.finding!.uncertainty != null) ...[
                const SizedBox(height: 10),
                Text('What is uncertain', style: AppText.sectionLabel),
                const SizedBox(height: 4),
                Text(s.finding!.uncertainty!, style: AppText.bodySmall),
              ],
              if (s.finding!.nextStep != null) ...[
                const SizedBox(height: 10),
                Text('Next step', style: AppText.sectionLabel),
                const SizedBox(height: 4),
                Text(s.finding!.nextStep!, style: AppText.bodySmall),
              ],
            ],
          ),
        ),
      ],
      if (s.awaitingHuman) ...[
        const SizedBox(height: 14),
        const InfoBand(
          text: 'Waiting on a professor.',
          tone: BandTone.neutral,
          icon: Icons.hourglass_empty,
        ),
      ],
      const SectionLabel('Answers'),
      if (d.answers.isEmpty)
        const InfoBand(text: 'No answers recorded for this sitting.')
      else
        Column(
          children: [
            for (final a in d.answers) ...[
              _answerRow(a, citedRefs.contains(a.ref)),
              const SizedBox(height: 8),
            ],
          ],
        ),
      const SizedBox(height: 14),
      if (s.realAnswersFrom != null)
        Text(
          'Real answers from ${s.realAnswersFrom}.',
          style: AppText.captionSmall,
        ),
      const SizedBox(height: 10),
      InfoBand(text: d.disclosure, tone: BandTone.neutral),
    ];
  }

  Widget _answerRow(MemoryAnswer a, bool cited) {
    return AppCard(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Text(a.ref ?? '', style: AppText.rowTitle.copyWith(fontSize: 13)),
                    const SizedBox(width: 8),
                    TagPill(
                      text: a.kind == 'strength' ? 'Strength' : 'Difficulty',
                      tone: a.kind == 'strength'
                          ? AppColors.accent
                          : AppColors.grey2,
                      background: a.kind == 'strength'
                          ? AppColors.accentTint
                          : AppColors.neutralBand,
                    ),
                  ],
                ),
                if (a.concept != null) ...[
                  const SizedBox(height: 4),
                  Text(a.concept!, style: AppText.bodySmall),
                ],
                if (a.detail != null) ...[
                  const SizedBox(height: 4),
                  Text(a.detail!, style: AppText.caption),
                ],
              ],
            ),
          ),
          if (cited) ...[
            const SizedBox(width: 8),
            const Icon(Icons.check_circle, size: 18, color: AppColors.accent),
          ],
        ],
      ),
    );
  }
}
