import 'package:flutter/material.dart';
import '../../domain/entities/article.dart';
import '../../domain/usecases/get_articles.dart';

enum ArticleState { initial, loading, loaded, error }

class ArticleProvider with ChangeNotifier {
  final GetArticles getArticlesUseCase;

  ArticleProvider({required this.getArticlesUseCase});

  List<Article> _articles = [];
  List<Article> get articles => _articles;

  ArticleState _state = ArticleState.initial;
  ArticleState get state => _state;

  String _errorMessage = '';
  String get errorMessage => _errorMessage;

  Future<void> fetchArticles({int limit = 20}) async {
    _state = ArticleState.loading;
    _errorMessage = '';
    notifyListeners();

    try {
      _articles = await getArticlesUseCase.execute(limit: limit);
      _state = ArticleState.loaded;
    } catch (e) {
      _state = ArticleState.error;
      _errorMessage = 'Failed to load articles: $e';
    } finally {
      notifyListeners();
    }
  }
}
