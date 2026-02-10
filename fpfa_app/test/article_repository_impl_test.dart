import 'package:flutter_test/flutter_test.dart';
import 'package:fpfa_flutter/data/datasources/local_article_data_source.dart';
import 'package:fpfa_flutter/data/datasources/remote_article_data_source.dart';
import 'package:fpfa_flutter/data/models/article_model.dart';
import 'package:fpfa_flutter/data/repositories/article_repository_impl.dart';

class FakeRemoteArticleDataSource implements RemoteArticleDataSource {
  FakeRemoteArticleDataSource({
    this.articles = const [],
    this.error,
  });

  final List<ArticleModel> articles;
  final Exception? error;
  int callCount = 0;

  @override
  Future<List<ArticleModel>> getLatestArticles({int limit = 20}) async {
    callCount += 1;
    if (error != null) {
      throw error!;
    }
    return articles;
  }
}

class FakeLocalArticleDataSource implements LocalArticleDataSource {
  FakeLocalArticleDataSource({this.cachedArticles = const []});

  final List<ArticleModel> cachedArticles;
  int getLastArticlesCallCount = 0;
  int cacheArticlesCallCount = 0;
  List<ArticleModel> lastCachedPayload = const [];

  @override
  Future<void> cacheArticles(List<ArticleModel> articlesToCache) async {
    cacheArticlesCallCount += 1;
    lastCachedPayload = articlesToCache;
  }

  @override
  Future<List<ArticleModel>> getLastArticles() async {
    getLastArticlesCallCount += 1;
    return cachedArticles;
  }
}

ArticleModel _sampleArticle({
  String title = 'Title',
  String url = 'https://example.com/article',
}) {
  return ArticleModel(
    source: 'Foreign Policy',
    url: url,
    title: title,
    author: 'Author',
    date: '2026-02-10 10:00:00',
    coreThesis: 'Core thesis',
    detailedAbstract: 'Detailed abstract',
    quotes: const ['Quote 1', 'Quote 2'],
  );
}

void main() {
  group('ArticleRepositoryImpl', () {
    test('returns remote articles and caches them when remote fetch succeeds', () async {
      final remoteArticles = [_sampleArticle(title: 'Remote')];
      final remoteDataSource = FakeRemoteArticleDataSource(articles: remoteArticles);
      final localDataSource = FakeLocalArticleDataSource();
      final repository = ArticleRepositoryImpl(
        remoteDataSource: remoteDataSource,
        localDataSource: localDataSource,
      );

      final result = await repository.getLatestArticles(limit: 20);

      expect(result, remoteArticles);
      expect(remoteDataSource.callCount, 1);
      expect(localDataSource.cacheArticlesCallCount, 1);
      expect(localDataSource.lastCachedPayload, remoteArticles);
      expect(localDataSource.getLastArticlesCallCount, 0);
    });

    test('returns cached articles when remote fetch fails and cache is available', () async {
      final cachedArticles = [_sampleArticle(title: 'Cached')];
      final remoteDataSource = FakeRemoteArticleDataSource(
        error: Exception('remote unavailable'),
      );
      final localDataSource = FakeLocalArticleDataSource(
        cachedArticles: cachedArticles,
      );
      final repository = ArticleRepositoryImpl(
        remoteDataSource: remoteDataSource,
        localDataSource: localDataSource,
      );

      final result = await repository.getLatestArticles(limit: 20);

      expect(result, cachedArticles);
      expect(remoteDataSource.callCount, 1);
      expect(localDataSource.getLastArticlesCallCount, 1);
      expect(localDataSource.cacheArticlesCallCount, 0);
    });

    test('rethrows remote fetch error when cache is empty', () async {
      final remoteDataSource = FakeRemoteArticleDataSource(
        error: Exception('remote unavailable'),
      );
      final localDataSource = FakeLocalArticleDataSource(cachedArticles: const []);
      final repository = ArticleRepositoryImpl(
        remoteDataSource: remoteDataSource,
        localDataSource: localDataSource,
      );

      expect(
        () => repository.getLatestArticles(limit: 20),
        throwsA(
          isA<Exception>().having(
            (e) => e.toString(),
            'message',
            contains('remote unavailable'),
          ),
        ),
      );
      expect(remoteDataSource.callCount, 1);
      expect(localDataSource.getLastArticlesCallCount, 1);
      expect(localDataSource.cacheArticlesCallCount, 0);
    });
  });
}
