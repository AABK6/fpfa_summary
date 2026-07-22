import '../../domain/entities/article.dart';

class ArticleModel extends Article {
  ArticleModel({
    required super.source,
    required super.url,
    required super.title,
    required super.author,
    required super.date,
    super.publicationDate,
    required super.coreThesis,
    required super.detailedAbstract,
    required super.quotes,
  });

  factory ArticleModel.fromJson(Map<String, dynamic> json) {
    String requiredString(String key, {required int maxLength}) {
      final value = json[key];
      if (value is! String || value.trim().isEmpty) {
        throw const FormatException(
          'Article response contains a missing field.',
        );
      }
      final normalized = value.trim();
      if (normalized.length > maxLength) {
        throw const FormatException(
          'Article response contains an oversized field.',
        );
      }
      return normalized;
    }

    String? optionalString(String key, {required int maxLength}) {
      final value = json[key];
      if (value == null) return null;
      final text = value.toString().trim();
      if (text.length > maxLength) {
        throw const FormatException(
          'Article response contains an oversized field.',
        );
      }
      return text.isEmpty ? null : text;
    }

    String requiredPublisherUrl(String key, String source) {
      final value = requiredString(key, maxLength: 2048);
      final uri = Uri.tryParse(value);
      final expectedHost = switch (source) {
        'Foreign Affairs' => 'foreignaffairs.com',
        'Foreign Policy' => 'foreignpolicy.com',
        _ => '',
      };
      final host = uri?.host.toLowerCase() ?? '';
      if (uri == null ||
          uri.scheme.toLowerCase() != 'https' ||
          expectedHost.isEmpty ||
          (host != expectedHost && !host.endsWith('.$expectedHost'))) {
        throw const FormatException(
          'Article response contains an invalid publisher URL.',
        );
      }
      return value;
    }

    final source = requiredString('source', maxLength: 64);

    return ArticleModel(
      source: source,
      url: requiredPublisherUrl('url', source),
      title: requiredString('title', maxLength: 500),
      author: optionalString('author', maxLength: 500) ?? 'Author unavailable',
      date: optionalString('date_added', maxLength: 64) ?? '',
      publicationDate: optionalString('publication_date', maxLength: 64),
      coreThesis:
          optionalString('core_thesis', maxLength: 4000) ??
          'No thesis is available.',
      detailedAbstract:
          optionalString('detailed_abstract', maxLength: 20000) ??
          'No summary is available.',
      quotes: _parseQuotes(json['supporting_data_quotes']),
    );
  }

  static List<String> _parseQuotes(dynamic value) {
    if (value is List) {
      if (value.length > 20) {
        throw const FormatException(
          'Article response contains too many quotes.',
        );
      }
      final quotes = value
          .map((item) => item.toString().trim())
          .where((item) => item.isNotEmpty)
          .toList(growable: false);
      if (quotes.any((quote) => quote.length > 4000)) {
        throw const FormatException(
          'Article response contains an oversized quote.',
        );
      }
      return quotes;
    }
    final text = value?.toString().trim() ?? '';
    if (text.isEmpty) return const [];
    if (text.length > 12000) {
      throw const FormatException(
        'Article response contains oversized quotes.',
      );
    }
    return text
        .split(RegExp(r'\s*\*\s*|\n\s*[-•]\s*'))
        .map((quote) => quote.trim())
        .where((quote) => quote.isNotEmpty)
        .toList(growable: false);
  }

  Map<String, dynamic> toJson() {
    return {
      'source': source,
      'url': url,
      'title': title,
      'author': author,
      'date_added': date,
      'publication_date': publicationDate,
      'core_thesis': coreThesis,
      'detailed_abstract': detailedAbstract,
      'supporting_data_quotes': quotes,
    };
  }
}
