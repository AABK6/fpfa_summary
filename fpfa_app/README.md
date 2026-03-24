# fpfa_app

Flutter client for the FPFA summary backend.

## What It Talks To

The app fetches articles from:

```text
<API_BASE_URL>/api/articles
```

The runtime base URL resolution in `lib/main.dart` is:

- `API_BASE_URL` compile-time define if provided
- otherwise Android emulator fallback: `http://10.0.2.2:8000`
- otherwise local fallback: `http://localhost:8000`

Examples:

```bash
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:5000
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
flutter build web --dart-define=API_BASE_URL=https://ppfflaskapp.azurewebsites.net
```

## Local Development

```bash
flutter pub get
flutter analyze
flutter test
flutter run
```

## Deployment Paths

- Web: Azure Static Web Apps via `.github/workflows/deploy_flutter_static_web_apps.yml`
- Android APK distribution: Firebase App Distribution via `.github/workflows/deploy_android.yml`

There is Firebase configuration in the Android app, but the repository does not contain a Firebase Hosting deployment for the Flutter web build.
