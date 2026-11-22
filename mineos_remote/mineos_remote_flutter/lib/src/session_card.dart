import 'package:flutter/material.dart';
import 'package:mineos_remote_client/mineos_remote_client.dart';
import 'session_detail_screen.dart';
import 'theme.dart';
import 'widgets.dart';

class SessionCard extends StatefulWidget {
  const SessionCard({
    super.key,
    required this.session,
    this.fillHeight = false,
  });
  final AgentSession session;
  final bool fillHeight;
  @override
  State<SessionCard> createState() => _SessionCardState();
}

class _SessionCardState extends State<SessionCard> {
  bool _hovered = false, _pressed = false;
  @override
  Widget build(BuildContext context) {
    final s = widget.session;
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: AnimatedScale(
        scale: _pressed ? .987 : 1,
        duration: AppStyle.motion,
        child: AnimatedContainer(
          duration: AppStyle.motion,
          decoration: BoxDecoration(
            borderRadius: AppStyle.rounded,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: _hovered ? .18 : .06),
                blurRadius: _hovered ? 24 : 8,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: Material(
            color: _hovered ? Palette.surfaceHigh : Palette.surface,
            shape: RoundedRectangleBorder(
              borderRadius: AppStyle.rounded,
              side: BorderSide(
                color: _hovered
                    ? Palette.accent.withValues(alpha: .35)
                    : Palette.border,
              ),
            ),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              onHighlightChanged: (value) => setState(() => _pressed = value),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) =>
                      SessionDetailScreen(sessionId: s.id!, initial: s),
                ),
              ),
              child: Padding(
                padding: const EdgeInsets.all(Space.xl),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: Space.md,
                      runSpacing: Space.sm,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        StatusChip(status: s.status),
                        Text(
                          '#${s.id.toString().padLeft(3, '0')}',
                          style: uiText(size: 12, color: Palette.faint),
                        ),
                      ],
                    ),
                    const SizedBox(height: Space.lg),
                    SizedBox(
                      height: 72 * MediaQuery.textScalerOf(context).scale(1),
                      child: Text(
                        s.task,
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                        style: uiText(
                          size: 16,
                          weight: FontWeight.w600,
                          height: 1.45,
                        ),
                      ),
                    ),
                    const SizedBox(height: Space.lg),
                    Tooltip(
                      message: s.modelName,
                      child: Row(
                        children: [
                          const Icon(
                            Icons.memory_rounded,
                            size: 16,
                            color: Palette.faint,
                          ),
                          const SizedBox(width: Space.sm),
                          Expanded(
                            child: Text(
                              s.modelName,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: uiText(size: 12, color: Palette.muted),
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (widget.fillHeight)
                      const Spacer()
                    else
                      const SizedBox(height: Space.lg),
                    const Divider(),
                    const SizedBox(height: Space.lg),
                    Wrap(
                      alignment: WrapAlignment.spaceBetween,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      spacing: Space.lg,
                      runSpacing: Space.md,
                      children: [
                        Wrap(
                          spacing: Space.lg,
                          runSpacing: Space.sm,
                          children: [
                            Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(
                                  Icons.schedule_rounded,
                                  size: 14,
                                  color: Palette.faint,
                                ),
                                const SizedBox(width: 5),
                                DefaultTextStyle(
                                  style: uiText(size: 12, color: Palette.muted),
                                  child: ElapsedText(session: s),
                                ),
                              ],
                            ),
                            Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(
                                  Icons.segment_rounded,
                                  size: 14,
                                  color: Palette.faint,
                                ),
                                const SizedBox(width: 5),
                                Text(
                                  formatSteps(s.stepCount),
                                  style: uiText(size: 12, color: Palette.muted),
                                ),
                              ],
                            ),
                          ],
                        ),
                        if (s.isLocal) const LocalBadge(),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Elapsed time. Ticks every second while the session is running; for a
/// finished or paused session it is how long the recording took.
class ElapsedText extends StatelessWidget {
  const ElapsedText({super.key, required this.session, this.startedAt});

  final AgentSession session;

  /// Overrides session.startedAt, e.g. the current replay loop's start.
  final DateTime? startedAt;

  @override
  Widget build(BuildContext context) {
    final start = (startedAt ?? session.startedAt).toLocal();
    if (session.status != SessionStatus.running) {
      return Text(
        formatElapsed(session.updatedAt.difference(session.startedAt)),
      );
    }
    return StreamBuilder<int>(
      stream: Stream<int>.periodic(const Duration(seconds: 1), (i) => i),
      builder: (context, _) =>
          Text('${formatElapsed(DateTime.now().difference(start))} elapsed'),
    );
  }
}
