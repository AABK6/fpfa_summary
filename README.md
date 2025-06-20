# Foreign Policy & Foreign Affairs Summaries

This repository contains a small Flask backend that serves article summaries from `articles.db` and a Flutter front-end (`fpfa_app`) that displays them.

## Running the backend

```bash
pip install -r requirements.txt
python app.py
```

The API will be available at `http://localhost:5000/api/articles` by default.

## Running the Flutter app

From the `fpfa_app` directory, run `flutter run`. The app expects the backend URL specified by the `API_BASE_URL` compile-time environment variable. If none is supplied, it defaults to `http://localhost:5000` (or `http://10.0.2.2:5000` when running on the Android emulator).

Example:

```bash
flutter run -d chrome --dart-define=API_BASE_URL=http://192.168.1.100:5000
```
