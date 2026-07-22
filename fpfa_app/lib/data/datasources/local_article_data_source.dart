import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/article_model.dart';

abstract class LocalArticleDataSource {
  Future<CachedArticleFeed?> getLastArticles();
  Future<void> cacheArticles(List<ArticleModel> articlesToCache);
}

const cachedArticlesKey = 'CACHED_ARTICLES';
const cachedArticlesAtKey = 'CACHED_ARTICLES_AT';
const cachedArticleFeedKey = 'CACHED_ARTICLE_FEED_V1';

class CachedArticleFeed {
  const CachedArticleFeed({required this.articles, this.cachedAt});

  final List<ArticleModel> articles;
  final DateTime? cachedAt;
}

class LocalArticleDataSourceImpl implements LocalArticleDataSource {
  final SharedPreferences sharedPreferences;
  final DateTime Function() now;

  LocalArticleDataSourceImpl({
    required this.sharedPreferences,
    DateTime Function()? now,
  }) : now = now ?? DateTime.now;

  @override
  Future<CachedArticleFeed?> getLastArticles() async {
    final envelope = sharedPreferences.getString(cachedArticleFeedKey);
    if (envelope != null) {
      try {
        return _decodeEnvelope(envelope);
      } on Object {
        return null;
      }
    }

    final jsonString = sharedPreferences.getString(cachedArticlesKey);
    if (jsonString != null) {
      try {
        final List<dynamic> jsonList = json.decode(jsonString);
        final cachedAtValue = sharedPreferences.getString(cachedArticlesAtKey);
        final feed = CachedArticleFeed(
          articles: jsonList
              .map(
                (item) => ArticleModel.fromJson(
                  Map<String, dynamic>.from(item as Map),
                ),
              )
              .toList(growable: false),
          cachedAt: DateTime.tryParse(cachedAtValue ?? ''),
        );
        await _writeEnvelope(feed);
        await sharedPreferences.remove(cachedArticlesKey);
        await sharedPreferences.remove(cachedArticlesAtKey);
        return feed;
      } on Object {
        return null;
      }
    }
    return null;
  }

  @override
  Future<void> cacheArticles(List<ArticleModel> articlesToCache) async {
    await _writeEnvelope(
      CachedArticleFeed(articles: articlesToCache, cachedAt: now().toUtc()),
    );
  }

  CachedArticleFeed _decodeEnvelope(String raw) {
    final decoded = Map<String, dynamic>.from(json.decode(raw) as Map);
    if (decoded['version'] != 1 || decoded['articles'] is! List) {
      throw const FormatException('Unsupported cache envelope.');
    }
    return CachedArticleFeed(
      articles: (decoded['articles'] as List)
          .map(
            (item) =>
                ArticleModel.fromJson(Map<String, dynamic>.from(item as Map)),
          )
          .toList(growable: false),
      cachedAt: DateTime.tryParse(decoded['cachedAt']?.toString() ?? ''),
    );
  }

  Future<void> _writeEnvelope(CachedArticleFeed feed) async {
    final payload = json.encode({
      'version': 1,
      'cachedAt': feed.cachedAt?.toUtc().toIso8601String(),
      'articles': feed.articles.map((article) => article.toJson()).toList(),
    });
    final committed = await sharedPreferences.setString(
      cachedArticleFeedKey,
      payload,
    );
    if (!committed) {
      throw StateError('The article cache could not be committed.');
    }
  }
}
