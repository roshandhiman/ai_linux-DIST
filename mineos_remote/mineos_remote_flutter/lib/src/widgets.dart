import 'package:flutter/material.dart';
import 'package:mineos_remote_client/mineos_remote_client.dart';

import 'theme.dart';

/// Always visible: this app shows recordings, never a live machine.
class DemoReplayChip extends StatelessWidget {
  const DemoReplayChip({super.key});

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message:
          'Recorded MineOS sessions, replayed (time-compressed).\n'
          'Not a live machine.',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          border: Border.all(color: Palette.accent.withValues(alpha: 0.6)),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.replay, size: 13, color: Palette.accent),
            const SizedBox(width: 5),
            Text(
              'Demo replay',
              style: mono(
                size: 11,
                color: Palette.accent,
                weight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// "Ran on-device": shown when the session used the local model.
class LocalBadge extends StatelessWidget {
  const LocalBadge({super.key});

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: 'Ran on-device. No data left the machine.',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(
          color: Palette.done.withValues(alpha: 0.10),
          border: Border.all(color: Palette.done.withValues(alpha: 0.45)),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.lock, size: 12, color: Palette.done),
            const SizedBox(width: 4),
            Text(
              'Local',
              style: mono(
                size: 11,
                color: Palette.done,
                weight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

Color statusColor(SessionStatus status) => switch (status) {
  SessionStatus.running => Palette.running,
  SessionStatus.awaitingApproval => Palette.awaiting,
  SessionStatus.done => Palette.done,
  SessionStatus.failed => Palette.failed,
};

String statusLabel(SessionStatus status) => switch (status) {
  SessionStatus.running => 'Running',
  SessionStatus.awaitingApproval => 'Awaiting approval',
  SessionStatus.done => 'Done',
  SessionStatus.failed => 'Failed',
};

/// Coloured status pill. "Running" pulses.
class StatusBadge extends StatefulWidget {
  const StatusBadge({super.key, required this.status});

  final SessionStatus status;

  @override
  State<StatusBadge> createState() => _StatusBadgeState();
}

class _StatusBadgeState extends State<StatusBadge>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulse = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1100),
  );

  @override
  void initState() {
    super.initState();
    _sync();
  }

  @override
  void didUpdateWidget(StatusBadge old) {
    super.didUpdateWidget(old);
    _sync();
  }

  void _sync() {
    if (widget.status == SessionStatus.running) {
      if (!_pulse.isAnimating) _pulse.repeat(reverse: true);
    } else {
      _pulse.stop();
      _pulse.value = 1;
    }
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = statusColor(widget.status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          FadeTransition(
            opacity: Tween(begin: 0.25, end: 1.0).animate(_pulse),
            child: Container(
              width: 7,
              height: 7,
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            ),
          ),
          const SizedBox(width: 6),
          Text(
            statusLabel(widget.status),
            style: mono(size: 11, color: color, weight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}

/// Blinking block cursor plus a label, while the agent works on the next
/// step.
class ThinkingIndicator extends StatefulWidget {
  const ThinkingIndicator({super.key, required this.label, this.detail});

  final String label;
  final String? detail;

  @override
  State<ThinkingIndicator> createState() => _ThinkingIndicatorState();
}

class _ThinkingIndicatorState extends State<ThinkingIndicator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _blink = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 600),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _blink.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 10, 4, 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(
            width: 28,
            child: Padding(
              padding: EdgeInsets.only(top: 2),
              child: SizedBox(
                width: 14,
                height: 14,
                child: CircularProgressIndicator(strokeWidth: 1.6),
              ),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        'thinking… ${widget.label}',
                        style: mono(size: 13, color: Palette.accent),
                      ),
                    ),
                    FadeTransition(
                      opacity: _blink,
                      child: Container(
                        margin: const EdgeInsets.only(left: 4),
                        width: 7,
                        height: 14,
                        color: Palette.accent,
                      ),
                    ),
                  ],
                ),
                if (widget.detail != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(
                      widget.detail!,
                      style: mono(size: 11, color: Palette.muted),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Centered message with an optional action, for loading, empty and error
/// states.
class StateMessage extends StatelessWidget {
  const StateMessage({
    super.key,
    required this.icon,
    required this.title,
    this.message,
    this.actionLabel,
    this.onAction,
    this.busy = false,
  });

  const StateMessage.loading({super.key, this.title = 'Connecting…'})
    : icon = Icons.sync,
      message = null,
      actionLabel = null,
      onAction = null,
      busy = true;

  final IconData icon;
  final String title;
  final String? message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (busy)
              const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            else
              Icon(icon, size: 30, color: Palette.muted),
            const SizedBox(height: 14),
            Text(
              title,
              textAlign: TextAlign.center,
              style: mono(size: 14, weight: FontWeight.w600),
            ),
            if (message != null) ...[
              const SizedBox(height: 6),
              Text(
                message!,
                textAlign: TextAlign.center,
                style: mono(size: 12, color: Palette.muted),
              ),
            ],
            if (actionLabel != null) ...[
              const SizedBox(height: 18),
              OutlinedButton.icon(
                onPressed: onAction,
                icon: const Icon(Icons.refresh, size: 16),
                label: Text(actionLabel!, style: mono(size: 12)),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Palette.accent,
                  side: const BorderSide(color: Palette.border),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

String formatSteps(int n) => n == 1 ? '1 step' : '$n steps';

String formatElapsed(Duration d) {
  if (d.isNegative) d = Duration.zero;
  final h = d.inHours;
  final m = d.inMinutes.remainder(60);
  final s = d.inSeconds.remainder(60);
  if (h > 0) return '${h}h ${m}m';
  if (m > 0) return '${m}m ${s.toString().padLeft(2, '0')}s';
  return '${s}s';
}

String formatDuration(int ms) {
  if (ms <= 0) return '';
  if (ms < 1000) return '$ms ms';
  return '${(ms / 1000).toStringAsFixed(1)} s';
}
