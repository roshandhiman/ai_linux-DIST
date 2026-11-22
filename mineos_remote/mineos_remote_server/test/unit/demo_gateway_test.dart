import 'dart:convert';

import 'package:test/test.dart';

import '../../../tool/demo_gateway.dart';

String open({
  String endpoint = 'sessions',
  String method = 'watch',
  int id = 1,
  Map<String, dynamic> extra = const {},
}) => jsonEncode({
  'type': 'omsc',
  'data': {
    'en': endpoint,
    'm': method,
    'cid': 'demo-connection',
    'args': jsonEncode({'sessionId': id, 'resumeFrom': 0}),
    'is': [],
    ...extra,
  },
});

void main() {
  test('allows only approved recordings and read-only replay', () {
    for (final id in demoIds) {
      expect(allowedStreamMessage(open(id: id), {}), isTrue);
    }
    expect(allowedStreamMessage(open(id: 5), {}), isFalse);
    expect(allowedStreamMessage(open(endpoint: 'emailIdp'), {}), isFalse);
    expect(allowedStreamMessage(open(method: 'approve'), {}), isFalse);
    expect(allowedStreamMessage(open(extra: {'auth': 'secret'}), {}), isFalse);
  });

  test('rejects malformed, duplicate, and arbitrary stream messages', () {
    final streams = <String>{};
    expect(allowedStreamMessage(open(), streams), isTrue);
    expect(allowedStreamMessage(open(), streams), isFalse);
    for (final message in [
      'not json',
      '{}',
      '{"type":"msm"}',
      jsonEncode({'type': 'omsc', 'data': {}}),
    ]) {
      expect(allowedStreamMessage(message, {}), isFalse);
    }
  });
}
