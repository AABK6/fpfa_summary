import '../entities/article_feed.dart';

abstract class ArticleRepository {
  Future<ArticleFeed> getLatestArticles({int limit = 20});
}
