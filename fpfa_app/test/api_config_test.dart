import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fpfa_flutter/core/api_config.dart';

void main() {
  group('API configuration', () {
    test('keeps the production endpoint explicit', () {
      expect(
        productionApiBaseUrl,
        'https://fpfa-summary-api-1076204999548.europe-west1.run.app',
      );
    });

    test('uses the local Flask endpoint in a desktop debug test', () {
      debugDefaultTargetPlatformOverride = TargetPlatform.windows;
      addTearDown(() => debugDefaultTargetPlatformOverride = null);
      expect(resolveApiBaseUrl(), 'http://localhost:5000');
    });

    test('rejects loopback and insecure URLs for release', () {
      expect(
        () => validateReleaseApiBaseUrl('http://10.0.2.2:5000'),
        throwsStateError,
      );
      expect(
        () => validateReleaseApiBaseUrl('http://example.com'),
        throwsStateError,
      );
    });

    test('accepts and normalizes a production HTTPS URL', () {
      expect(
        validateReleaseApiBaseUrl('$productionApiBaseUrl/'),
        productionApiBaseUrl,
      );
    });
  });
}
