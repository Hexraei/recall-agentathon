/// Where the FastAPI backend (webapp.py) lives, for the two HTTP-backed
/// repositories (MemoryRepository, StudentReportRepository).
///
/// There is no build-flavour switcher here on purpose — this app is built and
/// run once per demo, by hand, and a silently-wrong default is worse than a
/// value that has to be edited before running. Change [baseUrl] to match
/// wherever `webapp.py` is actually listening, then rebuild.
///
/// Values for the common cases:
///
///   Android emulator     http://10.0.2.2:8000
///   iOS simulator         http://localhost:8000
///   Chrome / desktop      http://localhost:8000
///   Real phone, same LAN  http://<your machine's LAN IP>:8000
///   Real phone, no LAN    an ngrok/tunnel URL forwarding to :8000
///
/// (See FLUTTER_CONTEXT.md's "Practical notes" section — this mirrors it.)
class ApiConfig {
  ApiConfig._();

  /// The default assumes a desktop/Chrome run against `webapp.py` on the
  /// same machine. Edit this line for an emulator or a real device.
  static const String baseUrl = 'http://localhost:8000';
}
