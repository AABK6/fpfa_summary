import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:fpfa_flutter/data/datasources/local_article_data_source.dart';
import 'package:fpfa_flutter/data/models/article_model.dart';

ArticleModel _article() => ArticleModel(
  source: 'Foreign Affairs',
  url: 'https://foreignaffairs.com/example',
  title: 'A title',
  author: 'An author',
  date: '2026-07-22 10:00:00',
  coreThesis: 'A thesis',
  detailedAbstract: 'A summary',
  quotes: const ['A quote', 'Growth was 2* higher'],
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('stores articles with a UTC cache timestamp', () async {
    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    final dataSource = LocalArticleDataSourceImpl(
      sharedPreferences: preferences,
      now: () => DateTime.utc(2026, 7, 22, 12, 30),
    );

    await dataSource.cacheArticles([_article()]);
    final cached = await dataSource.getLastArticles();

    expect(cached, isNotNull);
    expect(cached!.articles.single.title, 'A title');
    expect(cached.articles.single.quotes, ['A quote', 'Growth was 2* higher']);
    expect(cached.cachedAt, DateTime.utc(2026, 7, 22, 12, 30));
    expect(preferences.containsKey(cachedArticleFeedKey), isTrue);
    expect(preferences.containsKey(cachedArticlesKey), isFalse);
    expect(preferences.containsKey(cachedArticlesAtKey), isFalse);
  });

  test('ignores corrupt cache data', () async {
    SharedPreferences.setMockInitialValues({cachedArticlesKey: '{bad json'});
    final preferences = await SharedPreferences.getInstance();
    final dataSource = LocalArticleDataSourceImpl(
      sharedPreferences: preferences,
    );

    expect(await dataSource.getLastArticles(), isNull);
  });

  test('migrates the two-key legacy cache to one atomic envelope', () async {
    final articleJson = _article().toJson();
    SharedPreferences.setMockInitialValues({
      cachedArticlesKey: jsonEncode([articleJson]),
      cachedArticlesAtKey: '2026-07-22T12:30:00.000Z',
    });
    final preferences = await SharedPreferences.getInstance();
    final dataSource = LocalArticleDataSourceImpl(
      sharedPreferences: preferences,
    );

    final cached = await dataSource.getLastArticles();

    expect(cached!.articles.single.title, 'A title');
    expect(preferences.containsKey(cachedArticleFeedKey), isTrue);
    expect(preferences.containsKey(cachedArticlesKey), isFalse);
    expect(preferences.containsKey(cachedArticlesAtKey), isFalse);
  });
}
