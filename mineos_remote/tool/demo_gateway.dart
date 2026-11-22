// Temporary public gateway: only the four repository demo recordings.
// Never tunnel the API port itself. This listener exposes no auth, storage,
// Insights, filesystem or arbitrary proxy routes, and forwards no credentials.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import '../mineos_remote_server/lib/src/sessions/demo_recordings.dart';

const demoIds = {1, 2, 3, 4};
const maxBody = 16384;

bool allowedStreamMessage(Object message, Set<String> streams) {
  if (message is! String || message.length > maxBody) return false;
  try {
    final value = jsonDecode(message) as Map<String, dynamic>;
    if (value['type'] == 'ping' || value['type'] == 'pong') return true;
    final data = value['data'] as Map<String, dynamic>;
    if (data['en'] != 'sessions' || data['m'] != 'watch') return false;
    if (data.containsKey('auth') || data.containsKey('am')) return false;
    final id = data['cid'];
    if (id is! String || id.length > 80) return false;
    if (value['type'] == 'cmsc') return streams.remove(id);
    if (value['type'] != 'omsc' || streams.length >= 8) return false;
    if (data['is'] is! List || (data['is'] as List).isNotEmpty) return false;
    final args = jsonDecode(data['args'] as String) as Map;
    if (args.keys.toSet().difference({'sessionId', 'resumeFrom'}).isNotEmpty ||
        !demoIds.contains(args['sessionId']) ||
        args['resumeFrom'] is! int ||
        args['resumeFrom'] < 0 ||
        args['resumeFrom'] > 100)
      return false;
    return streams.add(id);
  } catch (_) {
    return false;
  }
}

Future<void> main(List<String> arguments) async {
  final upstream = Uri.parse(
    arguments.isEmpty ? 'http://127.0.0.1:54550/' : arguments.first,
  );
  if (upstream.host != '127.0.0.1' && upstream.host != 'localhost') {
    throw ArgumentError('The upstream must be the local demo Serverpod.');
  }
  final client = HttpClient()..connectionTimeout = const Duration(seconds: 10);
  final check = await client.postUrl(upstream.resolve('/sessions/list'));
  check.headers.contentType = ContentType.json;
  check.write('{}');
  final response = await check.close();
  final sessions = jsonDecode(await utf8.decoder.bind(response).join()) as List;
  if (sessions.length != demoRecordings.length ||
      !sessions.every(
        (s) =>
            demoIds.contains(s['id']) &&
            s['task'] == demoRecordings[(s['id'] as int) - 1].task,
      )) {
    throw StateError(
      'Refusing to publish: database does not match the four public demo fixtures.',
    );
  }
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 54600);
  print('Read-only demo gateway ready at http://127.0.0.1:54600');
  await for (final request in server) {
    unawaited(handle(request, upstream, client));
  }
}

Future<void> reject(HttpRequest request, int status) async {
  request.response.statusCode = status;
  await request.response.close();
}

Future<void> handle(
  HttpRequest request,
  Uri upstream,
  HttpClient client,
) async {
  request.response.headers
    ..set('Access-Control-Allow-Origin', '*')
    ..set('Access-Control-Allow-Methods', 'POST, OPTIONS')
    ..set(
      'Access-Control-Allow-Headers',
      'Content-Type, X-Serverpod-Web-Auth-Mode',
    )
    ..set('Cache-Control', 'no-store');
  try {
    final path = request.uri.path;
    if (request.uri.hasQuery ||
        request.headers.value('authorization') != null ||
        request.headers.value('cookie') != null) {
      return await reject(request, HttpStatus.forbidden);
    }
    if (path == '/v1/websocket' &&
        WebSocketTransformer.isUpgradeRequest(request)) {
      final remote = await WebSocket.connect(
        upstream.replace(scheme: 'ws', path: path).toString(),
      );
      final visitor = await WebSocketTransformer.upgrade(request, compression: CompressionOptions.compressionOff);
      print("Demo replay WebSocket connected");
      final streams = <String>{};
      remote.listen(
        visitor.add,
        onDone: () { print("Upstream replay closed: ${remote.closeCode}"); visitor.close(); },
        onError: (Object error) { print("Upstream replay error: $error"); visitor.close(); },
      );
      visitor.listen(
        (message) {
          if (allowedStreamMessage(message, streams)) {
            remote.add(message);
          } else {
            visitor.close(
              WebSocketStatus.policyViolation,
              'Only demo session replay is available',
            );
            remote.close();
          }
        },
        onDone: () { print("Viewer closed: ${visitor.closeCode}"); remote.close(); },
        onError: (Object error) { print("Viewer replay error: $error"); remote.close(); },
      );
      return;
    }
    if (path != '/sessions/list' && path != '/sessions/get')
      return await reject(request, HttpStatus.notFound);
    if (request.method == 'OPTIONS')
      return await reject(request, HttpStatus.noContent);
    if (request.method != 'POST')
      return await reject(request, HttpStatus.methodNotAllowed);
    final body = <int>[];
    await for (final chunk in request) {
      body.addAll(chunk);
      if (body.length > maxBody)
        return await reject(request, HttpStatus.requestEntityTooLarge);
    }
    final args = jsonDecode(utf8.decode(body)) as Map;
    if ((path == '/sessions/list' && args.isNotEmpty) ||
        (path == '/sessions/get' &&
            (args.length != 1 || !demoIds.contains(args['sessionId'])))) {
      return await reject(request, HttpStatus.forbidden);
    }
    final proxy = await client.postUrl(upstream.resolve(path));
    proxy.headers.contentType = ContentType.json;
    proxy.add(body);
    final result = await proxy.close();
    request.response.statusCode = result.statusCode;
    request.response.headers.contentType = ContentType.json;
    final text = await utf8.decoder.bind(result).join();
    if (path == '/sessions/list' && result.statusCode == 200) {
      final rows = jsonDecode(text) as List;
      request.response.write(
        jsonEncode(rows.where((s) => demoIds.contains(s['id'])).toList()),
      );
    } else {
      request.response.write(text);
    }
    await request.response.close();
  } catch (_) {
    try {
      await reject(request, HttpStatus.badGateway);
    } catch (_) {}
  }
}
