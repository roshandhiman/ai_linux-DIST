import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mineos_remote_client/mineos_remote_client.dart';
import 'package:mineos_remote/src/providers.dart';
import 'package:mineos_remote/src/session_detail_screen.dart';
import 'package:mineos_remote/src/connection_screen.dart';
import 'package:mineos_remote/src/about_screen.dart';
import 'package:mineos_remote/src/sessions_screen.dart';
import 'package:mineos_remote/src/theme.dart';
import 'package:mineos_remote/src/widgets.dart';

final sessions = [
  for (final status in SessionStatus.values)
    AgentSession(
      id: status.index + 1,
      task:
          'Summarise this week’s meeting notes in ~/Documents/meetings into ~/Documents/weekly-summary.md',
      status: status,
      modelName: 'qwen2.5-1.5b-instruct',
      provider: 'local',
      isLocal: true,
      route: 'TASK 0.50 via rules',
      startedAt: DateTime.now(),
      updatedAt: DateTime.now(),
      stepCount: 7,
    ),
];

class _PreviewConnection extends BackendConnection {
  @override
  Client build() => Client('https://api.example.com/');
}

class _PreviewTimeline extends TimelineNotifier {
  _PreviewTimeline() : super(2);
  @override
  TimelineState build() =>
      TimelineState(phase: StreamPhase.holding, steps: [approval]);
}

final approval = AgentStep(
  sessionId: 2,
  index: 7,
  kind: StepKind.approvalRequest,
  title: 'Create the weekly summary',
  detail:
      'The assistant wants to: create ~/Documents/weekly-summary.md\nAllow this? [y/N]',
  durationMs: 100,
  createdAt: DateTime.now(),
);

void main() {
  for (final size in [
    const Size(320, 640),
    const Size(390, 844),
    const Size(820, 1180),
    const Size(1440, 1000),
  ]) {
    testWidgets('sessions fit ${size.width.toInt()}px without overflow', (
      tester,
    ) async {
      tester.view.physicalSize = size;
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        ProviderScope(
          overrides: [sessionsProvider.overrideWith((ref) async => sessions)],
          child: MaterialApp(theme: buildTheme(), home: const SessionsScreen()),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 900));
      expect(tester.takeException(), isNull);
      expect(find.text('New task'), findsOneWidget);
      expect(
        find.byType(NavigationBar),
        size.width < 700 ? findsOneWidget : findsNothing,
      );
      await tester.tap(find.text('New task'));
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.text('Start on your MineOS machine'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
    });
  }
  testWidgets('loading skeleton and friendly error fit a small phone', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final pending = Completer<List<AgentSession>>();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [sessionsProvider.overrideWith((ref) => pending.future)],
        child: MaterialApp(theme: buildTheme(), home: const SessionsScreen()),
      ),
    );
    expect(find.byType(SessionsSkeleton), findsOneWidget);
    expect(tester.takeException(), isNull);
    pending.completeError(StateError('offline'));
    await tester.pump();
    await tester.pump();
    expect(find.text('Let’s reconnect'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  });
  testWidgets('detail, approval, settings and about fit a small phone', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 568);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    for (final screen in [
      SessionDetailScreen(sessionId: 2, initial: sessions[1]),
      const ConnectionScreen(),
      const AboutScreen(),
    ]) {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            clientProvider.overrideWith(_PreviewConnection.new),
            sessionDetailProvider(2).overrideWith(
              (ref) async =>
                  SessionDetail(session: sessions[1], steps: [approval]),
            ),
            timelineProvider(2).overrideWith(_PreviewTimeline.new),
          ],
          child: MaterialApp(theme: buildTheme(), home: screen),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));
      expect(
        tester.takeException(),
        isNull,
        reason: screen.runtimeType.toString(),
      );
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
    }
  });
  testWidgets('large text remains usable on mobile', (tester) async {
    tester.view.physicalSize = const Size(320, 700);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [sessionsProvider.overrideWith((ref) async => sessions)],
        child: MaterialApp(
          theme: buildTheme(),
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(
              context,
            ).copyWith(textScaler: const TextScaler.linear(1.5)),
            child: child!,
          ),
          home: const SessionsScreen(),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 900));
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  });
}
