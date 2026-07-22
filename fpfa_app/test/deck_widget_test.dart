import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fpfa_flutter/core/theme.dart';
import 'package:fpfa_flutter/domain/entities/article.dart';
import 'package:fpfa_flutter/presentation/widgets/deck_widget.dart';

Article _article({
  required String title,
  required String thesis,
  required String summary,
  String source = 'Foreign Policy',
}) {
  return Article(
    source: source,
    url: 'https://example.com/${title.toLowerCase().replaceAll(' ', '-')}',
    title: title,
    author: 'Author',
    date: '2026-07-22 10:00:00',
    coreThesis: thesis,
    detailedAbstract: summary,
    quotes: const ['Evidence one', 'Evidence two'],
  );
}

Widget _app(List<Article> articles) {
  return MaterialApp(
    theme: AppTheme.lightTheme,
    home: Scaffold(
      body: SizedBox.expand(child: Deck(articles: articles)),
    ),
  );
}

void main() {
  final articles = [
    _article(
      title: 'Latest article title',
      thesis: 'Latest thesis',
      summary: 'Latest detailed summary',
    ),
    _article(
      title: 'Previous article title',
      thesis: 'Previous thesis',
      summary: 'Previous detailed summary',
      source: 'Foreign Affairs',
    ),
  ];

  testWidgets('starts with the latest article and exposes explicit sections', (
    tester,
  ) async {
    await tester.pumpWidget(_app(articles));

    expect(find.text('1 of 2 · newest first'), findsOneWidget);
    expect(find.text('Latest thesis'), findsOneWidget);

    await tester.tap(find.widgetWithText(OutlinedButton, 'Summary'));
    await tester.pumpAndSettle();
    expect(find.text('Latest detailed summary'), findsOneWidget);

    await tester.tap(find.widgetWithText(OutlinedButton, 'Evidence'));
    await tester.pumpAndSettle();
    expect(find.text('Evidence one'), findsOneWidget);
  });

  testWidgets('navigates toward older articles and resets the section', (
    tester,
  ) async {
    await tester.pumpWidget(_app(articles));
    await tester.tap(find.widgetWithText(OutlinedButton, 'Summary'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Older'));
    await tester.pumpAndSettle();

    expect(find.text('2 of 2 · newest first'), findsOneWidget);
    expect(find.text('Previous thesis'), findsOneWidget);
    expect(find.text('Previous detailed summary'), findsNothing);
  });

  testWidgets('fits a 320 pixel viewport without layout exceptions', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 700);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_app(articles));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text('1 of 2 · newest first'), findsOneWidget);
  });

  testWidgets('meets labeled target and contrast guidelines', (tester) async {
    final semantics = tester.ensureSemantics();
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_app(articles));
    await tester.pumpAndSettle();

    await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
    await expectLater(tester, meetsGuideline(iOSTapTargetGuideline));
    await expectLater(tester, meetsGuideline(textContrastGuideline));
    semantics.dispose();
  });
}
