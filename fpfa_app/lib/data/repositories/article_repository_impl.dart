import '../../domain/entities/article_feed.dart';
import '../../domain/repositories/article_repository.dart';
import '../datasources/local_article_data_source.dart';
import '../datasources/remote_article_data_source.dart';
import '../models/article_model.dart';

class ArticleRepositoryImpl implements ArticleRepository {
  final RemoteArticleDataSource remoteDataSource;
  final LocalArticleDataSource localDataSource;

  ArticleRepositoryImpl({
    required this.remoteDataSource,
    required this.localDataSource,
  });

  @override
  Future<ArticleFeed> getLatestArticles({int limit = 20}) async {
    final boundedLimit = limit.clamp(1, 50);
    late final List<ArticleModel> remoteArticles;
    try {
      remoteArticles = await remoteDataSource.getLatestArticles(
        limit: boundedLimit,
      );
    } catch (e, stackTrace) {
      // Use cache only when it has data; otherwise surface the fetch failure.
      CachedArticleFeed? cachedFeed;
      try {
        cachedFeed = await localDataSource.getLastArticles();
      } on Object {
        Error.throwWithStackTrace(e, stackTrace);
      }
      if (cachedFeed != null && cachedFeed.articles.isNotEmpty) {
        return ArticleFeed(
          articles: cachedFeed.articles
              .take(boundedLimit)
              .toList(growable: false),
          isStale: true,
          cachedAt: cachedFeed.cachedAt,
        );
      }
      Error.throwWithStackTrace(e, stackTrace);
    }

    // A cache write is an optimization. It must never discard fresh data.
    try {
      await localDataSource.cacheArticles(remoteArticles);
    } on Object {
      // The next successful refresh can repair the cache.
    }
    return ArticleFeed(articles: remoteArticles, isStale: false);
  }
}
