import 'package:flutter/material.dart';
import 'package:mineos_remote_client/mineos_remote_client.dart';
import 'theme.dart';

class DemoReplayChip extends StatelessWidget {
  const DemoReplayChip({super.key});
  @override
  Widget build(BuildContext context) => Tooltip(
    message: 'Recorded sessions, replayed. This is not a live machine.',
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Palette.accent.withValues(alpha: .07),
        border: Border.all(color: Palette.accent.withValues(alpha: .17)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.replay_rounded, size: 14, color: Palette.accent),
          const SizedBox(width: 6),
          Text(
            'Demo replay',
            style: uiText(
              size: 12,
              color: Palette.accent,
              weight: FontWeight.w500,
            ),
          ),
        ],
      ),
    ),
  );
}

class LocalBadge extends StatelessWidget {
  const LocalBadge({super.key});
  @override
  Widget build(BuildContext context) => Tooltip(
    message: 'This recording used the on-device model.',
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: .035),
        border: Border.all(color: Palette.border),
        borderRadius: BorderRadius.circular(7),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.shield_outlined, size: 12, color: Palette.muted),
          const SizedBox(width: 5),
          Text(
            'Local',
            style: uiText(
              size: 11,
              color: Palette.muted,
              weight: FontWeight.w500,
            ),
          ),
        ],
      ),
    ),
  );
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

class StatusChip extends StatefulWidget {
  const StatusChip({super.key, required this.status});
  final SessionStatus status;
  @override
  State<StatusChip> createState() => _StatusChipState();
}

class _StatusChipState extends State<StatusChip>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulse = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  );
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _sync();
  }

  @override
  void didUpdateWidget(StatusChip oldWidget) {
    super.didUpdateWidget(oldWidget);
    _sync();
  }

  void _sync() {
    if (widget.status == SessionStatus.running &&
        !MediaQuery.disableAnimationsOf(context)) {
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
    return AnimatedContainer(
      duration: AppStyle.motion,
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: .09),
        border: Border.all(color: color.withValues(alpha: .16)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          FadeTransition(
            opacity: Tween(begin: .35, end: 1.0).animate(_pulse),
            child: Icon(
              switch (widget.status) {
                SessionStatus.running => Icons.circle,
                SessionStatus.awaitingApproval =>
                  Icons.pause_circle_outline_rounded,
                SessionStatus.done => Icons.check_circle_outline_rounded,
                SessionStatus.failed => Icons.error_outline_rounded,
              },
              size: widget.status == SessionStatus.running ? 6 : 13,
              color: color,
            ),
          ),
          const SizedBox(width: 6),
          Flexible(
            child: AnimatedSwitcher(
              duration: AppStyle.motion,
              child: Text(
                statusLabel(widget.status),
                key: ValueKey(widget.status),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: uiText(size: 12, color: color, weight: FontWeight.w500),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

typedef StatusBadge = StatusChip;

class Entrance extends StatelessWidget {
  const Entrance({super.key, required this.child, this.index = 0});
  final Widget child;
  final int index;
  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
    tween: Tween(
      begin: MediaQuery.disableAnimationsOf(context) ? 1 : 0,
      end: 1,
    ),
    duration: Duration(milliseconds: 380 + index.clamp(0, 5) * 70),
    curve: Curves.easeOutCubic,
    builder: (context, value, child) => Opacity(
      opacity: value,
      child: Transform.translate(
        offset: Offset(0, 12 * (1 - value)),
        child: child,
      ),
    ),
    child: child,
  );
}

class ThinkingIndicator extends StatelessWidget {
  const ThinkingIndicator({super.key, required this.label, this.detail});
  final String label;
  final String? detail;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(Space.lg),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(
          width: 18,
          height: 18,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
        const SizedBox(width: Space.lg),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: uiText(weight: FontWeight.w500)),
              if (detail != null)
                Text(detail!, style: uiText(size: 12, color: Palette.muted)),
            ],
          ),
        ),
      ],
    ),
  );
}

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
  final String? message, actionLabel;
  final VoidCallback? onAction;
  final bool busy;
  @override
  Widget build(BuildContext context) {
    if (busy) return const SessionsSkeleton();
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(Space.xxl),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 380),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  color: Palette.surfaceHigh,
                  border: Border.all(color: Palette.border),
                  borderRadius: AppStyle.rounded,
                ),
                child: Icon(icon, size: 27, color: Palette.accent),
              ),
              const SizedBox(height: Space.xl),
              Text(
                title,
                textAlign: TextAlign.center,
                style: uiText(size: 20, weight: FontWeight.w600),
              ),
              if (message != null) ...[
                const SizedBox(height: Space.sm),
                Text(
                  message!,
                  textAlign: TextAlign.center,
                  style: uiText(size: 14, color: Palette.muted),
                ),
              ],
              if (actionLabel != null) ...[
                const SizedBox(height: Space.xl),
                OutlinedButton.icon(
                  onPressed: onAction,
                  icon: const Icon(Icons.refresh_rounded, size: 17),
                  label: Text(actionLabel!),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class SessionsSkeleton extends StatefulWidget {
  const SessionsSkeleton({super.key});
  @override
  State<SessionsSkeleton> createState() => _SessionsSkeletonState();
}

class _SessionsSkeletonState extends State<SessionsSkeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1000),
  );
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!MediaQuery.disableAnimationsOf(context)) {
      _controller.repeat(reverse: true);
    } else {
      _controller.value = 1;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Widget _bar(double width, double height) => Container(
    width: width,
    height: height,
    decoration: BoxDecoration(
      color: Palette.border,
      borderRadius: BorderRadius.circular(6),
    ),
  );
  @override
  Widget build(BuildContext context) => Semantics(
    label: 'Loading sessions',
    child: FadeTransition(
      opacity: Tween(begin: .35, end: .8).animate(_controller),
      child: ListView.separated(
        shrinkWrap: true,
        padding: const EdgeInsets.all(Space.xl),
        itemCount: 3,
        separatorBuilder: (_, _) => const SizedBox(height: Space.lg),
        itemBuilder: (context, index) => Container(
          padding: const EdgeInsets.all(Space.xl),
          decoration: BoxDecoration(
            color: Palette.surface,
            border: Border.all(color: Palette.border),
            borderRadius: AppStyle.rounded,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _bar(90, 22),
              const SizedBox(height: Space.xl),
              FractionallySizedBox(
                widthFactor: .85,
                child: _bar(double.infinity, 16),
              ),
              const SizedBox(height: Space.sm),
              FractionallySizedBox(
                widthFactor: .6,
                child: _bar(double.infinity, 16),
              ),
              const SizedBox(height: Space.xl),
              _bar(120, 12),
            ],
          ),
        ),
      ),
    ),
  );
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
