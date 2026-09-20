import 'package:flutter/material.dart';

/// Registered once on the app's [Navigator] so any screen can be told when
/// it has become visible again, rather than only when the specific route it
/// pushed happens to complete.
///
/// That distinction matters here: a dashboard that refreshes via
/// `pushNamed(...).then((_) => _reload())` only reloads when *that* pushed
/// route itself is popped. Several flows in this app push several levels
/// deep and then replace a route partway through (a lobby handing off to the
/// question view, say) before finally returning home with `popUntil`. The
/// replacement completes and consumes the very first route's future early —
/// before anything the user did downstream has happened — so the `.then()`
/// never fires again for the rest of the trip. [RouteAware.didPopNext] does
/// not have that problem: it fires whenever anything above this route is
/// popped and this route is exposed again, however many levels that was.
final routeObserver = RouteObserver<PageRoute<dynamic>>();
