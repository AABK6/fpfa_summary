class Article {
  final String source;
  final String url;
  final String title;
  final String author;
  final String date;
  final String coreThesis;
  final String detailedAbstract;
  final List<String> quotes;

  Article({
    required this.source,
    required this.url,
    required this.title,
    required this.author,
    required this.date,
    required this.coreThesis,
    required this.detailedAbstract,
    required this.quotes,
  });

  String get shortDate {
    final parts = date.split(' ').first.split('-');
    if (parts.length < 3) return date;
    final monthNames = [
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
    final month = int.tryParse(parts[1]) ?? 0;
    final day = int.tryParse(parts[2]) ?? 1;
    return '${monthNames[month]} $day';
  }
}
