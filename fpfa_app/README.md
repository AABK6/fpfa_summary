# FPFA Flutter reader

Responsive web and mobile reader for the FPFA summary API.

## API resolution

`lib/core/api_config.dart` applies this order:

1. a valid `API_BASE_URL` compile-time define;
2. the production Cloud Run URL in release builds;
3. `http://10.0.2.2:5000` for Android debug;
4. `http://localhost:5000` for other debug targets.

Release builds reject HTTP and loopback URLs.

## Local checks

```powershell
flutter pub get
dart format --output=none --set-exit-if-changed lib test integration_test
flutter analyze
flutter test
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:5000
```

## Production builds

```powershell
flutter build web --release --dart-define=API_BASE_URL=https://fpfa-summary-api-1076204999548.europe-west1.run.app
flutter build apk --release --dart-define=API_BASE_URL=https://fpfa-summary-api-1076204999548.europe-west1.run.app
```

The reader starts at index zero because the API is newest-first. It marks cached data as stale, exposes the original source, uses explicit Thesis/Summary/Evidence sections, and provides responsive chronology controls for keyboard, touch, and screen-reader users.
