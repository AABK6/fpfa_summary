import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/article_model.dart';

abstract class RemoteArticleDataSource {
  Future<List<ArticleModel>> getLatestArticles({int limit = 20});
}

class RemoteArticleDataSourceImpl implements RemoteArticleDataSource {
  final http.Client client;
  final String baseUrl;
  final Duration requestTimeout;

  RemoteArticleDataSourceImpl({
    required this.client,
    required this.baseUrl,
    this.requestTimeout = const Duration(seconds: 10),
  });

  @override
  Future<List<ArticleModel>> getLatestArticles({int limit = 20}) async {
    final response = await client.get(
      Uri.parse('$baseUrl/api/articles'),
      headers: {'Content-Type': 'application/json'},
    ).timeout(requestTimeout);

    if (response.statusCode == 200) {
      final List<dynamic> jsonList = json.decode(response.body);
      return jsonList.map((json) => ArticleModel.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load articles from remote');
    }
  }
}
