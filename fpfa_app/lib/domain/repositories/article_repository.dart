import '../entities/article.dart';

abstract class ArticleRepository {
  Future<List<Article>> getLatestArticles({int limit = 20});
}
