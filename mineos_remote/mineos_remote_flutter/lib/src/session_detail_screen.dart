import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mineos_remote_client/mineos_remote_client.dart';

import 'providers.dart';
import 'app_scaffold.dart';
import 'sessions_screen.dart';
import 'step_card.dart';
import 'theme.dart';
import 'widgets.dart';

class SessionDetailScreen extends ConsumerStatefulWidget {
  const SessionDetailScreen({super.key, required this.sessionId, this.initial});

  final int sessionId;

  /// The card's copy of the session, shown until get() answers.
  final AgentSession? initial;

  @override
  ConsumerState<SessionDetailScreen> createState() =>
      _SessionDetailScreenState();
}

class _SessionDetailScreenState extends ConsumerState<SessionDetailScreen> {
  final _scroll = ScrollController();

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  /// Follow the newest step, unless the viewer has scrolled up to read.
  void _followNewest() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      final pos = _scroll.position;
      if (pos.maxScrollExtent - pos.pixels > 420) return;
      _scroll.animateTo(
        pos.maxScrollExtent,
        duration: const Duration(milliseconds: 350),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final id = widget.sessionId;
    final detail = ref.watch(sessionDetailProvider(id));
    final timeline = ref.watch(timelineProvider(id));

    ref.listen(timelineProvider(id), (prev, next) {
      if (next.steps.length != (prev?.steps.length ?? 0) ||
          next.thinking != prev?.thinking ||
          next.phase != prev?.phase) {
        _followNewest();
      }
    });

    final session = detail.value?.session ?? widget.initial;

    return AppScaffold(
      title: 'Session details',
      showBack: true,
      body: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 960),
          child: session == null
              ? (detail.hasError
                    ? StateMessage(
                        icon: Icons.cloud_off_outlined,
                        title: 'This session is out of reach',
                        message:
                            'Check your connection and try loading it again.',
                        actionLabel: 'Try again',
                        onAction: () =>
                            ref.invalidate(sessionDetailProvider(id)),
                      )
                    : const StateMessage.loading())
              : _timeline(session, timeline),
        ),
      ),
    );
  }

  Widget _timeline(AgentSession session, TimelineState t) {
    final emptyState = switch (t.phase) {
      StreamPhase.connecting => const StateMessage.loading(
        title: 'Connecting to the replay…',
      ),
      StreamPhase.reconnecting => const StateMessage(
        icon: Icons.wifi_off_rounded,
        title: 'Waiting to reconnect',
        message: 'Your timeline will continue when the connection returns.',
      ),
      StreamPhase.finished || StreamPhase.holding => const StateMessage(
        icon: Icons.inbox_outlined,
        title: 'No steps in this recording',
      ),
      StreamPhase.live => ThinkingIndicator(
        label: t.thinking ?? 'Getting started',
        detail: '${session.modelName} on the CPU',
      ),
    };
    return ListView(
      controller: _scroll,
      padding: const EdgeInsets.fromLTRB(
        Space.lg,
        Space.xl,
        Space.lg,
        Space.xxxl,
      ),
      children: [
        _Header(session: session, timeline: t),
        if (t.usingPolling)
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: Space.lg,
              vertical: Space.md,
            ),
            child: Text(
              'Refreshing every 2 seconds · replay stream reconnecting',
              style: uiText(size: 12, color: Palette.accent),
            ),
          ),
        if (t.phase == StreamPhase.reconnecting)
          _ReconnectBanner(
            timeline: t,
            onRetry: () => ref
                .read(timelineProvider(widget.sessionId).notifier)
                .retryNow(),
          ),
        if (t.approval != null && t.phase == StreamPhase.holding)
          _ApprovalBanner(step: t.approval!),
        Padding(
          padding: const EdgeInsets.fromLTRB(
            Space.lg,
            Space.xl,
            Space.lg,
            Space.xl,
          ),
          child: Row(
            children: [
              const Icon(
                Icons.account_tree_outlined,
                size: 18,
                color: Palette.muted,
              ),
              const SizedBox(width: Space.sm),
              Text(
                'Activity timeline',
                style: uiText(size: 15, weight: FontWeight.w600),
              ),
              const Spacer(),
              Text(
                formatSteps(t.steps.length),
                style: uiText(size: 12, color: Palette.muted),
              ),
            ],
          ),
        ),
        if (t.steps.isEmpty) SizedBox(height: 300, child: emptyState),
        for (var i = 0; i < t.steps.length; i++)
          StepCard(
            key: ValueKey('${t.cycle}-${t.steps[i].index}'),
            step: t.steps[i],
            isLast: i == t.steps.length - 1 && t.phase != StreamPhase.live,
          ),
        if (t.steps.isNotEmpty && t.phase == StreamPhase.live)
          ThinkingIndicator(
            label: t.thinking ?? 'Working on the next step',
            detail: '${session.modelName} via llama.cpp, on the CPU',
          ),
        if (t.steps.isNotEmpty && t.phase == StreamPhase.finished)
          _EndOfReplay(session: session),
        if (t.steps.isNotEmpty && t.phase == StreamPhase.holding)
          Padding(
            padding: const EdgeInsets.only(left: 44, top: Space.md),
            child: Text(
              'Paused until someone answers the approval prompt.',
              style: uiText(size: 13, color: Palette.awaiting),
            ),
          ),
      ],
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.session, required this.timeline});

  final AgentSession session;
  final TimelineState timeline;

  @override
  Widget build(BuildContext context) {
    final s = session;
    return Container(
      padding: const EdgeInsets.all(Space.xl),
      decoration: BoxDecoration(
        color: Palette.surface,
        border: Border.all(color: Palette.border),
        borderRadius: AppStyle.rounded,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: Space.sm,
            runSpacing: Space.sm,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              const DemoReplayChip(),
              StatusChip(status: s.status),
              if (s.isLocal) const LocalBadge(),
            ],
          ),
          const SizedBox(height: Space.xl),
          Text(
            s.task,
            style: uiText(
              size: MediaQuery.sizeOf(context).width < 700 ? 20 : 24,
              weight: FontWeight.w600,
              height: 1.4,
            ),
          ),
          const SizedBox(height: Space.xl),
          const Divider(),
          const SizedBox(height: Space.lg),
          DefaultTextStyle(
            style: uiText(size: 12, color: Palette.muted),
            child: Wrap(
              spacing: Space.lg,
              runSpacing: Space.sm,
              children: [
                Text('Model · ${s.modelName}'),
                Text('Provider · ${s.provider}'),
                ElapsedText(session: s, startedAt: timeline.startedAt),
                Text(formatSteps(timeline.steps.length)),
              ],
            ),
          ),
          const SizedBox(height: Space.md),
          Text(
            'Route · ${s.route}',
            style: uiText(size: 12, color: Palette.faint),
          ),
        ],
      ),
    );
  }
}

class _ApprovalBanner extends StatelessWidget {
  const _ApprovalBanner({required this.step});

  final AgentStep step;

  @override
  Widget build(BuildContext context) {
    // The first line of the real prompt is "The assistant wants to: <action>".
    final firstLine = step.detail.split('\n').first;
    final action = firstLine.startsWith('The assistant wants to: ')
        ? firstLine.substring('The assistant wants to: '.length)
        : step.title;
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(
        color: Palette.awaiting.withValues(alpha: 0.10),
        border: Border.all(color: Palette.awaiting.withValues(alpha: 0.25)),
        borderRadius: AppStyle.rounded,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.pause_circle_filled,
                size: 18,
                color: Palette.awaiting,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Agent paused: waiting for approval',
                  style: uiText(
                    size: 13,
                    color: Palette.awaiting,
                    weight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text('It wants to:', style: uiText(size: 11.5, color: Palette.muted)),
          const SizedBox(height: 2),
          SelectableText(
            action,
            style: uiText(size: 13, weight: FontWeight.w600),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: null,
                  icon: const Icon(Icons.check, size: 16),
                  label: const Text('Approve'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: null,
                  icon: const Icon(Icons.close, size: 16),
                  label: const Text('Deny'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Center(
            child: Text(
              'Coming next: approve from your phone',
              style: uiText(size: 11, color: Palette.muted),
            ),
          ),
        ],
      ),
    );
  }
}

class _ReconnectBanner extends StatelessWidget {
  const _ReconnectBanner({required this.timeline, required this.onRetry});

  final TimelineState timeline;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.fromLTRB(16, 0, 16, 12),
    padding: const EdgeInsets.fromLTRB(12, 8, 4, 8),
    decoration: BoxDecoration(
      color: Palette.failed.withValues(alpha: 0.10),
      border: Border.all(color: Palette.failed.withValues(alpha: 0.25)),
      borderRadius: AppStyle.smallRounded,
    ),
    child: Row(
      children: [
        const Icon(Icons.wifi_off, size: 16, color: Palette.failed),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            '${timeline.error ?? 'Connection lost'}. '
            'Reconnecting${timeline.retryInSeconds != null ? ' in ${timeline.retryInSeconds}s' : ''}…',
            style: uiText(size: 11.5, color: Palette.text),
          ),
        ),
        TextButton(onPressed: onRetry, child: const Text('Retry now')),
      ],
    ),
  );
}

class _EndOfReplay extends StatelessWidget {
  const _EndOfReplay({required this.session});

  final AgentSession session;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(36, 6, 0, 0),
    child: Text(
      '— end of recording${session.outcome != null ? ' (outcome: ${session.outcome})' : ''}',
      style: uiText(size: 11.5, color: Palette.faint),
    ),
  );
}
