import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'colors.dart';

/// The type scale, straight off the canvas.
///
/// Fraunces sets headings and any number meant to be read as a result.
/// IBM Plex Sans sets everything else — including the PIN and the countdown,
/// because those are read aloud and typed rather than read as headings.
class AppText {
  AppText._();

  static TextStyle _serif({
    required double size,
    FontWeight weight = FontWeight.w600,
    Color color = AppColors.ink,
    double? letterSpacing,
    double? height,
  }) => GoogleFonts.fraunces(
    fontSize: size,
    fontWeight: weight,
    color: color,
    letterSpacing: letterSpacing,
    height: height == null ? null : height / size,
  );

  static TextStyle _sans({
    required double size,
    FontWeight weight = FontWeight.w400,
    Color color = AppColors.ink,
    double? letterSpacing,
    double? height,
    FontFeature? feature,
  }) => GoogleFonts.ibmPlexSans(
    fontSize: size,
    fontWeight: weight,
    color: color,
    letterSpacing: letterSpacing,
    height: height == null ? null : height / size,
    fontFeatures: feature == null ? null : [feature],
  );

  // ---------------------------------------------------------------- serif
  /// The Recall lockup on Splash.
  static TextStyle get lockup => _serif(size: 46, letterSpacing: -0.5);

  /// Large result figures — a student's score, a class percentage.
  static TextStyle get displayResult => _serif(size: 34, letterSpacing: -0.6);

  static TextStyle get resultFigure => _serif(size: 30, letterSpacing: -0.5);

  /// The standard page title on an inner screen.
  static TextStyle get pageTitle => _serif(size: 27, letterSpacing: -0.4);

  static TextStyle get sectionTitle => _serif(size: 24, letterSpacing: -0.3);

  /// Sheet and dialog headings.
  static TextStyle get sheetTitle => _serif(size: 21, letterSpacing: -0.2);

  static TextStyle get dialogTitle => _serif(size: 22, letterSpacing: -0.2);

  /// A question stem, and a finding statement, are both set in the serif.
  static TextStyle get questionStem =>
      _serif(size: 23, letterSpacing: -0.2, height: 31);

  static TextStyle get statFigure => _serif(size: 28, letterSpacing: -0.4);

  // ----------------------------------------------------------------- sans
  /// 52px control label.
  static TextStyle get button =>
      _sans(size: 16, weight: FontWeight.w600, letterSpacing: 0.2);

  static TextStyle get bodyLarge =>
      _sans(size: 15, height: 22, color: AppColors.grey2);

  /// Row titles in a navigation list.
  static TextStyle get rowTitle => _sans(size: 15, weight: FontWeight.w600);

  static TextStyle get body =>
      _sans(size: 14, height: 20, color: AppColors.grey1);

  static TextStyle get bodySmall =>
      _sans(size: 13.5, height: 19, color: AppColors.grey1);

  /// One line of live secondary text under a row title.
  static TextStyle get rowSecondary =>
      _sans(size: 12.5, color: AppColors.grey3);

  static TextStyle get caption => _sans(size: 12, color: AppColors.grey3);

  static TextStyle get captionSmall => _sans(size: 11, color: AppColors.grey3);

  /// The uppercase section label that sits above a card group.
  static TextStyle get sectionLabel => _sans(
    size: 12,
    weight: FontWeight.w600,
    letterSpacing: 0.8,
    color: AppColors.grey3,
  );

  /// Field label above an input.
  static TextStyle get fieldLabel =>
      _sans(size: 13, weight: FontWeight.w600, color: AppColors.grey1);

  /// The six-digit PIN on the Host Lobby — sans, because it is read aloud.
  static TextStyle get pinDisplay => _sans(
    size: 52,
    weight: FontWeight.w600,
    letterSpacing: 6,
    feature: const FontFeature.tabularFigures(),
  );

  /// The PIN a student types.
  static TextStyle get pinInput => _sans(
    size: 40,
    weight: FontWeight.w600,
    letterSpacing: 8,
    feature: const FontFeature.tabularFigures(),
  );

  /// The countdown, in tabular numerals so digits do not jitter.
  static TextStyle countdown({double size = 40, Color color = AppColors.ink}) =>
      _sans(
        size: size,
        weight: FontWeight.w600,
        color: color,
        letterSpacing: -0.5,
        feature: const FontFeature.tabularFigures(),
      );

  /// A number inside a stat tile.
  static TextStyle get tileFigure => _sans(
    size: 26,
    weight: FontWeight.w600,
    feature: const FontFeature.tabularFigures(),
  );

  static TextStyle get optionText =>
      _sans(size: 14.5, height: 20, color: AppColors.grey1);

  static TextStyle get optionTextSelected => _sans(
    size: 14.5,
    height: 20,
    weight: FontWeight.w600,
    color: AppColors.ink,
  );
}
