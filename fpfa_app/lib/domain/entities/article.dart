class Article {
  final String source;
  final String url;
  final String title;
  final String author;
  final String date;
  final String? publicationDate;
  final String coreThesis;
  final String detailedAbstract;
  final List<String> quotes;

  Article({
    required this.source,
    required this.url,
    required this.title,
    required this.author,
    required this.date,
    this.publicationDate,
    required this.coreThesis,
    required this.detailedAbstract,
    required this.quotes,
  });

  String get shortDate {
    final parsed =
        DateTime.tryParse(publicationDate ?? '') ?? DateTime.tryParse(date);
    if (parsed == null) return 'Date unavailable';
    const monthNames = [
      '',
      'January',
      'February',
      'March',
      'April',
      'May',
      'June',
      'July',
      'August',
      'September',
      'October',
      'November',
      'December',
    ];
    return '${monthNames[parsed.month]} ${parsed.day}, ${parsed.year}';
  }
}
