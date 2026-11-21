import 'package:flutter/material.dart';
import 'package:mineos_remote_client/mineos_remote_client.dart';

import 'theme.dart';
import 'widgets.dart';

IconData kindIcon(StepKind kind) => switch (kind) {
  StepKind.plan => Icons.alt_route,
  StepKind.modelCall => Icons.memory,
  StepKind.toolCall => Icons.terminal,
  StepKind.approvalRequest => Icons.front_hand_outlined,
  StepKind.result => Icons.flag_outlined,
  StepKind.error => Icons.error_outline,
};

String kindLabel(StepKind kind) => switch (kind) {
  StepKind.plan => 'plan',
  StepKind.modelCall => 'model_call',
  StepKind.toolCall => 'tool_call',
  StepKind.approvalRequest => 'approval_request',
  StepKind.result => 'result',
  StepKind.error => 'error',
};

Color kindColor(StepKind kind) => switch (kind) {
  StepKind.approvalRequest => Palette.awaiting,
  StepKind.error => Palette.failed,
  StepKind.result => Palette.text,
  StepKind.modelCall => Palette.accent,
  _ => Palette.muted,
};

/// One step on the timeline: a rail with the kind icon, a title, the
/// duration, and the detail (monospace) behind a tap.
class StepCard extends StatefulWidget {
  const StepCard({
    super.key,
    required this.step,
    this.isLast = false,
    this.animateIn = true,
  });

  final AgentStep step;
  final bool isLast;
  final bool animateIn;

  @override
  State<StepCard> createState() => _StepCardState();
}

class _StepCardState extends State<StepCard> {
  late bool _open =
      widget.step.kind == StepKind.approvalRequest ||
      widget.step.kind == StepKind.result;

  @override
  Widget build(BuildContext context) {
    final step = widget.step;
    final color = kindColor(step.kind);
    final duration = formatDuration(step.durationMs);

    final card = IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // The rail.
          SizedBox(
            width: 28,
            child: Column(
              children: [
                const SizedBox(height: 12),
                Icon(kindIcon(step.kind), size: 17, color: color),
                const SizedBox(height: 6),
                Expanded(
                  child: Container(
                    width: 1,
                    color: widget.isLast ? Colors.transparent : Palette.border,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Material(
                color: Palette.surface,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                  side: BorderSide(
                    color: step.kind == StepKind.approvalRequest
                        ? Palette.awaiting.withValues(alpha: 0.6)
                        : Palette.border,
                  ),
                ),
                clipBehavior: Clip.antiAlias,
                child: InkWell(
                  onTap: () => setState(() => _open = !_open),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(12, 10, 10, 10),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(
                              '#${step.index} ${kindLabel(step.kind)}',
                              style: mono(size: 10.5, color: color),
                            ),
                            const Spacer(),
                            if (duration.isNotEmpty)
                              Text(
                                duration,
                                style: mono(size: 10.5, color: Palette.faint),
                              ),
                            const SizedBox(width: 4),
                            AnimatedRotation(
                              turns: _open ? 0.5 : 0,
                              duration: const Duration(milliseconds: 180),
                              child: const Icon(
                                Icons.expand_more,
                                size: 16,
                                color: Palette.faint,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          step.title,
                          style: Theme.of(context).textTheme.bodyMedium
                              ?.copyWith(
                                fontWeight: FontWeight.w600,
                                height: 1.3,
                              ),
                        ),
                        AnimatedSize(
                          duration: const Duration(milliseconds: 200),
                          curve: Curves.easeOut,
                          alignment: Alignment.topCenter,
                          child: _open
                              ? Container(
                                  width: double.infinity,
                                  margin: const EdgeInsets.only(top: 8),
                                  padding: const EdgeInsets.all(10),
                                  decoration: BoxDecoration(
                                    color: Palette.background,
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: SelectableText(
                                    step.detail,
                                    style: mono(
                                      size: 11.5,
                                      color: Palette.muted,
                                    ),
                                  ),
                                )
                              : const SizedBox(width: double.infinity),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );

    if (!widget.animateIn) return card;
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: const Duration(milliseconds: 380),
      curve: Curves.easeOutCubic,
      builder: (context, t, child) => Opacity(
        opacity: t,
        child: Transform.translate(
          offset: Offset(0, 14 * (1 - t)),
          child: child,
        ),
      ),
      child: card,
    );
  }
}
