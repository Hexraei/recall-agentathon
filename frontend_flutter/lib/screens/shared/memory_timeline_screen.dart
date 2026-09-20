import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/repositories.dart';
import '../../models/memory_models.dart';
import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/misc.dart';
import '../../widgets/shared/page_scaffold.dart';

/// Persistent-memory demo — one identity's timeline.
///
/// Calls `GET /api/memory/student/{id}` for real. Sittings render oldest
/// first, one card each, so the persistence tells itself: sitting 1 has
/// nothing behind it, and each later one is deciding against everything
/// before it. The three outcomes (`first`, `found`, `none_found`) are all
/// real, equally confident results — `none_found` is drawn as a normal card,
/// never as an empty or error state, per FLUTTER_CONTEXT.md.
class MemoryTimelineScreen extends StatefulWidget {
  const MemoryTimelineScreen({super.key, required this.studentId});

  final String studentId;

  @override
  State<MemoryTimelineScreen> createState() => _MemoryTimelineScreenState();
}

class _MemoryTimelineScreenState extends State<MemoryTimelineScreen> {
  late Future<MemoryIdentityDetail> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<MemoryIdentityDetail> _load() =>
      context.read<MemoryRepository>().student(widget.studentId);

  void _reload() => setState(() => _future = _load());

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<MemoryIdentityDetail>(
      future: _future,
      builder: (context, snap) {
        final done = snap.connectionState == ConnectionState.done;
        return PageScaffold(
          title: done && snap.hasData
              ? (snap.data!.name ?? widget.studentId)
              : 'Timeline',
          subtitle: done && snap.hasData ? _deptLabel(snap.data!.department) : null,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 8),
              if (!done)
                const LoadingState(message: 'Loading timeline')
              else if (snap.hasError)
                ErrorState(
                  message: 'Could not load this identity.',
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

  List<Widget> _body(MemoryIdentityDetail d) {
    return [
      _summary(d.summary),
      const SectionLabel('Sittings, oldest first'),
      for (final s in d.sittings) ...[
        _sittingCard(s),
        const SizedBox(height: 12),
      ],
      const SizedBox(height: 10),
      InfoBand(text: d.disclosure, tone: BandTone.neutral),
    ];
  }

  Widget _summary(MemorySummary s) {
    return Row(
      children: [
        Expanded(
          child: StatTile(figure: '${s.totalSittings}', label: 'Sittings'),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: StatTile(
            figure: '${s.repeatsFound}',
            label: 'Repeats found',
            tone: AppColors.accent,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: StatTile(figure: '${s.noRepeatClaimed}', label: 'No repeat'),
        ),
        if (s.awaitingHuman > 0) ...[
          const SizedBox(width: 10),
          Expanded(
            child: StatTile(
              figure: '${s.awaitingHuman}',
              label: 'Awaiting human',
              tone: AppColors.grey2,
            ),
          ),
        ],
      ],
    );
  }

  Widget _sittingCard(Sitting s) {
    return GestureDetector(
      onTap: () => Navigator.of(
        context,
      ).pushNamed(Routes.memorySitting, arguments: s.runId),
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Text(
                  'Sitting ${s.sittingNumber ?? '?'}',
                  style: AppText.rowTitle,
                ),
                const SizedBox(width: 8),
                if (s.date != null)
                  Text(s.date!, style: AppText.rowSecondary),
                const Spacer(),
                _outcomeChip(s.outcome),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              'Could see ${s.priorSittingsVisible} earlier sitting'
              '${s.priorSittingsVisible == 1 ? '' : 's'}.'
              '${s.score != null && s.asked != null ? '  Scored ${s.score}/${s.asked}.' : ''}',
              style: AppText.caption,
            ),
            if (s.explanation != null) ...[
              const SizedBox(height: 10),
              // The agent's own sentences, rendered verbatim.
              Text(s.explanation!, style: AppText.bodySmall),
            ],
            if (s.citedAnswers.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final ref in s.citedAnswers) TagPill(text: ref),
                ],
              ),
            ],
            if (s.awaitingHuman) ...[
              const SizedBox(height: 10),
              InfoBand(
                text: 'Waiting on a professor.',
                tone: BandTone.neutral,
                icon: Icons.hourglass_empty,
              ),
            ],
            if (s.realAnswersFrom != null) ...[
              const SizedBox(height: 8),
              Text(
                'Real answers from ${s.realAnswersFrom}.',
                style: AppText.captionSmall,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _outcomeChip(SittingOutcome outcome) {
    final (label, tone) = switch (outcome) {
      SittingOutcome.first => ('First sitting', AppColors.grey2),
      SittingOutcome.found => ('Repeat found', AppColors.accent),
      SittingOutcome.noneFound => ('No repeat claimed', AppColors.grey1),
      SittingOutcome.unknown => ('Unknown', AppColors.grey3),
    };
    return TagPill(
      text: label,
      tone: tone,
      background: outcome == SittingOutcome.found
          ? AppColors.accentTint
          : AppColors.neutralBand,
    );
  }

  static String _deptLabel(String? d) {
    if (d == null) return '';
    return d
        .split('_')
        .map((w) => w.isEmpty ? w : w[0].toUpperCase() + w.substring(1))
        .join(' ');
  }
}
