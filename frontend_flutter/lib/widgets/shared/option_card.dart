import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/text_styles.dart';

/// How an option card presents itself.
///
/// [unselected] and [selected] are the two states during an attempt.
/// [correct] and [incorrect] appear on results screens only — and note that
/// [incorrect] is grey, never red: a wrong answer is not an error state.
enum OptionState { unselected, selected, correct, incorrect }

/// The one option card used on every question in the app.
///
/// A 28px letter badge and the full option text in a bounded container,
/// minimum 60px tall. Options are deliberately not colour-coded or
/// shape-coded, and never laid out as four quadrants.
class OptionCard extends StatelessWidget {
  const OptionCard({
    super.key,
    required this.letter,
    required this.text,
    this.state = OptionState.unselected,
    this.onTap,
    this.trailing,
  });

  /// A, B, C or D.
  final String letter;
  final String text;
  final OptionState state;
  final VoidCallback? onTap;

  /// Used on the question-breakdown sheet to carry the share who chose this.
  final Widget? trailing;

  bool get _isSelected => state == OptionState.selected;
  bool get _isCorrect => state == OptionState.correct;
  bool get _isIncorrect => state == OptionState.incorrect;

  Color get _background {
    if (_isSelected || _isCorrect) return AppColors.accentTint;
    return AppColors.white;
  }

  Border get _border {
    if (_isSelected || _isCorrect) {
      return Border.all(color: AppColors.accent, width: 2);
    }
    return Border.all(color: AppColors.hairline);
  }

  @override
  Widget build(BuildContext context) {
    // A 2px border eats 1px more per side than the hairline, so the padding
    // compensates to keep the text on the same baseline across states.
    final pad = (_isSelected || _isCorrect) ? 15.0 : 16.0;

    return Semantics(
      button: onTap != null,
      selected: _isSelected,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            constraints: const BoxConstraints(minHeight: 60),
            padding: EdgeInsets.all(pad),
            decoration: BoxDecoration(
              color: _background,
              border: _border,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                _Badge(letter: letter, state: state),
                const SizedBox(width: 13),
                Expanded(
                  child: Text(
                    text,
                    style: AppText.optionText.copyWith(
                      fontSize: 15,
                      height: 21 / 15,
                      color: AppColors.ink,
                      fontWeight: (_isSelected || _isCorrect)
                          ? FontWeight.w600
                          : FontWeight.w400,
                    ),
                  ),
                ),
                if (trailing != null) ...[const SizedBox(width: 12), trailing!],
                if (_isCorrect) ...[
                  const SizedBox(width: 10),
                  const Icon(Icons.check, size: 18, color: AppColors.accent),
                ],
                if (_isIncorrect) ...[
                  const SizedBox(width: 10),
                  const Icon(Icons.close, size: 18, color: AppColors.grey4),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({required this.letter, required this.state});

  final String letter;
  final OptionState state;

  @override
  Widget build(BuildContext context) {
    final filled =
        state == OptionState.selected || state == OptionState.correct;

    return Container(
      width: 28,
      height: 28,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: filled ? AppColors.accent : AppColors.ground,
        border: filled ? null : Border.all(color: AppColors.hairlineStrong),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Text(
        letter,
        style: AppText.rowTitle.copyWith(
          fontSize: 13.5,
          color: filled ? AppColors.white : AppColors.grey2,
        ),
      ),
    );
  }
}
