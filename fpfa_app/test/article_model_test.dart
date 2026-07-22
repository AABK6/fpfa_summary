import 'package:flutter_test/flutter_test.dart';
import 'package:fpfa_flutter/data/models/article_model.dart';

Map<String, dynamic> _payload() => {
  'source': 'Foreign Policy',
  'url': 'https://foreignpolicy.com/example',
  'title': 'A useful title',
  'author': 'An Author',
  'date_added': '2026-07-22 10:30:00',
  'publication_date': '2026-07-21',
  'core_thesis': 'A thesis.',
  'detailed_abstract': 'A summary.',
  'supporting_data_quotes': '*First quote*Second quote',
};

void main() {
  test('parses publication date and quote separators safely', () {
    final article = ArticleModel.fromJson(_payload());

    expect(article.shortDate, 'July 21, 2026');
    expect(article.quotes, ['First quote', 'Second quote']);
  });

  test('supplies safe copy for optional summary fields', () {
    final payload = _payload()
      ..['author'] = null
      ..['date_added'] = null
      ..['publication_date'] = null
      ..['core_thesis'] = null
      ..['detailed_abstract'] = null
      ..['supporting_data_quotes'] = null;

    final article = ArticleModel.fromJson(payload);

    expect(article.author, 'Author unavailable');
    expect(article.shortDate, 'Date unavailable');
    expect(article.coreThesis, 'No thesis is available.');
    expect(article.quotes, isEmpty);
  });

  test('rejects a missing identity field', () {
    final payload = _payload()..['title'] = '';
    expect(() => ArticleModel.fromJson(payload), throwsFormatException);
  });

  test('rejects a non-web source URL', () {
    final payload = _payload()..['url'] = 'javascript:alert(1)';
    expect(() => ArticleModel.fromJson(payload), throwsFormatException);
  });

  test('rejects a URL whose host does not match the named publisher', () {
    final payload = _payload()..['url'] = 'https://foreignaffairs.com/example';
    expect(() => ArticleModel.fromJson(payload), throwsFormatException);
  });

  test('rejects oversized public fields', () {
    final payload = _payload()..['title'] = 'x' * 501;
    expect(() => ArticleModel.fromJson(payload), throwsFormatException);
  });
}
