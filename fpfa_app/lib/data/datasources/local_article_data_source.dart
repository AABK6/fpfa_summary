import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/article_model.dart';

abstract class LocalArticleDataSource {
  Future<List<ArticleModel>> getLastArticles();
  Future<void> cacheArticles(List<ArticleModel> articlesToCache);
}

const cachedArticlesKey = 'CACHED_ARTICLES';

class LocalArticleDataSourceImpl implements LocalArticleDataSource {
  final SharedPreferences sharedPreferences;

  LocalArticleDataSourceImpl({required this.sharedPreferences});

  @override
  Future<List<ArticleModel>> getLastArticles() {
    final jsonString = sharedPreferences.getString(cachedArticlesKey);
    if (jsonString != null) {
      final List<dynamic> jsonList = json.decode(jsonString);
      return Future.value(jsonList.map((json) => ArticleModel.fromJson(json)).toList());
    } else {
      return Future.value([]);
    }
  }

  @override
  Future<void> cacheArticles(List<ArticleModel> articlesToCache) {
    final List<Map<String, dynamic>> jsonList = articlesToCache.map((article) => article.toJson()).toList();
    return sharedPreferences.setString(
      cachedArticlesKey,
      json.encode(jsonList),
    );
  }
}
