import '../../domain/entities/article.dart';

class ArticleModel extends Article {
  ArticleModel({
    required super.source,
    required super.url,
    required super.title,
    required super.author,
    required super.date,
    required super.coreThesis,
    required super.detailedAbstract,
    required super.quotes,
  });

  factory ArticleModel.fromJson(Map<String, dynamic> json) {
    return ArticleModel(
      source: json['source'] as String,
      url: json['url'] as String,
      title: json['title'] as String,
      author: json['author'] as String,
      date: json['date_added'] as String,
      coreThesis: json['core_thesis'] as String,
      detailedAbstract: json['detailed_abstract'] as String,
      quotes: (json['supporting_data_quotes'] as String)
          .split('*')
          .where((q) => q.trim().isNotEmpty)
          .toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'source': source,
      'url': url,
      'title': title,
      'author': author,
      'date_added': date,
      'core_thesis': coreThesis,
      'detailed_abstract': detailedAbstract,
      'supporting_data_quotes': quotes.join('*'),
    };
  }
}
