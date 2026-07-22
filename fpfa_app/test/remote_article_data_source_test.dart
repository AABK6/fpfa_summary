import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:fpfa_flutter/data/datasources/remote_article_data_source.dart';

Map<String, dynamic> _payload() => {
  'source': 'Foreign Policy',
  'url': 'https://foreignpolicy.com/example',
  'title': 'A title',
  'author': 'An author',
  'date_added': '2026-07-22 10:00:00',
  'core_thesis': 'A thesis',
  'detailed_abstract': 'A summary',
  'supporting_data_quotes': 'A quote',
};

void main() {
  test('sends a bounded limit and parses the public contract', () async {
    late http.Request captured;
    final client = MockClient((request) async {
      captured = request;
      return http.Response(jsonEncode([_payload()]), 200);
    });
    final dataSource = RemoteArticleDataSourceImpl(
      client: client,
      baseUrl: 'https://api.example.com',
    );

    final articles = await dataSource.getLatestArticles(limit: 500);

    expect(
      captured.url.toString(),
      'https://api.example.com/api/articles?limit=50',
    );
    expect(captured.headers['Accept'], 'application/json');
    expect(articles.single.title, 'A title');
  });

  test('rejects a malformed response without leaking a cast error', () async {
    final client = MockClient(
      (_) async => http.Response('{"not":"a list"}', 200),
    );
    final dataSource = RemoteArticleDataSourceImpl(
      client: client,
      baseUrl: 'https://api.example.com',
    );

    await expectLater(
      dataSource.getLatestArticles(),
      throwsA(isA<RemoteArticleException>()),
    );
  });

  test(
    'does not trust a server response larger than the requested page',
    () async {
      final second = Map<String, dynamic>.from(_payload())
        ..['url'] = 'https://foreignpolicy.com/second'
        ..['title'] = 'Second title';
      final client = MockClient(
        (_) async => http.Response(jsonEncode([_payload(), second]), 200),
      );
      final dataSource = RemoteArticleDataSourceImpl(
        client: client,
        baseUrl: 'https://api.example.com',
      );

      final articles = await dataSource.getLatestArticles(limit: 1);

      expect(articles, hasLength(1));
      expect(articles.single.title, 'A title');
    },
  );

  test('surfaces a typed failure for a non-success status', () async {
    final client = MockClient((_) async => http.Response('unavailable', 503));
    final dataSource = RemoteArticleDataSourceImpl(
      client: client,
      baseUrl: 'https://api.example.com',
    );

    await expectLater(
      dataSource.getLatestArticles(),
      throwsA(
        isA<RemoteArticleException>().having(
          (error) => error.message,
          'message',
          contains('503'),
        ),
      ),
    );
  });

  test('rejects a response above the byte budget before decoding', () async {
    final client = MockClient(
      (_) async => http.Response('x' * (2 * 1024 * 1024 + 1), 200),
    );
    final dataSource = RemoteArticleDataSourceImpl(
      client: client,
      baseUrl: 'https://api.example.com',
    );

    await expectLater(
      dataSource.getLatestArticles(),
      throwsA(
        isA<RemoteArticleException>().having(
          (error) => error.message,
          'message',
          contains('too large'),
        ),
      ),
    );
  });
}
