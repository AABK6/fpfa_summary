import 'article.dart';

class ArticleFeed {
  const ArticleFeed({
    required this.articles,
    required this.isStale,
    this.cachedAt,
  });

  final List<Article> articles;
  final bool isStale;
  final DateTime? cachedAt;
}
