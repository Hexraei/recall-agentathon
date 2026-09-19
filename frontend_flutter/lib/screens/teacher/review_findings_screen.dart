import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/repositories.dart';
import '../../models/models.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/buttons.dart';
import '../../widgets/shared/misc.dart';
import '../../widgets/shared/page_scaffold.dart';
import '../../widgets/shared/sheets.dart';

/// Screen 10 — Review Findings.
///
/// A queue of one class gap at a time. Accept is filled; Reject is outlined
/// and neutral, because dismissal is not destructive; Skip for now sits
/// below. The line "Nothing reaches students until you accept" stays on
/// screen because it is the rule behind the screen.
///
/// States: a gap waiting; reject sheet; saving the decision; the next gap
/// after accepting, with a confirmation line; nothing to review.
class ReviewFindingsScreen extends StatefulWidget {
  const ReviewFindingsScreen({super.key});

  @override
  State<ReviewFindingsScreen> createState() => _ReviewFindingsScreenState();
}

class _ReviewFindingsScreenState extends State<ReviewFindingsScreen> {
  late Future<List<Finding>> _future;
  List<Finding> _queue = const [];
  int _index = 0;
  bool _saving = false;

  /// The confirmation line carried over from the decision just made.
  String? _justDecided;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Finding>> _load() async {
    final all = await context.read<ResultsRepository>().findings();
    _queue = all
        .where((f) => f.status == FindingStatus.awaitingReview)
        .toList();
    _index = 0;
    return _queue;
  }

  void _reload() => setState(() => _future = _load());

  Future<void> _decide(FindingStatus status, {String? reason}) async {
    final finding = _queue[_index];
    setState(() => _saving = true);
    await context
        .read<ResultsRepository>()
        .decideFinding(finding.id, status, reason: reason);
    if (!mounted) return;
    setState(() {
      _saving = false;
      _queue = [..._queue]..removeAt(_index);
      if (_index >= _queue.length) _index = 0;
      _justDecided = status == FindingStatus.accepted
          ? 'Accepted. It is on its way to students.'
          : 'Rejected. Nothing about it reaches students.';
    });
  }

  Future<void> _reject() async {
    final result = await showAppSheet<String?>(
      context: context,
      builder: (context) => const _RejectSheet(),
    );
    // A null return means the sheet was dismissed; an empty string means
    // rejected with no reason given, which the copy says is allowed.
    if (result != null) await _decide(FindingStatus.rejected, reason: result);
  }

  void _skip() {
    setState(() {
      _justDecided = null;
      _index = _queue.isEmpty ? 0 : (_index + 1) % _queue.length;
    });
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Finding>>(
      future: _future,
      builder: (context, snap) {
        final done = snap.connectionState == ConnectionState.done;
        final empty = _queue.isEmpty;

        return PageScaffold(
          title: 'Review findings',
          subtitle: !done
              ? null
              : empty
                  ? 'Nothing waiting'
                  : '${_queue.length} class gap'
                      '${_queue.length == 1 ? '' : 's'} waiting',
          backLabel: 'Back to dashboard',
          bottomBar: done && !empty ? _actions() : null,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 18),
              if (!done)
                const LoadingState()
              else if (snap.hasError)
                ErrorState(onRetry: _reload)
              else if (empty)
                _Empty(note: _justDecided)
              else
                _gap(_queue[_index]),
            ],
          ),
        );
      },
    );
  }

  Widget _actions() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            Expanded(
              child: FilledAction(
                label: 'Accept',
                busy: _saving,
                onPressed:
                    _saving ? null : () => _decide(FindingStatus.accepted),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              // Outlined and neutral, not red: dismissing a candidate is not
              // a destructive act.
              child: OutlinedAction(
                label: 'Reject',
                onPressed: _saving ? null : _reject,
              ),
            ),
          ],
        ),
        TextAction(
          label: 'Skip for now',
          color: AppColors.grey2,
          onPressed: _saving ? null : _skip,
        ),
      ],
    );
  }

  Widget _gap(Finding f) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (_justDecided != null) ...[
          InfoBand(
            text: _justDecided!,
            tone: BandTone.accent,
            icon: Icons.check_circle_outline,
          ),
          const SizedBox(height: 14),
        ],
        Row(
          children: [
            Text('${_index + 1} of ${_queue.length}',
                style: AppText.rowTitle
                    .copyWith(fontSize: 13, color: AppColors.grey2)),
            const Spacer(),
            Flexible(
              child: Text(
                'Nothing reaches students until you accept',
                textAlign: TextAlign.right,
                style: AppText.captionSmall.copyWith(color: AppColors.grey3),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Text('${f.topic} · class gap', style: AppText.sectionLabel),
        const SizedBox(height: 8),
        // The statement is in the serif, and describes what a share of the
        // class did — never what any student is like.
        Text('${f.statement}.', style: AppText.questionStem),
        const SectionLabel('Where it showed up', top: 24),
        AppCard(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(f.quizTitle,
                  style: AppText.rowTitle.copyWith(fontSize: 13.5)),
              const SizedBox(height: 4),
              Text(f.questionStem, style: AppText.bodySmall),
              const SizedBox(height: 8),
              Row(
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: [
                  Text('${f.chosenCount} of ${f.classSize}',
                      style: AppText.rowTitle.copyWith(fontSize: 14)),
                  const SizedBox(width: 6),
                  Text('chose it', style: AppText.rowSecondary),
                ],
              ),
            ],
          ),
        ),
        const SectionLabel('What is uncertain'),
        InfoBand(text: f.uncertainty),
        const SectionLabel('Next step students would see'),
        AppCard(
          child: Text(f.nextStep, style: AppText.bodySmall),
        ),
        const SizedBox(height: 8),
      ],
    );
  }
}

class _RejectSheet extends StatefulWidget {
  const _RejectSheet();

  @override
  State<_RejectSheet> createState() => _RejectSheetState();
}

class _RejectSheetState extends State<_RejectSheet> {
  final _reason = TextEditingController();

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SheetFrame(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('Reject this gap?', style: AppText.sheetTitle),
          const SizedBox(height: 8),
          Text('Students will not see a next step for it.',
              style: AppText.bodySmall),
          const SizedBox(height: 18),
          AppField(
            label: 'Reason (optional)',
            controller: _reason,
            maxLines: 3,
          ),
          const SizedBox(height: 22),
          FilledAction(
            label: 'Reject gap',
            onPressed: () => Navigator.of(context).pop(_reason.text.trim()),
          ),
          const SizedBox(height: 10),
          OutlinedAction(
            label: 'Keep it in the queue',
            onPressed: () => Navigator.of(context).pop(),
          ),
        ],
      ),
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty({this.note});

  final String? note;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (note != null) ...[
          InfoBand(
            text: note!,
            tone: BandTone.accent,
            icon: Icons.check_circle_outline,
          ),
          const SizedBox(height: 14),
        ],
        AppCard(
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Nothing to review.', style: AppText.sheetTitle),
              const SizedBox(height: 8),
              Text('New class gaps appear here after a quiz closes.',
                  style: AppText.bodySmall),
              const SizedBox(height: 20),
              OutlinedAction(
                label: 'Back to dashboard',
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
