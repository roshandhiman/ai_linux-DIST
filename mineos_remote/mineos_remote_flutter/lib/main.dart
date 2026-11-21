import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'client.dart';
import 'src/providers.dart';
import 'src/sessions_screen.dart';
import 'src/theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // The server URL comes from --dart-define=SERVER_URL, else from
  // assets/config.json (which the Serverpod web server fills in when it
  // serves the app), else http://localhost:8080/. See client.dart.
  await initializeClient();
  runApp(
    ProviderScope(
      overrides: [clientProvider.overrideWithValue(client)],
      child: const MineosRemoteApp(),
    ),
  );
}

class MineosRemoteApp extends StatelessWidget {
  const MineosRemoteApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MineOS Remote',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      themeMode: ThemeMode.dark,
      home: const SessionsScreen(),
    );
  }
}
