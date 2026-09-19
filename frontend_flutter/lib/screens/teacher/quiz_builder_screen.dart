import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../data/controllers.dart';
import '../../data/repositories.dart';
import '../../models/models.dart';
import '../../theme/colors.dart';
import '../../theme/text_styles.dart';
import '../../widgets/shared/bands.dart';
import '../../widgets/shared/buttons.dart';
import '../../widgets/shared/misc.dart';
import '../../widgets/shared/page_scaffold.dart';
import '../../widgets/shared/sheets.dart';

/// Screen 05 — Quiz Builder.
///
/// Add question is outlined, Save quiz is filled: outlined means a repeatable
/// step, filled means commit, and that distinction holds app-wide.
///
/// States: no questions yet, with a dashed empty slot; composing; validation
/// errors shown per field, with Add question disabled until all are resolved;
/// saving; leaving with unsaved changes, where Keep editing is the filled
/// action and Discard is a red outline.
class QuizBuilderScreen extends StatefulWidget {
  const QuizBuilderScreen({super.key, this.quiz});

  final Quiz? quiz;

  @override
  State<QuizBuilderScreen> createState() => _QuizBuilderScreenState();
}

class _QuizBuilderScreenState extends State<QuizBuilderScreen> {
  late final QuizBuilderController _c;
  late final TextEditingController _title;
  late final TextEditingController _questionText;
  late final TextEditingController _topic;
  final _options = List.generate(4, (_) => TextEditingController());
  final _topicFocus = FocusNode();
  bool _topicOpen = false;

  @override
  void initState() {
    super.initState();
    _c = QuizBuilderController(
      context.read<QuizRepository>(),
      existing: widget.quiz,
    )..loadTopics();
    _title = TextEditingController(text: _c.title);
    _questionText = TextEditingController();
    _topic = TextEditingController();
    _topicFocus.addListener(
      () => setState(() => _topicOpen = _topicFocus.hasFocus),
    );
  }

  @override
  void dispose() {
    _c.dispose();
    _title.dispose();
    _questionText.dispose();
    _topic.dispose();
    _topicFocus.dispose();
    for (final o in _options) {
      o.dispose();
    }
    super.dispose();
  }

  Future<bool> _confirmLeave() async {
    if (!_c.dirty) return true;
    final n = _c.questions.length;
    final leave = await showAppSheet<bool>(
      context: context,
      builder: (context) => ConfirmSheet(
        title: 'Leave without saving?',
        body:
            'A title, a time limit and $n question${n == 1 ? '' : 's'} are '
            'not saved yet. Leaving now loses all of it.',
        // Keep editing is the filled action: the safe path is the one being
        // recommended, and discarding is the red outline beneath it.
        confirmLabel: 'Discard changes',
        cancelLabel: 'Keep editing',
        destructive: true,
        confirmIsFilled: false,
      ),
    );
    return leave == true;
  }

  Future<void> _save() async {
    final quiz = await _c.save();
    if (quiz != null && mounted) Navigator.of(context).pop(quiz);
  }

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider.value(
      value: _c,
      child: Consumer<QuizBuilderController>(
        builder: (context, c, _) {
          final n = c.questions.length;
          return PopScope(
            canPop: false,
            onPopInvokedWithResult: (didPop, _) async {
              if (didPop) return;
              if (await _confirmLeave() && mounted) {
                if (context.mounted) Navigator.of(context).pop();
              }
            },
            child: PageScaffold(
              title: widget.quiz == null ? 'New quiz' : 'Edit quiz',
              subtitle: n == 0
                  ? 'No questions yet'
                  : '$n question${n == 1 ? '' : 's'} added · '
                        '${c.dirty ? 'not saved yet' : 'saved'}',
              backLabel: 'Back to my quizzes',
              onBack: () async {
                if (await _confirmLeave() && context.mounted) {
                  Navigator.of(context).pop();
                }
              },
              bottomBar: Row(
                children: [
                  Expanded(
                    child: FilledAction(
                      label: c.saving ? 'Saving…' : 'Save quiz',
                      busy: c.saving,
                      onPressed: c.canSave && !c.saving ? _save : null,
                    ),
                  ),
                  const SizedBox(width: 10),
                  SizedBox(
                    width: 110,
                    child: OutlinedAction(
                      label: 'Discard',
                      destructive: true,
                      onPressed: c.saving
                          ? null
                          : () async {
                              if (await _confirmLeave() && context.mounted) {
                                Navigator.of(context).pop();
                              }
                            },
                    ),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 20),
                  _details(c),
                  const SectionLabel('Add a question'),
                  _composer(c),
                  SectionLabel('Questions so far · $n', bottom: 10),
                  if (c.questions.isEmpty)
                    const DashedSlot(
                      text:
                          'No questions yet. The first one you add appears here.',
                    )
                  else
                    RowCard(
                      children: [
                        for (var i = 0; i < c.questions.length; i++)
                          _QuestionRow(
                            index: i + 1,
                            question: c.questions[i],
                            onDelete: () => c.removeQuestion(c.questions[i].id),
                          ),
                      ],
                    ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _details(QuizBuilderController c) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppField(
          label: 'Quiz title',
          controller: _title,
          error: c.titleError,
          onChanged: (v) {
            c.title = v;
            c.touch();
          },
        ),
        const SizedBox(height: 18),
        Text('Time limit for the whole quiz', style: AppText.fieldLabel),
        const SizedBox(height: 7),
        _TimeLimitStepper(
          value: int.tryParse(c.timeLimit) ?? 0,
          error: c.timeLimitError,
          onChanged: (v) {
            c.timeLimit = v.toString();
            c.touch();
          },
        ),
        const SizedBox(height: 7),
        Text(
          'Counts down once for everyone from the moment you start the '
          'session. There is no timer on individual questions.',
          style: AppText.caption.copyWith(fontSize: 12.5, height: 18 / 12.5),
        ),
      ],
    );
  }

  Widget _composer(QuizBuilderController c) {
    return AppCard(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          AppField(
            label: 'Question ${c.questions.length + 1}',
            controller: _questionText,
            maxLines: 2,
            error: c.questionError,
            onChanged: (v) {
              c.questionText = v;
              c.touch();
            },
          ),
          const SizedBox(height: 16),
          _TopicCombobox(
            controller: _topic,
            focusNode: _topicFocus,
            open: _topicOpen,
            error: c.topicError,
            suggestions: c.filteredTopics(),
            onChanged: (v) {
              c.topic = v;
              c.touch();
            },
            onPick: (t) {
              _topic.text = t;
              c.topic = t;
              _topicFocus.unfocus();
              c.touch();
            },
          ),
          const SizedBox(height: 7),
          Text(
            'One topic per question. Type to reuse a topic from an earlier '
            'quiz, or name a new one.',
            style: AppText.caption.copyWith(fontSize: 12.5, height: 18 / 12.5),
          ),
          const SizedBox(height: 18),
          Text(
            'Fill all four options, then tap the circle beside the correct one.',
            style: AppText.caption.copyWith(fontSize: 12.5),
          ),
          const SizedBox(height: 10),
          for (var i = 0; i < 4; i++) ...[
            if (i > 0) const SizedBox(height: 8),
            _OptionRow(
              letter: Question.letters[i],
              controller: _options[i],
              isCorrect: c.correctIndex == i,
              error: c.optionError(i),
              onChanged: (v) {
                c.options[i] = v;
                c.touch();
              },
              onMarkCorrect: () {
                c.correctIndex = i;
                c.touch();
              },
            ),
          ],
          if (c.correctError != null) ...[
            const SizedBox(height: 8),
            Text(
              c.correctError!,
              style: AppText.caption.copyWith(
                fontSize: 12.5,
                color: AppColors.red,
              ),
            ),
          ],
          const SizedBox(height: 18),
          OutlinedAction(
            label: 'Add question',
            // Disabled until the question, its options and its correct answer
            // are all resolved.
            onPressed: c.canAddQuestion
                ? () {
                    if (c.addQuestion()) {
                      _questionText.clear();
                      for (final o in _options) {
                        o.clear();
                      }
                      // The topic carries forward: consecutive questions
                      // usually share one.
                    }
                  }
                : null,
          ),
        ],
      ),
    );
  }
}

class _TimeLimitStepper extends StatelessWidget {
  const _TimeLimitStepper({
    required this.value,
    required this.onChanged,
    this.error,
  });

  final int value;
  final ValueChanged<int> onChanged;
  final String? error;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          height: AppMetrics.control,
          decoration: BoxDecoration(
            color: AppColors.white,
            border: Border.all(
              color: error != null ? AppColors.red : AppColors.hairlineStrong,
            ),
            borderRadius: AppRadii.controlR,
          ),
          child: Row(
            children: [
              _StepButton(
                icon: Icons.remove,
                label: 'Decrease time limit by 5 minutes',
                onTap: value > 5 ? () => onChanged(value - 5) : null,
              ),
              Expanded(
                child: Center(
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.baseline,
                    textBaseline: TextBaseline.alphabetic,
                    children: [
                      Text(
                        '$value',
                        style: AppText.rowTitle.copyWith(fontSize: 17),
                      ),
                      const SizedBox(width: 5),
                      Text('min', style: AppText.rowSecondary),
                    ],
                  ),
                ),
              ),
              _StepButton(
                icon: Icons.add,
                label: 'Increase time limit by 5 minutes',
                onTap: value < 180 ? () => onChanged(value + 5) : null,
              ),
            ],
          ),
        ),
        if (error != null) ...[
          const SizedBox(height: 6),
          Text(
            error!,
            style: AppText.caption.copyWith(
              fontSize: 12.5,
              color: AppColors.red,
            ),
          ),
        ],
      ],
    );
  }
}

class _StepButton extends StatelessWidget {
  const _StepButton({required this.icon, required this.label, this.onTap});

  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: label,
      child: SizedBox(
        width: 50,
        height: AppMetrics.control,
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onTap,
            child: Icon(
              icon,
              size: 18,
              color: onTap == null ? AppColors.disabled : AppColors.grey1,
            ),
          ),
        ),
      ),
    );
  }
}

/// The combobox that filters existing topics as you type. It is deliberately
/// the only way a topic is entered, so "Hash table" and "Hash tables" cannot
/// split into two topics across quizzes.
class _TopicCombobox extends StatelessWidget {
  const _TopicCombobox({
    required this.controller,
    required this.focusNode,
    required this.open,
    required this.suggestions,
    required this.onChanged,
    required this.onPick,
    this.error,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final bool open;
  final List<String> suggestions;
  final ValueChanged<String> onChanged;
  final ValueChanged<String> onPick;
  final String? error;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('Topic', style: AppText.fieldLabel),
        const SizedBox(height: 7),
        Container(
          height: AppMetrics.control,
          decoration: BoxDecoration(
            color: AppColors.white,
            border: Border.all(
              color: error != null ? AppColors.red : AppColors.hairlineStrong,
            ),
            borderRadius: AppRadii.controlR,
          ),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: controller,
                  focusNode: focusNode,
                  onChanged: onChanged,
                  style: AppText.bodyLarge.copyWith(color: AppColors.ink),
                  decoration: InputDecoration(
                    hintText: 'Collisions',
                    hintStyle: AppText.bodyLarge.copyWith(
                      color: AppColors.disabledText,
                    ),
                    border: InputBorder.none,
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 15,
                    ),
                  ),
                ),
              ),
              const Padding(
                padding: EdgeInsets.only(right: 12),
                child: Icon(
                  Icons.expand_more,
                  size: 18,
                  color: AppColors.grey3,
                ),
              ),
            ],
          ),
        ),
        if (open && suggestions.isNotEmpty)
          Container(
            margin: const EdgeInsets.only(top: 6),
            constraints: const BoxConstraints(maxHeight: 176),
            decoration: BoxDecoration(
              color: AppColors.white,
              border: Border.all(color: AppColors.hairline),
              borderRadius: AppRadii.controlR,
            ),
            clipBehavior: Clip.antiAlias,
            child: ListView.builder(
              shrinkWrap: true,
              padding: EdgeInsets.zero,
              itemCount: suggestions.length,
              itemBuilder: (context, i) => InkWell(
                onTap: () => onPick(suggestions[i]),
                child: Container(
                  constraints: const BoxConstraints(minHeight: 44),
                  alignment: Alignment.centerLeft,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    border: i == 0
                        ? null
                        : const Border(
                            top: BorderSide(color: AppColors.hairlineSoft),
                          ),
                  ),
                  child: Text(suggestions[i], style: AppText.bodySmall),
                ),
              ),
            ),
          ),
        if (error != null) ...[
          const SizedBox(height: 6),
          Text(
            error!,
            style: AppText.caption.copyWith(
              fontSize: 12.5,
              color: AppColors.red,
            ),
          ),
        ],
      ],
    );
  }
}

/// One option row: a radio marking the correct answer, the letter, the text.
class _OptionRow extends StatelessWidget {
  const _OptionRow({
    required this.letter,
    required this.controller,
    required this.isCorrect,
    required this.onChanged,
    required this.onMarkCorrect,
    this.error,
  });

  final String letter;
  final TextEditingController controller;
  final bool isCorrect;
  final ValueChanged<String> onChanged;
  final VoidCallback onMarkCorrect;
  final String? error;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            Semantics(
              button: true,
              checked: isCorrect,
              label: 'Mark option $letter as correct',
              child: SizedBox(
                width: 44,
                height: 44,
                child: Material(
                  color: Colors.transparent,
                  shape: const CircleBorder(),
                  child: InkWell(
                    customBorder: const CircleBorder(),
                    onTap: onMarkCorrect,
                    child: Center(
                      child: Container(
                        width: 20,
                        height: 20,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: isCorrect
                                ? AppColors.accent
                                : AppColors.hairlineStrong,
                            width: isCorrect ? 6 : 1.5,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
            SizedBox(
              width: 20,
              child: Text(
                letter,
                style: AppText.rowTitle.copyWith(
                  fontSize: 13.5,
                  color: AppColors.grey2,
                ),
              ),
            ),
            Expanded(
              child: Container(
                height: 46,
                decoration: BoxDecoration(
                  color: AppColors.white,
                  border: Border.all(
                    color: error != null
                        ? AppColors.red
                        : AppColors.hairlineStrong,
                  ),
                  borderRadius: AppRadii.controlR,
                ),
                child: TextField(
                  controller: controller,
                  onChanged: onChanged,
                  style: AppText.optionText.copyWith(color: AppColors.ink),
                  inputFormatters: [LengthLimitingTextInputFormatter(140)],
                  decoration: const InputDecoration(
                    border: InputBorder.none,
                    isDense: true,
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 13,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
        if (error != null)
          Padding(
            padding: const EdgeInsets.only(left: 64, top: 4),
            child: Text(
              error!,
              style: AppText.caption.copyWith(
                fontSize: 12,
                color: AppColors.red,
              ),
            ),
          ),
      ],
    );
  }
}

class _QuestionRow extends StatelessWidget {
  const _QuestionRow({
    required this.index,
    required this.question,
    required this.onDelete,
  });

  final int index;
  final Question question;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 12, 6, 12),
      child: Row(
        children: [
          Container(
            width: 22,
            height: 22,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: AppColors.ground,
              borderRadius: BorderRadius.circular(11),
            ),
            child: Text(
              '$index',
              style: AppText.captionSmall.copyWith(
                fontWeight: FontWeight.w600,
                color: AppColors.grey2,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  question.text,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: AppText.bodySmall.copyWith(color: AppColors.ink),
                ),
                const SizedBox(height: 5),
                TagPill(text: question.topic),
              ],
            ),
          ),
          SizedBox(
            width: 44,
            height: 44,
            child: IconButton(
              tooltip: 'Delete question $index',
              icon: const Icon(Icons.close, size: 18, color: AppColors.grey3),
              onPressed: onDelete,
            ),
          ),
        ],
      ),
    );
  }
}
