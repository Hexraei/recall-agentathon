import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/repositories.dart';
import '../../models/memory_models.dart';
import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/misc.dart';
import '../../widgets/shared/nav_list.dart';
import '../../widgets/shared/page_scaffold.dart';

/// Persistent-memory demo — identity list.
///
/// Calls `GET /api/memory/students` for real, through [MemoryRepository].
/// Each row shows sittings, whether a repeat was ever found, and whether
/// anything is waiting on a human — never why. The disclosure that this is a
/// constructed timeline over real answers sits in the footer of every screen
/// this data appears on, per FLUTTER_CONTEXT.md.
class MemoryIdentitiesScreen extends StatefulWidget {
  const MemoryIdentitiesScreen({super.key});

  @override
  State<MemoryIdentitiesScreen> createState() =>
      _MemoryIdentitiesScreenState();
}

class _MemoryIdentitiesScreenState extends State<MemoryIdentitiesScreen> {
  late Future<List<MemoryIdentitySummary>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<MemoryIdentitySummary>> _load() =>
      context.read<MemoryRepository>().students();

  void _reload() => setState(() => _future = _load());

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<MemoryIdentitySummary>>(
      future: _future,
      builder: (context, snap) {
        final done = snap.connectionState == ConnectionState.done;
        return PageScaffold(
          title: 'Persistent memory',
          subtitle: done && snap.hasData
              ? (snap.data!.length == 1
                    ? '1 identity'
                    : '${snap.data!.length} identities')
              : null,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 8),
              if (!done)
                const LoadingState(message: 'Loading identities')
              else if (snap.hasError)
                _errorFor(snap.error, _reload)
              else if (snap.data!.isEmpty)
                const InfoBand(text: 'No identities recorded yet.')
              else ...[
                _list(snap.data!),
                const SizedBox(height: 22),
                InfoBand(text: _disclosure, tone: BandTone.neutral),
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _list(List<MemoryIdentitySummary> items) {
    return NavList(
      rows: [
        for (final s in items)
          NavRow(
            icon: Icons.timeline,
            title: s.name ?? s.studentId,
            secondary:
                '${_deptLabel(s.department)} · ${s.sittings} sitting'
                '${s.sittings == 1 ? '' : 's'}'
                '${s.awaitingHuman ? ' · awaiting a professor' : ''}',
            badge: s.foundARepeat ? 'Repeat found' : null,
            onTap: () => Navigator.of(context).pushNamed(
              Routes.memoryTimeline,
              arguments: s.studentId,
            ),
          ),
      ],
    );
  }

  static String _deptLabel(String? d) {
    if (d == null) return 'Unknown department';
    return d
        .split('_')
        .map((w) => w.isEmpty ? w : w[0].toUpperCase() + w.substring(1))
        .join(' ');
  }

  static Widget _errorFor(Object? error, VoidCallback onRetry) {
    if (error is MemoryNotBuiltException) {
      return InfoBand(
        title: 'The memory demo has not been built',
        text: error.message,
        tone: BandTone.neutral,
      );
    }
    return ErrorState(
      message: "Could not reach the server for the memory demo.",
      onRetry: onRetry,
    );
  }
}

const _disclosure =
    'Every answer in this record is a real answer from a real student who '
    'took this quiz. The timeline is constructed: separate real students are '
    'shown here as one person sitting the quiz several times, because the '
    'system detects mistakes that repeat across separate occasions and a '
    'two-day event cannot produce that naturally.';
