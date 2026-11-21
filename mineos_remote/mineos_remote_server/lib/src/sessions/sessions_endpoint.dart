import 'dart:async';

import 'package:serverpod/serverpod.dart';

import '../generated/protocol.dart';
import 'replay_plan.dart';

/// Read-only access to the recorded MineOS agent sessions, for anonymous
/// demo viewers. Everything served here is a replay of a recording, and the
/// app labels it "Demo replay".
class SessionsEndpoint extends Endpoint {
  /// Replay speed. 1.0 in production; tests lower it.
  static double replaySpeed = 1.0;

  /// The clock replays run on, in ms since epoch. Tests can replace it.
  static int Function() nowMs = () => DateTime.now().millisecondsSinceEpoch;

  /// All sessions, newest first.
  Future<List<AgentSession>> list(Session session) async {
    final sessions = await AgentSession.db.find(session);
    final result = <AgentSession>[];
    for (final s in sessions) {
      result.add(
        s.status == SessionStatus.running
            ? _live(s, await _plan(session, s.id!))
            : s,
      );
    }
    result.sort((a, b) => b.startedAt.compareTo(a.startedAt));
    return result;
  }

  /// One session and the steps revealed so far.
  Future<SessionDetail> get(Session session, int sessionId) async {
    final s = await _find(session, sessionId);
    final plan = await _plan(session, sessionId);
    if (s.status != SessionStatus.running) {
      return SessionDetail(session: s, steps: plan.steps);
    }
    final where = plan.position(nowMs());
    return SessionDetail(
      session: _live(s, plan),
      steps: plan.steps.take(plan.revealedAt(where.positionMs)).toList(),
    );
  }

  /// Replays a session step by step.
  ///
  /// Every call starts with a `restart` event, then any catch-up steps
  /// (instantly), then the remaining steps with their delays. A running
  /// session follows a shared clock and loops forever; [resumeFrom] is
  /// ignored for it. Any other session starts its replay at step 1, sends
  /// the first [resumeFrom] steps at once (for a client that reconnects),
  /// and ends with `holding` (paused at the approval prompt) or `finished`.
  Stream<ReplayEvent> watch(
    Session session,
    int sessionId,
    int resumeFrom,
  ) async* {
    final s = await _find(session, sessionId);
    final plan = await _plan(session, sessionId);

    if (s.status != SessionStatus.running) {
      yield ReplayEvent(type: ReplayEventType.restart, cycle: 0);
      for (var i = 0; i < plan.steps.length; i++) {
        final step = plan.steps[i];
        if (i >= resumeFrom) {
          if (step.kind == StepKind.modelCall) {
            yield _thinking(step);
          }
          await _sleep(plan.delayBeforeMs(step));
        }
        yield ReplayEvent(type: ReplayEventType.step, cycle: 0, step: step);
      }
      yield ReplayEvent(
        type: s.status == SessionStatus.awaitingApproval
            ? ReplayEventType.holding
            : ReplayEventType.finished,
        cycle: 0,
      );
      return;
    }

    // Running: loop on the shared clock.
    while (true) {
      final where = plan.position(nowMs());
      final startedAt = DateTime.fromMillisecondsSinceEpoch(
        where.cycleStartMs,
        isUtc: true,
      );
      yield ReplayEvent(
        type: ReplayEventType.restart,
        cycle: where.cycle,
        startedAt: startedAt,
      );
      var i = plan.revealedAt(where.positionMs);
      for (final step in plan.steps.take(i)) {
        yield ReplayEvent(
          type: ReplayEventType.step,
          cycle: where.cycle,
          step: step,
        );
      }
      for (; i < plan.steps.length; i++) {
        final step = plan.steps[i];
        if (step.kind == StepKind.modelCall) {
          yield _thinking(step, cycle: where.cycle);
        }
        await _sleep(where.cycleStartMs + plan.revealAtMs[i] - nowMs());
        yield ReplayEvent(
          type: ReplayEventType.step,
          cycle: where.cycle,
          step: step,
        );
      }
      // The recording ends while the agent is still working: keep the
      // "thinking" indicator up until the loop starts again.
      yield ReplayEvent(
        type: ReplayEventType.thinking,
        cycle: where.cycle,
        label: 'Writing the report',
      );
      await _sleep(where.cycleStartMs + plan.cycleMs - nowMs());
    }
  }

  ReplayEvent _thinking(AgentStep step, {int cycle = 0}) => ReplayEvent(
    type: ReplayEventType.thinking,
    cycle: cycle,
    label: step.title,
  );

  Future<void> _sleep(int ms) =>
      ms > 0 ? Future.delayed(Duration(milliseconds: ms)) : Future.value();

  Future<AgentSession> _find(Session session, int id) async {
    final s = await AgentSession.db.findById(session, id);
    if (s == null) {
      throw SessionNotFoundException(message: 'No session with id $id');
    }
    return s;
  }

  Future<ReplayPlan> _plan(Session session, int sessionId) async {
    final steps = await AgentStep.db.find(
      session,
      where: (t) => t.sessionId.equals(sessionId),
      orderBy: (t) => t.index,
    );
    return ReplayPlan(steps, speed: replaySpeed);
  }

  /// A running session as it stands right now in its loop.
  AgentSession _live(AgentSession s, ReplayPlan plan) {
    final where = plan.position(nowMs());
    final revealed = plan.revealedAt(where.positionMs);
    final startedAt = DateTime.fromMillisecondsSinceEpoch(
      where.cycleStartMs,
      isUtc: true,
    );
    return s.copyWith(
      startedAt: startedAt,
      updatedAt: revealed == 0
          ? startedAt
          : startedAt.add(
              Duration(milliseconds: plan.revealAtMs[revealed - 1]),
            ),
      stepCount: revealed,
    );
  }
}
