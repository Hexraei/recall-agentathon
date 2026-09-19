import 'package:flutter/material.dart';

/// Every hex value in the Recall design system, taken from the canvas exports.
/// Nothing here is invented: each constant appears in `frontend/*.html`.
class AppColors {
  AppColors._();

  /// Warm off-white ground that every screen sits on.
  static const ground = Color(0xFFF5F2EC);
  static const groundRaised = Color(0xFFFBF9F5);
  static const white = Color(0xFFFFFFFF);

  /// Ink and the grey ramp beneath it.
  static const ink = Color(0xFF16191A);
  static const grey1 = Color(0xFF43403A);
  static const grey2 = Color(0xFF5A574E);
  static const grey3 = Color(0xFF6E6A61);
  static const grey4 = Color(0xFF8A8579);
  static const grey5 = Color(0xFF9C988D);

  /// Hairlines. [hairline] bounds a card, [hairlineSoft] divides rows inside one.
  static const hairline = Color(0xFFE2DCD0);
  static const hairlineSoft = Color(0xFFEFEAE0);
  static const hairlineStrong = Color(0xFFD5CEBF);

  /// Disabled/placeholder fills.
  static const disabled = Color(0xFFC9C2B4);
  static const disabledDeep = Color(0xFFC0B8A6);
  static const disabledText = Color(0xFFB3AB9B);

  /// The neutral band: carries a condition that is nobody's fault.
  static const neutralBand = Color(0xFFEEE9DE);
  static const neutralBandBorder = Color(0xFFDBD2C0);

  /// Accent — pine. Switchable per board to navy, rust or ink.
  static const accent = Color(0xFF1F5F55);
  static const accentDeep = Color(0xFF163F39);
  static const accentTint = Color(0xFFECF1EF);
  static const accentTintDeep = Color(0xFFE4EBE9);
  static const accentBorder = Color(0xFFC9DAD5);
  static const accentBorderSoft = Color(0xFFCFE0DA);

  /// Alternate accents offered by the canvas theme switcher.
  static const accentNavy = Color(0xFF2B4A7E);
  static const accentRust = Color(0xFF8A4B2A);

  /// Red is reserved for three meanings only: destructive actions,
  /// user error, and time running out. It never marks a wrong answer.
  static const red = Color(0xFF8C2A20);
  static const redDeep = Color(0xFF6E2018);
  static const redTint = Color(0xFFF9EDEA);
  static const redTintSoft = Color(0xFFFBF4F2);
  static const redBorder = Color(0xFFE2B5AE);
  static const redBorderSoft = Color(0xFFE0BDB5);
}

/// Radii and metrics fixed by the design system.
class AppRadii {
  AppRadii._();

  /// Controls: buttons, inputs, option cards, pills.
  static const double control = 10;

  /// Containers: cards, bands, sheets.
  static const double container = 14;

  static const BorderRadius controlR = BorderRadius.all(Radius.circular(control));
  static const BorderRadius containerR = BorderRadius.all(Radius.circular(container));
}

class AppMetrics {
  AppMetrics._();

  /// Buttons and inputs are 52px; no tap target falls below 44px.
  static const double control = 52;
  static const double minTap = 44;

  /// The canvas is 390 x 844 throughout.
  static const double canvasWidth = 390;

  /// Standard horizontal page padding.
  static const double gutter = 20;
}
