import 'package:flutter/foundation.dart';

const productionApiBaseUrl =
    'https://fpfa-summary-api-1076204999548.europe-west1.run.app';

String resolveApiBaseUrl() {
  const configuredBaseUrl = String.fromEnvironment('API_BASE_URL');
  final configured = _normalizeBaseUrl(configuredBaseUrl);
  if (configured.isNotEmpty) {
    return _validateApiBaseUrl(configured, releaseMode: kReleaseMode);
  }
  if (kReleaseMode) return productionApiBaseUrl;
  if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
    return 'http://10.0.2.2:5000';
  }
  return 'http://localhost:5000';
}

@visibleForTesting
String validateReleaseApiBaseUrl(String value) {
  return _validateApiBaseUrl(_normalizeBaseUrl(value), releaseMode: true);
}

String _normalizeBaseUrl(String value) {
  return value.trim().replaceFirst(RegExp(r'/+$'), '');
}

String _validateApiBaseUrl(String resolved, {required bool releaseMode}) {
  final uri = Uri.tryParse(resolved);
  if (uri == null || !uri.hasScheme || uri.host.isEmpty) {
    throw StateError('API_BASE_URL must be an absolute HTTP(S) URL.');
  }
  if (!const {'http', 'https'}.contains(uri.scheme)) {
    throw StateError('API_BASE_URL must use HTTP or HTTPS.');
  }

  if (releaseMode && (uri.scheme != 'https' || _isPrivateHost(uri.host))) {
    throw StateError('Release builds require a non-loopback HTTPS API URL.');
  }
  return resolved;
}

bool _isPrivateHost(String host) {
  if (host == 'localhost' || host == '::1') return true;
  final octets = host.split('.').map(int.tryParse).toList(growable: false);
  if (octets.length != 4 || octets.any((octet) => octet == null)) return false;
  final first = octets[0]!;
  final second = octets[1]!;
  return first == 10 ||
      first == 127 ||
      (first == 172 && second >= 16 && second <= 31) ||
      (first == 192 && second == 168);
}
