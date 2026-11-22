import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mineos_remote_client/mineos_remote_client.dart';
import 'app_scaffold.dart';
import 'providers.dart';
import 'session_card.dart';
import 'theme.dart';
import 'widgets.dart';
export 'session_card.dart' show ElapsedText;

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
    return AppScaffold(
      title: 'Sessions',
      actions: [
        IconButton(
          tooltip: 'Refresh sessions',
          onPressed: () => ref.invalidate(sessionsProvider),
          icon: const Icon(Icons.refresh_rounded, size: 20),
        ),
      ],
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => showNewTaskInfo(context),
        icon: const Icon(Icons.add_rounded, size: 20),
        label: const Text('New task'),
      ),
      body: LayoutBuilder(
        builder: (context, constraints) {
          final padding = constraints.maxWidth < 600 ? Space.lg : Space.xxl;
          return Align(
            alignment: Alignment.topCenter,
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: AppStyle.pageWidth),
              child: switch (sessions) {
                AsyncValue(:final value?) => RefreshIndicator(
                  onRefresh: () => ref.refresh(sessionsProvider.future),
                  child: CustomScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    slivers: [
                      SliverPadding(
                        padding: EdgeInsets.fromLTRB(
                          padding,
                          Space.xxl,
                          padding,
                          Space.xl,
                        ),
                        sliver: SliverToBoxAdapter(
                          child: _Overview(sessions: value),
                        ),
                      ),
                      if (value.isEmpty)
                        const SliverFillRemaining(
                          hasScrollBody: false,
                          child: StateMessage(
                            icon: Icons.inbox_outlined,
                            title: 'A little quiet here',
                            message:
                                'Your recorded agent sessions will appear here. Pull down to check for updates.',
                          ),
                        )
                      else
                        SliverPadding(
                          padding: EdgeInsets.fromLTRB(
                            padding,
                            0,
                            padding,
                            112,
                          ),
                          sliver: constraints.maxWidth >= 850
                              ? SliverGrid(
                                  delegate: SliverChildBuilderDelegate(
                                    (context, i) => Entrance(
                                      index: i,
                                      child: SessionCard(
                                        session: value[i],
                                        fillHeight: true,
                                      ),
                                    ),
                                    childCount: value.length,
                                  ),
                                  gridDelegate:
                                      SliverGridDelegateWithFixedCrossAxisCount(
                                        crossAxisCount: 2,
                                        mainAxisSpacing: Space.lg,
                                        crossAxisSpacing: Space.lg,
                                        mainAxisExtent:
                                            300 *
                                            MediaQuery.textScalerOf(
                                              context,
                                            ).scale(1),
                                      ),
                                )
                              : SliverList.separated(
                                  itemCount: value.length,
                                  separatorBuilder: (_, _) =>
                                      const SizedBox(height: Space.lg),
                                  itemBuilder: (context, i) => Entrance(
                                    index: i,
                                    child: SessionCard(session: value[i]),
                                  ),
                                ),
                        ),
                    ],
                  ),
                ),
                AsyncValue(error: != null) => StateMessage(
                  icon: Icons.cloud_off_outlined,
                  title: 'Let’s reconnect',
                  message:
                      'We couldn’t reach your MineOS server. Check your connection, then try again.',
                  actionLabel: 'Try again',
                  onAction: () => ref.invalidate(sessionsProvider),
                ),
                _ => const SessionsSkeleton(),
              },
            ),
          );
        },
      ),
    );
  }
}

class _Overview extends StatelessWidget {
  const _Overview({required this.sessions});
  final List<AgentSession> sessions;
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Wrap(
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: Space.md,
        children: [
          Text('Sessions', style: Theme.of(context).textTheme.headlineLarge),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
            decoration: BoxDecoration(
              color: Palette.surfaceHigh,
              border: Border.all(color: Palette.border),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              '${sessions.length}',
              style: uiText(
                size: 13,
                color: Palette.muted,
                weight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
      const SizedBox(height: Space.sm),
      Text(
        'A clear view of every agent run.',
        style: uiText(size: 15, color: Palette.muted),
      ),
      const SizedBox(height: Space.xl),
      Container(
        width: double.infinity,
        padding: const EdgeInsets.all(Space.lg),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Palette.bannerStart,
              Palette.bannerEnd,
            ],
          ),
          border: Border.all(color: Palette.accent.withValues(alpha: .13)),
          borderRadius: AppStyle.smallRounded,
        ),
        child: Wrap(
          spacing: Space.md,
          runSpacing: Space.sm,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            const DemoReplayChip(),
            Text(
              'Recorded sessions. Real insight into how your agent works.',
              style: uiText(size: 13, color: Palette.muted),
            ),
          ],
        ),
      ),
      const SizedBox(height: Space.xxl),
      Wrap(
        spacing: Space.xl,
        runSpacing: Space.md,
        children: [
          for (final status in SessionStatus.values)
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.circle, size: 6, color: statusColor(status)),
                const SizedBox(width: Space.sm),
                Text(
                  '${sessions.where((s) => s.status == status).length}',
                  style: uiText(size: 13, weight: FontWeight.w600),
                ),
                const SizedBox(width: Space.xs),
                Flexible(
                  child: Text(
                    statusLabel(status),
                    style: uiText(size: 12, color: Palette.muted),
                  ),
                ),
              ],
            ),
        ],
      ),
      const SizedBox(height: Space.sm),
    ],
  );
}
