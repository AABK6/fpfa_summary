import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/article_model.dart';

class RemoteArticleException implements Exception {
  const RemoteArticleException(this.message);

  final String message;

  @override
  String toString() => message;
}

abstract class RemoteArticleDataSource {
  Future<List<ArticleModel>> getLatestArticles({int limit = 20});
}

class RemoteArticleDataSourceImpl implements RemoteArticleDataSource {
  static const int _maxResponseBytes = 2 * 1024 * 1024;
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
    final boundedLimit = limit.clamp(1, 50);
    final endpoint = Uri.parse(
      '$baseUrl/api/articles',
    ).replace(queryParameters: {'limit': '$boundedLimit'});
    final request = http.Request('GET', endpoint)
      ..headers['Accept'] = 'application/json';
    final response = await client.send(request).timeout(requestTimeout);

    final declaredLength = response.contentLength;
    if (declaredLength != null && declaredLength > _maxResponseBytes) {
      throw const RemoteArticleException('The server response is too large.');
    }
    final bytes = <int>[];
    await for (final chunk in response.stream.timeout(requestTimeout)) {
      if (bytes.length + chunk.length > _maxResponseBytes) {
        throw const RemoteArticleException('The server response is too large.');
      }
      bytes.addAll(chunk);
    }

    if (response.statusCode == 200) {
      final decoded = json.decode(utf8.decode(bytes));
      if (decoded is! List) {
        throw const RemoteArticleException(
          'The server returned an invalid response.',
        );
      }
      try {
        return decoded
            .take(boundedLimit)
            .map(
              (item) =>
                  ArticleModel.fromJson(Map<String, dynamic>.from(item as Map)),
            )
            .toList(growable: false);
      } on Object catch (error) {
        throw RemoteArticleException(
          'The server returned malformed article data: $error',
        );
      }
    }
    throw RemoteArticleException(
      'The server returned status ${response.statusCode}.',
    );
  }
}
