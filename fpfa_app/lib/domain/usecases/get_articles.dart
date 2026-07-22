import '../entities/article_feed.dart';
import '../repositories/article_repository.dart';

class GetArticles {
  final ArticleRepository repository;

  GetArticles(this.repository);

  Future<ArticleFeed> execute({int limit = 20}) {
    return repository.getLatestArticles(limit: limit);
  }
}
