import '../../domain/entities/article.dart';
import '../../domain/repositories/article_repository.dart';
import '../datasources/local_article_data_source.dart';
import '../datasources/remote_article_data_source.dart';

class ArticleRepositoryImpl implements ArticleRepository {
  final RemoteArticleDataSource remoteDataSource;
  final LocalArticleDataSource localDataSource;

  ArticleRepositoryImpl({
    required this.remoteDataSource,
    required this.localDataSource,
  });

  @override
  Future<List<Article>> getLatestArticles({int limit = 20}) async {
    try {
      final remoteArticles = await remoteDataSource.getLatestArticles(limit: limit);
      await localDataSource.cacheArticles(remoteArticles);
      return remoteArticles;
    } catch (e) {
      // Fallback to local cache if remote fails
      return await localDataSource.getLastArticles();
    }
  }
}
