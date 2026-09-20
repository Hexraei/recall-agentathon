import 'package:flutter/material.dart';

import '../../theme/text_styles.dart';
import 'buttons.dart';
import 'misc.dart';
import 'sheets.dart';

/// A one-field sheet asking for a student id, used by both home screens to
/// reach the individual student report — the report is per-student and this
/// app has no roster picker in scope, so the id is typed in directly.
///
/// Returns the trimmed id, or null if the sheet was dismissed without one.
class StudentIdSheet extends StatefulWidget {
  const StudentIdSheet({super.key});

  @override
  State<StudentIdSheet> createState() => _StudentIdSheetState();
}

class _StudentIdSheetState extends State<StudentIdSheet> {
  final _id = TextEditingController();

  @override
  void dispose() {
    _id.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SheetFrame(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('Open a student report', style: AppText.sheetTitle),
          const SizedBox(height: 8),
          Text(
            'Type the student id exactly as recorded in the quiz roster.',
            style: AppText.bodySmall,
          ),
          const SizedBox(height: 18),
          AppField(label: 'Student id', controller: _id, autofocus: true),
          const SizedBox(height: 22),
          FilledAction(
            label: 'Open report',
            onPressed: () {
              final id = _id.text.trim();
              if (id.isNotEmpty) Navigator.of(context).pop(id);
            },
          ),
          const SizedBox(height: 10),
          OutlinedAction(
            label: 'Cancel',
            onPressed: () => Navigator.of(context).pop(),
          ),
        ],
      ),
    );
  }
}
