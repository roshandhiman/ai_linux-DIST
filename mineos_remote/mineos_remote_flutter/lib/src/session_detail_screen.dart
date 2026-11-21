import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mineos_remote_client/mineos_remote_client.dart';

import 'providers.dart';
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

    return Scaffold(
      appBar: AppBar(
        title: const Text('Session'),
        actions: const [DemoReplayChip(), SizedBox(width: 12)],
      ),
      body: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: session == null
              ? (detail.hasError
                    ? StateMessage(
                        icon: Icons.cloud_off,
                        title: 'Could not load this session',
                        message: detail.error.toString(),
                        actionLabel: 'Retry',
                        onAction: () =>
                            ref.invalidate(sessionDetailProvider(id)),
                      )
                    : const StateMessage.loading(title: 'Loading session…'))
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _Header(session: session, timeline: timeline),
                    if (timeline.phase == StreamPhase.reconnecting)
                      _ReconnectBanner(
                        timeline: timeline,
                        onRetry: () =>
                            ref.read(timelineProvider(id).notifier).retryNow(),
                      ),
                    if (timeline.approval != null &&
                        timeline.phase == StreamPhase.holding)
                      _ApprovalBanner(step: timeline.approval!),
                    const Divider(),
                    Expanded(child: _timeline(session, timeline)),
                  ],
                ),
        ),
      ),
    );
  }

  Widget _timeline(AgentSession session, TimelineState t) {
    if (t.steps.isEmpty) {
      return switch (t.phase) {
        StreamPhase.connecting => const StateMessage.loading(
          title: 'Connecting to the replay…',
        ),
        StreamPhase.reconnecting => const StateMessage(
          icon: Icons.wifi_off,
          title: 'Waiting for the connection',
          message: 'Steps appear here as soon as the stream is back.',
        ),
        StreamPhase.finished || StreamPhase.holding => const StateMessage(
          icon: Icons.inbox_outlined,
          title: 'This session has no steps',
        ),
        StreamPhase.live => ThinkingIndicator(
          label: t.thinking ?? 'starting',
          detail: '${session.modelName} on the CPU',
        ),
      };
    }

    final footer = <Widget>[
      if (t.thinking != null && t.phase == StreamPhase.live)
        ThinkingIndicator(
          label: t.thinking!,
          detail: '${session.modelName} via llama.cpp, on the CPU',
        )
      else if (t.phase == StreamPhase.live)
        const ThinkingIndicator(label: 'running the next step'),
      if (t.phase == StreamPhase.finished) _EndOfReplay(session: session),
      if (t.phase == StreamPhase.holding)
        Padding(
          padding: const EdgeInsets.fromLTRB(36, 6, 0, 0),
          child: Text(
            '— paused: nothing happens until someone answers y/N',
            style: mono(size: 11.5, color: Palette.awaiting),
          ),
        ),
    ];

    return ListView(
      controller: _scroll,
      padding: const EdgeInsets.fromLTRB(12, 14, 16, 40),
      children: [
        for (var i = 0; i < t.steps.length; i++)
          StepCard(
            key: ValueKey('${t.cycle}-${t.steps[i].index}'),
            step: t.steps[i],
            isLast: i == t.steps.length - 1 && footer.isEmpty,
          ),
        ...footer,
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
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            s.task,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w700,
              height: 1.3,
            ),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              StatusBadge(status: s.status),
              if (s.isLocal) const LocalBadge(),
            ],
          ),
          const SizedBox(height: 10),
          DefaultTextStyle(
            style: mono(size: 11.5, color: Palette.muted),
            child: Wrap(
              spacing: 14,
              runSpacing: 4,
              children: [
                Text('model ${s.modelName}'),
                Text('provider ${s.provider}'),
                ElapsedText(session: s, startedAt: timeline.startedAt),
                Text(formatSteps(timeline.steps.length)),
              ],
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'route ${s.route}',
            style: mono(size: 11.5, color: Palette.faint),
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
        border: Border.all(color: Palette.awaiting.withValues(alpha: 0.7)),
        borderRadius: BorderRadius.circular(10),
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
                  style: mono(
                    size: 13,
                    color: Palette.awaiting,
                    weight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text('It wants to:', style: mono(size: 11.5, color: Palette.muted)),
          const SizedBox(height: 2),
          SelectableText(
            action,
            style: mono(size: 13, weight: FontWeight.w600),
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
              style: mono(size: 11, color: Palette.muted),
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
      border: Border.all(color: Palette.failed.withValues(alpha: 0.5)),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Row(
      children: [
        const Icon(Icons.wifi_off, size: 16, color: Palette.failed),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            '${timeline.error ?? 'Connection lost'}. '
            'Reconnecting${timeline.retryInSeconds != null ? ' in ${timeline.retryInSeconds}s' : ''}…',
            style: mono(size: 11.5, color: Palette.text),
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
      style: mono(size: 11.5, color: Palette.faint),
    ),
  );
}
