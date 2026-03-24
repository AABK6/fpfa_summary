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
flutter build web --dart-define=API_BASE_URL=https://fpfa-summary-api-1028212947283.europe-west1.run.app
```

## Local Development

```bash
flutter pub get
flutter analyze
flutter test
flutter run
```

## Deployment Paths

- Web: Firebase Hosting via `.github/workflows/deploy_flutter_static_web_apps.yml`
- Android APK distribution: Firebase App Distribution via `.github/workflows/deploy_android.yml`

The web deployment is now GCP / Firebase-native and no longer targets Azure Static Web Apps.
