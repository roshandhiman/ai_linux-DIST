import '../generated/protocol.dart';

/// When each step of a recording is revealed during a replay.
///
/// A replay is time-compressed: a 20-second model call on a laptop CPU is
/// shown as a 5–8 second wait, a sandbox run as 1–3 seconds. Model calls
/// still take visibly longer than everything else, as they do on the
/// machine.
///
/// Running sessions are replayed on a shared clock: every viewer of the same
/// session sees the same step at the same moment, which is what "watching a
/// session live from two phones" looks like.
class ReplayPlan {
  ReplayPlan(List<AgentStep> steps, {this.speed = 1.0})
      : steps = List.unmodifiable(
            [...steps]..sort((a, b) => a.index.compareTo(b.index))) {
    var at = 0;
    for (final step in this.steps) {
      at += delayBeforeMs(step);
      revealAtMs.add(at);
    }
    cycleMs = at + _scaled(restartPauseMs);
  }

  /// 1.0 in production. Tests use a tiny value so a replay takes
  /// milliseconds.
  final double speed;
  final List<AgentStep> steps;

  /// Offset from the start of a cycle at which step i is revealed.
  final List<int> revealAtMs = [];

  /// Length of one loop of a running session, including the pause before it
  /// starts again.
  late final int cycleMs;

  /// Pause after the last step of a running session, before the loop.
  static const restartPauseMs = 7000;

  int _scaled(int ms) => ms <= 0 ? 0 : (ms * speed).round().clamp(1, ms);

  /// How long the viewer waits before [step] appears.
  int delayBeforeMs(AgentStep step) {
    final int ms;
    switch (step.kind) {
      case StepKind.modelCall:
        // The slow part on a CPU: 4.5–8 s.
        ms = (3000 + step.durationMs ~/ 5).clamp(4500, 8000);
      case StepKind.plan:
        ms = 900;
      case StepKind.toolCall:
      case StepKind.error:
        // 1.2–2.8 s, varied but deterministic.
        ms = 1200 + (step.index * 373 + step.durationMs) % 1600;
      case StepKind.approvalRequest:
      case StepKind.result:
        ms = 1500;
    }
    return _scaled(ms);
  }

  /// Where a running session is in its loop at [nowMs] (ms since epoch).
  ({int cycle, int positionMs, int cycleStartMs}) position(int nowMs) {
    final cycle = nowMs ~/ cycleMs;
    final cycleStartMs = cycle * cycleMs;
    return (
      cycle: cycle,
      positionMs: nowMs - cycleStartMs,
      cycleStartMs: cycleStartMs,
    );
  }

  /// How many steps a running session has revealed at [positionMs].
  int revealedAt(int positionMs) {
    var n = 0;
    while (n < steps.length && revealAtMs[n] <= positionMs) {
      n++;
    }
    return n;
  }
}
