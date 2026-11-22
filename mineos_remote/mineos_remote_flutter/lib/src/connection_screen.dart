import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'providers.dart';
import 'theme.dart';

/// Accept public HTTPS endpoints and HTTP only for local development.
String normalizeServerUrl(String input) {
  final uri = Uri.tryParse(input.trim());
  if (uri == null ||
      !uri.hasAuthority ||
      uri.host.isEmpty ||
      uri.userInfo.isNotEmpty ||
      uri.hasQuery ||
      uri.hasFragment ||
      (uri.path.isNotEmpty && uri.path != '/')) {
    throw const FormatException(
      'Enter a server address, such as https://api.example.com/',
    );
  }
  final local =
      uri.host == 'localhost' ||
      uri.host == '127.0.0.1' ||
      uri.host == '10.0.2.2';
  if (uri.scheme != 'https' && !(uri.scheme == 'http' && local)) {
    throw const FormatException('Use an HTTPS address for your server.');
  }
  return uri.replace(path: '/').toString();
}

class ConnectionScreen extends ConsumerStatefulWidget {
  const ConnectionScreen({super.key});

  @override
  ConsumerState<ConnectionScreen> createState() => _ConnectionScreenState();
}

class _ConnectionScreenState extends ConsumerState<ConnectionScreen> {
  late final TextEditingController _address;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _address = TextEditingController(text: ref.read(clientProvider).host);
  }

  @override
  void dispose() {
    _address.dispose();
    super.dispose();
  }

  Future<void> _connect() async {
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final url = normalizeServerUrl(_address.text);
      await ref.read(clientProvider.notifier).connect(url);
      if (mounted) Navigator.of(context).pop();
    } on FormatException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) {
        setState(
          () => _error =
              'Could not connect. Check the API address and that the server is running. Your previous connection is unchanged.',
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Server connection')),
    body: Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 640),
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const Icon(Icons.dns_outlined, color: Palette.accent, size: 40),
            const SizedBox(height: 20),
            Text(
              'Connect to MineOS Remote',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            const Text(
              'Enter your Serverpod API address. The connection is tested before it is saved on this device.',
            ),
            const SizedBox(height: 24),
            TextField(
              controller: _address,
              enabled: !_saving,
              keyboardType: TextInputType.url,
              autocorrect: false,
              textInputAction: TextInputAction.go,
              onSubmitted: (_) {
                if (!_saving) _connect();
              },
              decoration: const InputDecoration(
                labelText: 'API server URL',
                hintText: 'https://your-project.api.serverpod.space/',
                border: OutlineInputBorder(),
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(_error!, style: const TextStyle(color: Palette.failed)),
            ],
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: _saving ? null : _connect,
              icon: _saving
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.link),
              label: Text(_saving ? 'Testing connection…' : 'Test and connect'),
            ),
            const SizedBox(height: 20),
            const Text(
              'On a phone, localhost refers to the phone itself. Use your hosted HTTPS API address.',
            ),
          ],
        ),
      ),
    ),
  );
}
