import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:fpfa_flutter/main.dart' as app;
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('application boot', () {
    testWidgets('mounts the production application root', (tester) async {
      SharedPreferences.setMockInitialValues({});
      await app.main();
      await tester.pump();

      expect(find.byType(app.MyApp), findsOneWidget);
    });
  });
}
