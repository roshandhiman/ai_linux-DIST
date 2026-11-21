import 'package:mineos_remote_server/src/generated/protocol.dart';
import 'package:mineos_remote_server/src/sessions/seed.dart';
import 'package:mineos_remote_server/src/sessions/sessions_endpoint.dart';
import 'package:test/test.dart';

import 'test_tools/serverpod_test_tools.dart';

void main() {
  withServerpod('Given the seeded demo sessions', (sessionBuilder, endpoints) {
    setUp(() async {
      SessionsEndpoint.replaySpeed = 0.001; // a replay takes milliseconds
      await seedDemoSessions(sessionBuilder.build());
    });

    tearDown(() => SessionsEndpoint.replaySpeed = 1.0);

    test('seeding again adds nothing', () async {
      expect(await seedDemoSessions(sessionBuilder.build()), 0);
      final all = await endpoints.sessions.list(sessionBuilder);
      expect(all, hasLength(4));
    });

    test('list() returns every session, newest first, all local', () async {
      final all = await endpoints.sessions.list(sessionBuilder);
      expect(all.map((s) => s.status).toSet(), {
        SessionStatus.running,
        SessionStatus.awaitingApproval,
        SessionStatus.done,
        SessionStatus.failed,
      });
      for (var i = 1; i < all.length; i++) {
        expect(
          all[i - 1].startedAt.isBefore(all[i].startedAt),
          isFalse,
          reason: 'sessions must be sorted newest first',
        );
      }
      expect(all.every((s) => s.isLocal), isTrue);
      expect(all.map((s) => s.modelName).toSet(), {'qwen2.5-1.5b-instruct'});
    });

    test(
      'get() of a finished session returns all its steps in order',
      () async {
        final done = (await endpoints.sessions.list(
          sessionBuilder,
        )).firstWhere((s) => s.status == SessionStatus.done);
        final detail = await endpoints.sessions.get(sessionBuilder, done.id!);
        expect(detail.steps, hasLength(done.stepCount));
        expect(
          detail.steps.map((s) => s.index),
          List.generate(done.stepCount, (i) => i + 1),
        );
      },
    );

    test('watch() of a done session streams every step in order, then '
        'finishes', () async {
      final done = (await endpoints.sessions.list(
        sessionBuilder,
      )).firstWhere((s) => s.status == SessionStatus.done);
      final events = await endpoints.sessions
          .watch(sessionBuilder, done.id!, 0)
          .toList();
      expect(events.first.type, ReplayEventType.restart);
      expect(events.last.type, ReplayEventType.finished);
      final indices = [
        for (final e in events)
          if (e.type == ReplayEventType.step) e.step!.index,
      ];
      expect(indices, List.generate(done.stepCount, (i) => i + 1));
    });

    test(
      'watch() of an awaiting session holds at the approval request',
      () async {
        final paused = (await endpoints.sessions.list(
          sessionBuilder,
        )).firstWhere((s) => s.status == SessionStatus.awaitingApproval);
        final events = await endpoints.sessions
            .watch(sessionBuilder, paused.id!, 0)
            .toList();
        final steps = [
          for (final e in events)
            if (e.type == ReplayEventType.step) e.step!,
        ];
        expect(steps.last.kind, StepKind.approvalRequest);
        expect(events.last.type, ReplayEventType.holding);
      },
    );

    test('watch() of a running session loops, in order each time', () async {
      final running = (await endpoints.sessions.list(
        sessionBuilder,
      )).firstWhere((s) => s.status == SessionStatus.running);
      // Collect until the third restart: at least one complete loop.
      var restarts = 0;
      final loops = <List<int>>[];
      await for (final e in endpoints.sessions.watch(
        sessionBuilder,
        running.id!,
        0,
      )) {
        if (e.type == ReplayEventType.restart) {
          restarts++;
          if (restarts == 3) break;
          loops.add([]);
        } else if (e.type == ReplayEventType.step) {
          loops.last.add(e.step!.index);
        }
      }
      final full = loops[1]; // the first loop may start mid-way (catch-up)
      expect(full, List.generate(full.length, (i) => i + 1));
      expect(full.length, greaterThanOrEqualTo(12));
    });
  });
}
