import '../entities/article.dart';
import '../repositories/article_repository.dart';

class GetArticles {
  final ArticleRepository repository;

  GetArticles(this.repository);

  Future<List<Article>> execute({int limit = 20}) async {
    return await repository.getLatestArticles(limit: limit);
  }
}
