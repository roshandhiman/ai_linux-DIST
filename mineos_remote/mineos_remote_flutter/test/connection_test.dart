import 'package:flutter_test/flutter_test.dart';
import 'package:mineos_remote/src/connection_screen.dart';

void main() {
  test('normalizes the API root and trims pasted whitespace', () {
    expect(
      normalizeServerUrl(' https://api.example.com '),
      'https://api.example.com/',
    );
    expect(
      normalizeServerUrl('http://localhost:8080'),
      'http://localhost:8080/',
    );
  });

  test('rejects URLs that cannot identify a safe API root', () {
    for (final input in [
      '',
      'example.com',
      'http://api.example.com',
      'ftp://api.example.com',
      'https://user:secret@api.example.com',
      'https://api.example.com/path',
      'https://api.example.com/?token=secret',
      'https://api.example.com/#x',
    ]) {
      expect(
        () => normalizeServerUrl(input),
        throwsFormatException,
        reason: input,
      );
    }
  });
}
