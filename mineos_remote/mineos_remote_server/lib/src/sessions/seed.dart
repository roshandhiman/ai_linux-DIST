import 'package:serverpod/serverpod.dart';

import '../generated/protocol.dart';
import 'demo_recordings.dart';

/// Stores the demo recordings if the tables are empty. Safe to run on every
/// start: a database that already has sessions is left alone.
Future<int> seedDemoSessions(Session session, {DateTime? now}) async {
  if (await AgentSession.db.count(session) > 0) return 0;
  final clock = (now ?? DateTime.now()).toUtc();

  await session.db.transaction((transaction) async {
    for (final spec in demoRecordings) {
      final startedAt = clock.subtract(
        Duration(minutes: spec.startedMinutesAgo),
      );
      var at = startedAt;
      final steps = <AgentStep>[];
      for (var i = 0; i < spec.steps.length; i++) {
        final s = spec.steps[i];
        at = at.add(Duration(milliseconds: s.durationMs));
        steps.add(
          AgentStep(
            sessionId: 0, // set below, once the session has an id
            index: i + 1,
            kind: StepKind.fromJson(s.kind),
            title: s.title,
            detail: s.detail,
            durationMs: s.durationMs,
            createdAt: at,
          ),
        );
      }
      final stored = await AgentSession.db.insertRow(
        session,
        AgentSession(
          task: spec.task,
          status: SessionStatus.fromJson(spec.status),
          modelName: demoModelName,
          provider: demoProvider,
          isLocal: demoProvider == 'local',
          route: spec.route,
          outcome: spec.outcome,
          answer: spec.answer,
          startedAt: startedAt,
          updatedAt: at,
          stepCount: steps.length,
        ),
        transaction: transaction,
      );
      await AgentStep.db.insert(
        session,
        [for (final step in steps) step.copyWith(sessionId: stored.id!)],
        transaction: transaction,
      );
    }
  });
  return demoRecordings.length;
}
