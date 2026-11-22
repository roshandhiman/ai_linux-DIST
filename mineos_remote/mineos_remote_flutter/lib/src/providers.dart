import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mineos_remote_client/mineos_remote_client.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../client.dart' as connection;

/// The one generated Serverpod client, created in main().
final clientProvider = NotifierProvider<BackendConnection, Client>(
  BackendConnection.new,
);

class BackendConnection extends Notifier<Client> {
  @override
  Client build() => connection.client;

  /// Keep the current connection until the replacement passes a real API call.
  Future<void> connect(String url) async {
    final next = connection.createClient(url);
    try {
      await next.sessions.list().timeout(const Duration(seconds: 12));
      final preferences = await SharedPreferences.getInstance();
      if (!await preferences.setString(connection.serverUrlPreference, url)) {
        throw StateError('Could not save the server address. Please retry.');
      }
    } catch (_) {
      next.close();
      rethrow;
    }
    final previous = state;
    connection.client = next;
    state = next;
    previous.close();
  }
}

/// Home screen: every session, newest first.
final sessionsProvider = FutureProvider.autoDispose<List<AgentSession>>(
  (ref) => ref.watch(clientProvider).sessions.list(),
  retry: (retryCount, error) => null, // the screen offers Retry instead
);

/// Detail header: one session and the steps revealed so far.
final sessionDetailProvider = FutureProvider.autoDispose
    .family<SessionDetail, int>(
      (ref, id) => ref.watch(clientProvider).sessions.get(id),
      retry: (retryCount, error) => null,
    );

enum StreamPhase { connecting, live, holding, finished, reconnecting }

class TimelineState {
  const TimelineState({
    this.steps = const [],
    this.phase = StreamPhase.connecting,
    this.thinking,
    this.cycle,
    this.startedAt,
    this.error,
    this.retryInSeconds,
    this.usingPolling = false,
  });

  final List<AgentStep> steps;
  final StreamPhase phase;

  /// What the agent is working on while the next step has not arrived.
  final String? thinking;

  /// Loop number of a running session's replay.
  final int? cycle;

  /// When the current replay loop started (running sessions).
  final DateTime? startedAt;
  final String? error;
  final int? retryInSeconds;
  final bool usingPolling;

  AgentStep? get approval {
    for (final s in steps.reversed) {
      if (s.kind == StepKind.approvalRequest) return s;
    }
    return null;
  }

  TimelineState copyWith({
    List<AgentStep>? steps,
    StreamPhase? phase,
    String? Function()? thinking,
    int? cycle,
    DateTime? Function()? startedAt,
    String? Function()? error,
    int? Function()? retryInSeconds,
    bool? usingPolling,
  }) => TimelineState(
    steps: steps ?? this.steps,
    phase: phase ?? this.phase,
    thinking: thinking != null ? thinking() : this.thinking,
    cycle: cycle ?? this.cycle,
    startedAt: startedAt != null ? startedAt() : this.startedAt,
    error: error != null ? error() : this.error,
    retryInSeconds: retryInSeconds != null
        ? retryInSeconds()
        : this.retryInSeconds,
    usingPolling: usingPolling ?? this.usingPolling,
  );
}

/// Follows `sessions.watch()` for one session and reconnects with backoff
/// when the connection drops.
class TimelineNotifier extends Notifier<TimelineState> {
  TimelineNotifier(this.sessionId);

  final int sessionId;

  StreamSubscription<ReplayEvent>? _sub;
  Timer? _retryTimer;
  Timer? _countdown;
  Timer? _pollTimer;
  bool _polling = false;
  int _failures = 0;

  @override
  TimelineState build() {
    ref.watch(clientProvider);
    ref.onDispose(() {
      _stop();
      _pollTimer?.cancel();
    });
    // Connect after build() has returned its first state.
    scheduleMicrotask(_connect);
    return const TimelineState();
  }

  void _stop() {
    _sub?.cancel();
    _sub = null;
    _retryTimer?.cancel();
    _countdown?.cancel();
  }

  void _connect() {
    if (!ref.mounted) return;
    _stop();
    final client = ref.read(clientProvider);
    _sub = client.sessions
        .watch(sessionId, state.steps.length)
        .listen(
          _onEvent,
          onError: (Object e, StackTrace _) => _dropped(e),
          onDone: () {
            if (state.phase != StreamPhase.holding &&
                state.phase != StreamPhase.finished) {
              _dropped('the stream closed');
            }
          },
          cancelOnError: true,
        );
  }

  void _onEvent(ReplayEvent e) {
    if (!ref.mounted) return;
    _pollTimer?.cancel();
    _pollTimer = null;
    _failures = 0;
    switch (e.type) {
      case ReplayEventType.restart:
        // A new loop of a running session starts from an empty timeline.
        // A reconnect into the same loop keeps what is already shown.
        final newLoop = state.cycle != null && state.cycle != e.cycle;
        state = state.copyWith(
          steps: newLoop ? const [] : state.steps,
          phase: StreamPhase.live,
          cycle: e.cycle,
          startedAt: () => e.startedAt?.toLocal(),
          thinking: () => null,
          error: () => null,
          retryInSeconds: () => null,
          usingPolling: false,
        );
      case ReplayEventType.step:
        final step = e.step!;
        if (state.steps.any((s) => s.index == step.index)) return;
        state = state.copyWith(
          steps: [...state.steps, step],
          phase: StreamPhase.live,
          thinking: () => null,
        );
      case ReplayEventType.thinking:
        state = state.copyWith(thinking: () => e.label ?? '');
      case ReplayEventType.holding:
        state = state.copyWith(
          phase: StreamPhase.holding,
          thinking: () => null,
        );
      case ReplayEventType.finished:
        state = state.copyWith(
          phase: StreamPhase.finished,
          thinking: () => null,
        );
    }
  }

  void _dropped(Object error) {
    if (!ref.mounted) return;
    _pollTimer ??= Timer.periodic(
      const Duration(seconds: 2),
      (_) => _snapshot(),
    );
    unawaited(_snapshot());
    _sub = null;
    _failures++;
    final seconds = [1, 2, 4, 8, 15][(_failures - 1).clamp(0, 4)];
    state = state.copyWith(
      phase: StreamPhase.reconnecting,
      thinking: () => null,
      error: () => _describe(error),
      retryInSeconds: () => seconds,
    );
    var left = seconds;
    _countdown?.cancel();
    _countdown = Timer.periodic(const Duration(seconds: 1), (t) {
      left--;
      if (!ref.mounted || left <= 0) {
        t.cancel();
        return;
      }
      state = state.copyWith(retryInSeconds: () => left);
    });
    _retryTimer?.cancel();
    _retryTimer = Timer(Duration(seconds: seconds), _connect);
  }

  /// Some temporary hosts drop WebSockets. Keep real server data visible
  /// over HTTP while retrying the streaming transport in the background.
  Future<void> _snapshot() async {
    if (!ref.mounted || _polling) return;
    _polling = true;
    try {
      final result = await ref
          .read(clientProvider)
          .sessions
          .get(sessionId)
          .timeout(const Duration(seconds: 10));
      if (!ref.mounted || _pollTimer == null) return;
      state = TimelineState(
        steps: result.steps,
        phase: switch (result.session.status) {
          SessionStatus.running => StreamPhase.live,
          SessionStatus.awaitingApproval => StreamPhase.holding,
          SessionStatus.done || SessionStatus.failed => StreamPhase.finished,
        },
        startedAt: result.session.startedAt.toLocal(),
        usingPolling: true,
      );
    } catch (_) {
      if (ref.mounted) {
        state = state.copyWith(
          phase: StreamPhase.reconnecting,
          usingPolling: false,
        );
      }
    } finally {
      _polling = false;
    }
  }

  /// "Retry now" in the reconnect banner.
  void retryNow() => _connect();

  static String _describe(Object error) {
    if (error is SessionNotFoundException) return error.message;
    if (error is MethodStreamException) {
      return 'Connection to the server was lost';
    }
    return 'Connection problem: $error';
  }
}

final timelineProvider = NotifierProvider.autoDispose
    .family<TimelineNotifier, TimelineState, int>(TimelineNotifier.new);
