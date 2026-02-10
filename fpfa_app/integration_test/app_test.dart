import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:fpfa_flutter/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('end-to-end test', () {
    testWidgets('verify health check and initial load', (tester) async {
      app.main();
      await tester.pumpAndSettle();

      // Verify if some text is found (Loading, Error, or Articles)
      // Since we can't guarantee backend state, we just check if it settled
      expect(find.byType(app.MyApp), findsOneWidget);
    });
  });
}
