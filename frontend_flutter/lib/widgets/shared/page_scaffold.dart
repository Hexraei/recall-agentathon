import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/text_styles.dart';

/// An inner screen: a 44px back chevron, a Fraunces title and one line of
/// secondary text.
///
/// Session flows use [TakeoverScaffold] instead, which replaces the chevron
/// with a plain text action — that is how the design signals there is no
/// dashboard behind the screen.
class PageScaffold extends StatelessWidget {
  const PageScaffold({
    super.key,
    required this.title,
    required this.child,
    this.subtitle,
    this.onBack,
    this.backLabel = 'Back',
    this.trailing,
    this.scrollable = true,
    this.bottomBar,
    this.overlay,
    this.horizontalPadding = 24,
  });

  final String title;
  final String? subtitle;
  final Widget child;
  final VoidCallback? onBack;
  final String backLabel;
  final Widget? trailing;
  final bool scrollable;
  final Widget? bottomBar;

  /// A full-bleed layer drawn over the page — the auto-submit notice.
  final Widget? overlay;
  final double horizontalPadding;

  @override
  Widget build(BuildContext context) {
    final header = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            // The canvas pulls the chevron 12px left so the glyph, not its
            // 44px tap target, lines up with the page gutter.
            Transform.translate(
              offset: const Offset(-12, 0),
              child: Semantics(
                button: true,
                label: backLabel,
                child: SizedBox(
                  width: 44,
                  height: 44,
                  child: Material(
                    color: Colors.transparent,
                    shape: const CircleBorder(),
                    child: InkWell(
                      customBorder: const CircleBorder(),
                      onTap: onBack ?? () => Navigator.of(context).maybePop(),
                      child: const Icon(
                        Icons.arrow_back,
                        size: 22,
                        color: AppColors.ink,
                      ),
                    ),
                  ),
                ),
              ),
            ),
            const Spacer(),
            if (trailing != null) trailing!,
          ],
        ),
        const SizedBox(height: 8),
        Text(title, style: AppText.pageTitle),
        if (subtitle != null) ...[
          const SizedBox(height: 3),
          Text(
            subtitle!,
            style: AppText.bodySmall.copyWith(color: AppColors.grey2),
          ),
        ],
      ],
    );

    return _Frame(
      horizontalPadding: horizontalPadding,
      header: header,
      scrollable: scrollable,
      bottomBar: bottomBar,
      overlay: overlay,
      child: child,
    );
  }
}

/// A full-screen takeover — host lobby, join, lobby, the attempt.
///
/// Top left is a plain text action (Cancel, Leave, Exit quiz, Back to
/// questions), never a back chevron.
class TakeoverScaffold extends StatelessWidget {
  const TakeoverScaffold({
    super.key,
    required this.actionLabel,
    required this.child,
    this.onAction,
    this.actionEnabled = true,
    this.scrollable = false,
    this.bottomBar,
    this.overlay,
    this.horizontalPadding = 24,
  });

  /// Cancel, Leave, Exit quiz, or Back to questions.
  final String actionLabel;
  final VoidCallback? onAction;
  final bool actionEnabled;
  final Widget child;
  final bool scrollable;
  final Widget? bottomBar;
  final Widget? overlay;
  final double horizontalPadding;

  @override
  Widget build(BuildContext context) {
    return _Frame(
      horizontalPadding: horizontalPadding,
      header: Align(
        alignment: Alignment.centerLeft,
        child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(6),
          child: InkWell(
            onTap: actionEnabled ? onAction : null,
            borderRadius: BorderRadius.circular(6),
            child: Container(
              height: 44,
              alignment: Alignment.centerLeft,
              padding: const EdgeInsets.symmetric(horizontal: 6),
              child: Text(
                actionLabel,
                style: AppText.bodyLarge.copyWith(
                  fontWeight: FontWeight.w500,
                  color: actionEnabled
                      ? AppColors.grey2
                      : AppColors.disabledText,
                ),
              ),
            ),
          ),
        ),
      ),
      scrollable: scrollable,
      bottomBar: bottomBar,
      overlay: overlay,
      child: child,
    );
  }
}

class _Frame extends StatelessWidget {
  const _Frame({
    required this.header,
    required this.child,
    required this.scrollable,
    required this.horizontalPadding,
    this.bottomBar,
    this.overlay,
  });

  final Widget header;
  final Widget child;
  final bool scrollable;
  final double horizontalPadding;
  final Widget? bottomBar;
  final Widget? overlay;

  @override
  Widget build(BuildContext context) {
    final pad = EdgeInsets.symmetric(horizontal: horizontalPadding);

    Widget body = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(padding: pad, child: header),
        if (scrollable)
          Expanded(
            child: SingleChildScrollView(
              padding: pad.copyWith(bottom: 28),
              child: child,
            ),
          )
        else
          Expanded(
            child: Padding(padding: pad, child: child),
          ),
        if (bottomBar != null)
          Padding(padding: pad.copyWith(bottom: 26, top: 4), child: bottomBar),
      ],
    );

    if (overlay != null) {
      body = Stack(
        children: [
          Positioned.fill(child: body),
          overlay!,
        ],
      );
    }

    return Scaffold(
      backgroundColor: AppColors.ground,
      body: SafeArea(
        bottom: false,
        child: Padding(padding: const EdgeInsets.only(top: 16), child: body),
      ),
    );
  }
}
