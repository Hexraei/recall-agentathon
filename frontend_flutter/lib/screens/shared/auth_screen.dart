import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/controllers.dart';
import '../../data/repositories.dart';
import '../../models/models.dart';
import '../../routes.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/buttons.dart';
import '../../widgets/shared/misc.dart';

/// Screen 02 — Login / Sign up.
///
/// Sets the shared control vocabulary: 52px inputs and buttons, hairline
/// borders, 10px radius, label above field, error text below.
///
/// States: idle; submitting; invalid credentials, with recovery re-labelled
/// "Reset your password"; network failure, in the neutral band rather than
/// red, with an inline retry; sign up.
class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _name = TextEditingController();
  final _identifier = TextEditingController();
  final _password = TextEditingController();

  bool _signUp = false;
  bool _submitting = false;
  UserRole _role = UserRole.student;

  /// A rejected password — red, because it is user error.
  String? _credentialError;
  String? _passwordFieldError;

  /// A failed request — the neutral band, because it is nobody's fault.
  bool _networkFailed = false;

  @override
  void dispose() {
    _name.dispose();
    _identifier.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _submitting = true;
      _credentialError = null;
      _passwordFieldError = null;
      _networkFailed = false;
    });

    final auth = context.read<AuthController>();
    try {
      // A blank identifier stands in for a request that never left the device.
      if (_identifier.text.trim().isEmpty) {
        throw const _NetworkFailure();
      }
      final user = _signUp
          ? await auth.signUp(
              name: _name.text,
              identifier: _identifier.text,
              password: _password.text,
              role: _role,
            )
          : await auth.signIn(_identifier.text, _password.text);

      if (!mounted) return;
      Navigator.of(context).pushReplacementNamed(
        user.role == UserRole.teacher ? Routes.teacherHome : Routes.studentHome,
      );
    } on AuthException catch (e) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _credentialError = e.message;
        _passwordFieldError = 'Password must be at least 8 characters.';
      });
    } on _NetworkFailure {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _networkFailed = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.ground,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(28, 40, 28, 28),
          child: ConstrainedBox(
            constraints: BoxConstraints(
              minHeight: MediaQuery.sizeOf(context).height - 140,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const RecallMark(size: 26),
                    const SizedBox(width: 10),
                    Text('Recall',
                        style: AppText.sheetTitle.copyWith(fontSize: 20)),
                  ],
                ),
                const SizedBox(height: 30),
                Text(_signUp ? 'Create your account' : 'Sign in',
                    style: AppText.pageTitle),
                const SizedBox(height: 6),
                Text(
                  _signUp
                      ? "Your role decides what you see. It can't be changed later."
                      : 'Use your college email or roll number.',
                  style: AppText.bodyLarge,
                ),
                const SizedBox(height: 24),

                if (_credentialError != null) ...[
                  InfoBand(
                    text: _credentialError!,
                    tone: BandTone.danger,
                    icon: Icons.error_outline,
                  ),
                  const SizedBox(height: 20),
                ],
                if (_networkFailed) ...[
                  InfoBand(
                    text: "We couldn't reach Recall. Your details weren't sent.",
                    icon: Icons.cloud_off_outlined,
                    action: GestureDetector(
                      onTap: _submit,
                      child: Text(
                        'Try again',
                        style: AppText.rowTitle.copyWith(
                            fontSize: 13.5, color: AppColors.accent),
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),
                ],

                if (_signUp) ...[
                  Text("I'm joining as", style: AppText.fieldLabel),
                  const SizedBox(height: 9),
                  Row(
                    children: [
                      Expanded(
                        child: _RoleCard(
                          label: 'Teacher',
                          description: 'Build and host quizzes',
                          selected: _role == UserRole.teacher,
                          onTap: _submitting
                              ? null
                              : () => setState(() => _role = UserRole.teacher),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _RoleCard(
                          label: 'Student',
                          description: 'Join with a PIN',
                          selected: _role == UserRole.student,
                          onTap: _submitting
                              ? null
                              : () => setState(() => _role = UserRole.student),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  AppField(
                    label: 'Display name',
                    controller: _name,
                    enabled: !_submitting,
                  ),
                  const SizedBox(height: 6),
                  Text('This is the name your teacher sees on the roster.',
                      style: AppText.caption.copyWith(fontSize: 12.5)),
                  const SizedBox(height: 16),
                ],

                AppField(
                  label: 'Email or roll number',
                  controller: _identifier,
                  enabled: !_submitting,
                  keyboardType: TextInputType.emailAddress,
                ),
                const SizedBox(height: 16),
                AppField(
                  label: 'Password',
                  controller: _password,
                  obscure: true,
                  enabled: !_submitting,
                  error: _passwordFieldError,
                ),
                if (_signUp) ...[
                  const SizedBox(height: 6),
                  Text('At least 8 characters.',
                      style: AppText.caption.copyWith(fontSize: 12.5)),
                ],

                if (!_signUp) ...[
                  const SizedBox(height: 12),
                  Align(
                    alignment: Alignment.centerRight,
                    child: GestureDetector(
                      onTap: _submitting ? null : () {},
                      child: Text(
                        // Once the password has been rejected, recovery stops
                        // being a question and becomes the next step.
                        _credentialError != null
                            ? 'Reset your password'
                            : 'Forgot password?',
                        style: AppText.rowTitle.copyWith(
                          fontSize: 13.5,
                          color: _submitting
                              ? AppColors.disabledText
                              : AppColors.accent,
                        ),
                      ),
                    ),
                  ),
                ],

                const SizedBox(height: 22),
                FilledAction(
                  label: _signUp
                      ? 'Create account'
                      : (_submitting ? 'Signing in…' : 'Sign in'),
                  busy: _submitting,
                  onPressed: _submitting ? null : _submit,
                ),

                const SizedBox(height: 36),
                Center(
                  child: GestureDetector(
                    onTap: _submitting
                        ? null
                        : () => setState(() {
                              _signUp = !_signUp;
                              _credentialError = null;
                              _passwordFieldError = null;
                              _networkFailed = false;
                            }),
                    child: Text.rich(
                      TextSpan(
                        style: AppText.bodySmall.copyWith(color: AppColors.grey2),
                        children: [
                          TextSpan(
                              text: _signUp
                                  ? 'Already have an account? '
                                  : 'New to Recall? '),
                          TextSpan(
                            text: _signUp ? 'Sign in' : 'Create an account',
                            style: AppText.rowTitle.copyWith(
                              fontSize: 13.5,
                              color: _submitting
                                  ? AppColors.disabledText
                                  : AppColors.accent,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// One of the two role cards at sign-up. Role is presented as permanent.
class _RoleCard extends StatelessWidget {
  const _RoleCard({
    required this.label,
    required this.description,
    required this.selected,
    this.onTap,
  });

  final String label;
  final String description;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? AppColors.accentTint : AppColors.white,
      borderRadius: AppRadii.controlR,
      child: InkWell(
        onTap: onTap,
        borderRadius: AppRadii.controlR,
        child: Container(
          padding: EdgeInsets.all(selected ? 13 : 14),
          decoration: BoxDecoration(
            border: Border.all(
              color: selected ? AppColors.accent : AppColors.hairlineStrong,
              width: selected ? 2 : 1,
            ),
            borderRadius: AppRadii.controlR,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(label,
                  style: AppText.rowTitle.copyWith(
                      color: selected ? AppColors.accentDeep : AppColors.ink)),
              const SizedBox(height: 3),
              Text(description, style: AppText.rowSecondary),
            ],
          ),
        ),
      ),
    );
  }
}

class _NetworkFailure implements Exception {
  const _NetworkFailure();
}
