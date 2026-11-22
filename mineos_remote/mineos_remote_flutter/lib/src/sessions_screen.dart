import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mineos_remote_client/mineos_remote_client.dart';

import 'about_screen.dart';
import 'connection_screen.dart';
import 'providers.dart';
import 'session_detail_screen.dart';
import 'theme.dart';
import 'widgets.dart';

class SessionsScreen extends ConsumerStatefulWidget {
  const SessionsScreen({super.key});

  @override
  ConsumerState<SessionsScreen> createState() => _SessionsScreenState();
}

class _SessionsScreenState extends ConsumerState<SessionsScreen> {
  Timer? _refresh;

  @override
  void initState() {
    super.initState();
    // Keep the running session's step count fresh without a manual pull.
    _refresh = Timer.periodic(const Duration(seconds: 15), (_) {
      if (!ref.read(sessionsProvider).hasError) {
        ref.invalidate(sessionsProvider);
      }
    });
  }

  @override
  void dispose() {
    _refresh?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final sessions = ref.watch(sessionsProvider);
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 16,
        title: Row(
          children: [
            Text('>', style: mono(size: 16, color: Palette.accent)),
            const SizedBox(width: 8),
            const Text('MineOS Remote'),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Server connection',
            icon: const Icon(Icons.settings_outlined, size: 20),
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(builder: (_) => const ConnectionScreen()),
            ),
          ),
          IconButton(
            tooltip: 'About',
            icon: const Icon(Icons.info_outline, size: 20),
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(builder: (_) => const AboutScreen()),
            ),
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: _Body(
        child: switch (sessions) {
          AsyncValue(:final value?) => RefreshIndicator(
            color: Palette.accent,
            backgroundColor: Palette.surfaceHigh,
            onRefresh: () => ref.refresh(sessionsProvider.future),
            child: value.isEmpty
                ? ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    children: const [
                      SizedBox(height: 120),
                      StateMessage(
                        icon: Icons.inbox_outlined,
                        title: 'No sessions yet',
                        message:
                            'Agent sessions appear here as soon as the '
                            'server has recordings.\nPull down to refresh.',
                      ),
                    ],
                  )
                : ListView.separated(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
                    itemCount: value.length + 1,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (context, i) => i == 0
                        ? const _ListHeader()
                        : SessionCard(session: value[i - 1]),
                  ),
          ),
          AsyncValue(:final error?) => StateMessage(
            icon: Icons.cloud_off,
            title: 'Could not reach the server',
            message: _short(error),
            actionLabel: 'Retry',
            onAction: () => ref.invalidate(sessionsProvider),
          ),
          _ => const StateMessage.loading(title: 'Loading sessions…'),
        },
      ),
    );
  }
}

String _short(Object error) {
  final text = error.toString();
  return text.length > 140 ? '${text.substring(0, 140)}…' : text;
}

/// Keeps the content phone-width on a desktop browser.
class _Body extends StatelessWidget {
  const _Body({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => Align(
    alignment: Alignment.topCenter,
    child: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 720),
      child: child,
    ),
  );
}

class _ListHeader extends StatelessWidget {
  const _ListHeader();

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 4, bottom: 2),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const DemoReplayChip(),
        const SizedBox(height: 10),
        Text(
          'Recorded sessions from a MineOS machine',
          style: mono(size: 12, color: Palette.muted),
        ),
        const SizedBox(height: 4),
      ],
    ),
  );
}

class SessionCard extends StatelessWidget {
  const SessionCard({super.key, required this.session});

  final AgentSession session;

  @override
  Widget build(BuildContext context) {
    final s = session;
    return Material(
      color: Palette.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(
          color: s.status == SessionStatus.awaitingApproval
              ? Palette.awaiting.withValues(alpha: 0.5)
              : Palette.border,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => SessionDetailScreen(sessionId: s.id!, initial: s),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  StatusBadge(status: s.status),
                  const Spacer(),
                  if (s.isLocal) const LocalBadge(),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                s.task,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w600,
                  height: 1.35,
                ),
              ),
              const SizedBox(height: 10),
              DefaultTextStyle(
                style: mono(size: 11.5, color: Palette.muted),
                child: Wrap(
                  spacing: 14,
                  runSpacing: 4,
                  children: [
                    _Meta(icon: Icons.memory, text: s.modelName),
                    _Meta(
                      icon: Icons.timer_outlined,
                      child: ElapsedText(session: s),
                    ),
                    _Meta(
                      icon: Icons.format_list_numbered,
                      text: formatSteps(s.stepCount),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Meta extends StatelessWidget {
  const _Meta({required this.icon, this.text, this.child});

  final IconData icon;
  final String? text;
  final Widget? child;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Icon(icon, size: 13, color: Palette.faint),
      const SizedBox(width: 4),
      child ?? Text(text ?? ''),
    ],
  );
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
