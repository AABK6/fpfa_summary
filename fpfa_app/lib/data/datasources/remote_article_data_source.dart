import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/article_model.dart';

abstract class RemoteArticleDataSource {
  Future<List<ArticleModel>> getLatestArticles({int limit = 20});
}

class RemoteArticleDataSourceImpl implements RemoteArticleDataSource {
  final http.Client client;
  final String baseUrl;

  RemoteArticleDataSourceImpl({required this.client, required this.baseUrl});

  @override
  Future<List<ArticleModel>> getLatestArticles({int limit = 20}) async {
    final response = await client.get(
      Uri.parse('$baseUrl/api/articles'),
      headers: {'Content-Type': 'application/json'},
    );

    if (response.statusCode == 200) {
      final List<dynamic> jsonList = json.decode(response.body);
      return jsonList.map((json) => ArticleModel.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load articles from remote');
    }
  }
}
