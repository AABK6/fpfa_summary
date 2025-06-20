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

## Troubleshooting
If the Flutter app displays **"Failed to load articles"**, confirm the backend is reachable and that the app is using the correct API URL.

1. Start the Flask server (from this directory):
   ```bash
   pip install -r requirements.txt
   python app.py
   ```
2. Verify the endpoint returns data:
   ```bash
   curl http://localhost:5000/api/articles | head
   ```
   You should see JSON output.
3. Run the Flutter app with an explicit API URL (adjust if the server runs elsewhere):
   ```bash
   flutter run -d edge --dart-define=API_BASE_URL=http://localhost:5000
   ```
4. Ensure `articles.db` exists in the project root so the backend can read the database.

