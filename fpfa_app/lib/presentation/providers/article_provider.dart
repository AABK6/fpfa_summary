import 'package:flutter/material.dart';
import '../../domain/entities/article.dart';
import '../../domain/usecases/get_articles.dart';

enum ArticleState { initial, loading, loaded, error }

class ArticleProvider with ChangeNotifier {
  final GetArticles getArticlesUseCase;
  bool _disposed = false;

  ArticleProvider({required this.getArticlesUseCase});

  List<Article> _articles = [];
  List<Article> get articles => _articles;

  ArticleState _state = ArticleState.initial;
  ArticleState get state => _state;

  String _errorMessage = '';
  String get errorMessage => _errorMessage;

  bool _isStale = false;
  bool get isStale => _isStale;

  bool _isRefreshing = false;
  bool get isRefreshing => _isRefreshing;

  DateTime? _cachedAt;
  DateTime? get cachedAt => _cachedAt;

  Future<void> fetchArticles({int limit = 20}) async {
    if (_disposed) return;
    final hadArticles = _articles.isNotEmpty;
    _state = hadArticles ? ArticleState.loaded : ArticleState.loading;
    _isRefreshing = hadArticles;
    _errorMessage = '';
    _notifyIfActive();

    try {
      final feed = await getArticlesUseCase.execute(limit: limit);
      _articles = feed.articles;
      _isStale = feed.isStale;
      _cachedAt = feed.cachedAt;
      _state = ArticleState.loaded;
    } on Object {
      _isStale = hadArticles;
      _state = hadArticles ? ArticleState.loaded : ArticleState.error;
      _errorMessage =
          'We could not refresh the summaries. Check your connection and try again.';
    } finally {
      _isRefreshing = false;
      _notifyIfActive();
    }
  }

  void _notifyIfActive() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
