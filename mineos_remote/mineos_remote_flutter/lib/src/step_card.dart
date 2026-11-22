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
  StepKind.plan => 'Plan',
  StepKind.modelCall => 'Model call',
  StepKind.toolCall => 'Tool call',
  StepKind.approvalRequest => 'Approval request',
  StepKind.result => 'Result',
  StepKind.error => 'Error',
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
                  borderRadius: AppStyle.rounded,
                  side: BorderSide(
                    color: step.kind == StepKind.approvalRequest
                        ? Palette.awaiting.withValues(alpha: 0.3)
                        : Palette.border,
                  ),
                ),
                clipBehavior: Clip.antiAlias,
                child: InkWell(
                  onTap: () => setState(() => _open = !_open),
                  child: Padding(
                    padding: const EdgeInsets.all(Space.lg),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                '#${step.index} ${kindLabel(step.kind)}',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: uiText(size: 12, color: color),
                              ),
                            ),
                            if (duration.isNotEmpty)
                              Text(
                                duration,
                                style: uiText(size: 12, color: Palette.faint),
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
                                  padding: const EdgeInsets.all(Space.lg),
                                  decoration: BoxDecoration(
                                    color: Palette.background,
                                    borderRadius: AppStyle.smallRounded,
                                  ),
                                  child: SelectableText(
                                    step.detail,
                                    style: mono(
                                      size: 13,
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

    return widget.animateIn ? Entrance(child: card) : card;
  }
}
