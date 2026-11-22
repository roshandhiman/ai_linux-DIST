import 'dart:convert';
import 'dart:io';
import 'dart:math';

/// Run from mineos_remote/. Creates development secrets once, never overwrites.
void main() {
  final target = File('mineos_remote_server/config/passwords.yaml');
  if (target.existsSync()) {
    print('Local passwords already exist; kept unchanged.');
    return;
  }
  final random = Random.secure();
  String secret() =>
      base64UrlEncode(List.generate(64, (_) => random.nextInt(256)));
  target.writeAsStringSync(
    'shared:\n${['database', 'serviceSecret', 'jwtHmacSha512PrivateKey', 'jwtRefreshTokenHashPepper', 'emailSecretHashPepper'].map((name) => '  $name: ${secret()}\n').join()}',
  );
  if (!Platform.isWindows) Process.runSync('chmod', ['600', target.path]);
  print('Created ignored development secrets. Never commit passwords.yaml.');
}
