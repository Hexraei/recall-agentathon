import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

import '../../theme/colors.dart';

/// Every screen was designed for one phone-width canvas. Stretched to a
/// browser window's full width, the same interface reads as a text field
/// spanning a metre and a half — nothing in it was designed to fill that
/// width, so it just looks broken rather than "responsive".
///
/// Wrapping the navigator in this keeps the design at the width it was built
/// for and centres it in whatever space is left over, the way a mobile-only
/// web app is normally presented on a desktop browser. This only ever
/// applies on web: a real phone screen — Android or iOS — is never wider
/// than [maxContentWidth] to begin with, so gating on [kIsWeb] rather than on
/// width alone is what keeps this a true no-op there, including inside
/// flutter_test's default 800-wide surface, which is wider than a phone but
/// is not a browser window either.
class ResponsiveShell extends StatelessWidget {
  const ResponsiveShell({super.key, required this.child});

  final Widget child;

  /// A little past the 390 the canvas was drawn at, so nothing the design
  /// already allows to breathe (a 400px sheet, say) is squeezed by the frame
  /// meant to stop it stretching further than that.
  static const double maxContentWidth = 460;

  @override
  Widget build(BuildContext context) {
    if (!kIsWeb) return child;
    final width = MediaQuery.sizeOf(context).width;
    if (width <= maxContentWidth) return child;

    return ColoredBox(
      color: AppColors.neutralBand,
      child: Center(
        child: Container(
          width: maxContentWidth,
          decoration: const BoxDecoration(
            color: AppColors.ground,
            border: Border.symmetric(
              vertical: BorderSide(color: AppColors.hairline),
            ),
          ),
          child: child,
        ),
      ),
    );
  }
}
