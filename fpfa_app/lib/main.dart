import "dart:math";
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter/foundation.dart'
    show kIsWeb, defaultTargetPlatform, TargetPlatform;

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Latest Summaries',
      theme: ThemeData(primarySwatch: Colors.blue),
      home: const HomePage(),
    );
  }
}

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

  factory Article.fromJson(Map<String, dynamic> json) {
    return Article(
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
}

enum CardState { stacked, front, back, quotes }

class Deck extends StatefulWidget {
  final List<Article> articles;
  const Deck({super.key, required this.articles});

  @override
  State<Deck> createState() => _DeckState();
}

class _DeckState extends State<Deck> {
  late List<CardState> _states;

  @override
  double _offset = 0.0;
  double _dragStartY = 0.0;
  double _dragStartOffset = 0.0;
  int? _focusedIndex;

  @override
  void initState() {
    super.initState();
    _states =
        List.generate(widget.articles.length, (i) => i == 0 ? CardState.front : CardState.stacked);
  }

  void reset() {
    setState(() {
      _states =
          List.generate(widget.articles.length, (i) => i == 0 ? CardState.front : CardState.stacked);
      _offset = 0.0;
      _focusedIndex = null;
    });
  }

  void _onCardTap(int index) {
    setState(() {
      final current = _states[index];
      if (current == CardState.stacked) {
        for (int i = 0; i < _states.length; i++) {
          _states[i] = CardState.stacked;
        }
        _states[index] = CardState.front;
        _offset = index.toDouble();
        _focusedIndex = index;
      } else if (current == CardState.front) {
        _states[index] = CardState.back;
        _focusedIndex = index;
      } else if (current == CardState.back) {
        _states[index] = CardState.quotes;
        _focusedIndex = index;
      } else if (current == CardState.quotes) {
        _states[index] = CardState.front;
        _focusedIndex = index;
      }
    });
  }

  void _onDragStart(DragStartDetails details) {
    _dragStartY = details.localPosition.dy;
    _dragStartOffset = _offset;
  }

  void _onDragUpdate(DragUpdateDetails details) {
    if (_focusedIndex != null) return;
    final diff = (details.localPosition.dy - _dragStartY) / 50.0;
    setState(() {
      _offset = (_dragStartOffset - diff).clamp(0.0, widget.articles.length - 1).toDouble();
    });
  }

  @override
  Widget build(BuildContext context) {
    final total = widget.articles.length;
    return GestureDetector(
      onVerticalDragStart: _onDragStart,
      onVerticalDragUpdate: _onDragUpdate,
      child: SizedBox(
        width: 600,
        height: MediaQuery.of(context).size.height * 0.8,
        child: Stack(
          alignment: Alignment.bottomCenter,
          children: List.generate(total, (i) {
            final depth = (i - _offset);
            final state = _states[i];
            final bottom = depth * 40.0;
            final scale = (1 - depth * 0.05).clamp(0.7, 1.0);
            if (bottom > MediaQuery.of(context).size.height || bottom < -200) {
              return const SizedBox.shrink();
            }
            return Positioned(
              bottom: bottom,
              child: AnimatedScale(
                duration: const Duration(milliseconds: 300),
                scale: scale,
                child: ArticleCard(
                  article: widget.articles[i],
                  state: state,
                  onTap: () => _onCardTap(i),
                ),
              ),
            );
          }),
        ),
      ),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final GlobalKey<_DeckState> _deckKey = GlobalKey<_DeckState>();

  List<Article> articles = [];
  bool loading = true;
  String error = '';

  @override
  void initState() {
    super.initState();
    _loadArticles();
  }

  Future<void> _loadArticles() async {
    try {
      final defaultUrl = (!kIsWeb &&
              defaultTargetPlatform == TargetPlatform.android)
          ? 'http://10.0.2.2:5000'
          : 'http://localhost:5000';
      const envUrl = String.fromEnvironment('API_BASE_URL');
      final baseUrl = envUrl.isNotEmpty ? envUrl : defaultUrl;
      final response = await http.get(
        Uri.parse('$baseUrl/api/articles'),
      );
      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        setState(() {
          articles = data.map((e) => Article.fromJson(e)).toList();
          loading = false;
          error = '';
        });
      } else {
        debugPrint('Failed to load articles: ${response.statusCode}');
        setState(() {
          loading = false;
          error = 'Failed to load articles';
        });
      }
    } catch (e) {
      debugPrint('Error loading articles: $e');
      setState(() {
        loading = false;
        error = 'Failed to load articles';
      });
    }
  }

  void _handleTapDown(TapDownDetails details) {
    final box = _deckKey.currentContext?.findRenderObject() as RenderBox?;
    if (box != null) {
      final offset = box.localToGlobal(Offset.zero);
      final rect = offset & box.size;
      if (!rect.contains(details.globalPosition)) {
        _deckKey.currentState?.reset();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF0F2F5),
      body: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTapDown: _handleTapDown,
        child: Center(
          child: loading
              ? const CircularProgressIndicator()
              : articles.isEmpty
                  ? Text(error.isEmpty ? 'No articles found' : error)
                  : Deck(key: _deckKey, articles: articles),
        ),
      ),
    );
  }
}

class ArticleCard extends StatefulWidget {
  final Article article;
  final CardState state;
  final VoidCallback onTap;
  const ArticleCard({
    super.key,
    required this.article,
    required this.state,
    required this.onTap,
  });

  @override
  State<ArticleCard> createState() => _ArticleCardState();
}

class _ArticleCardState extends State<ArticleCard> {
  late CardState _state;

  @override
  void initState() {
    super.initState();
    _state = widget.state;
  }

  @override
  void didUpdateWidget(covariant ArticleCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.state != widget.state) {
      setState(() {
        _state = widget.state;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isStacked = _state == CardState.stacked;
    final isFront = _state == CardState.front;
    final showQuotes = _state == CardState.quotes;
    final maxHeight = isStacked
        ? 60.0
        : MediaQuery.of(context).size.height * 0.7;

    Widget inner;
    if (isStacked) {
      inner = _StackedCard(article: widget.article);
    } else {
      inner = SingleChildScrollView(
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 600),
          transitionBuilder: (child, animation) {
            final rotate = Tween(begin: pi, end: 0.0).animate(animation);
            return AnimatedBuilder(
              animation: rotate,
              child: child,
              builder: (context, child) {
                final isUnder = (ValueKey(isFront) != child!.key);
                var tilt = ((animation.value - 0.5).abs() - 0.5) * 0.003;
                tilt *= isUnder ? -1.0 : 1.0;
                final value = isUnder ? min(rotate.value, pi / 2) : rotate.value;
                return Transform(
                  transform: Matrix4.rotationY(value)..setEntry(3, 0, tilt),
                  alignment: Alignment.center,
                  child: child,
                );
              },
            );
          },
          layoutBuilder: (widget, list) {
            return Stack(children: [widget!, ...list]);
          },
          child: isFront
              ? _FrontCard(article: widget.article, key: const ValueKey(true))
              : _BackCard(
                  article: widget.article,
                  showQuotes: showQuotes,
                  key: const ValueKey(false),
                ),
        ),
      );
    }

    return GestureDetector(
      onTap: widget.onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        margin: const EdgeInsets.only(bottom: 20),
        constraints: BoxConstraints(maxHeight: maxHeight, maxWidth: 600),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: const [
            BoxShadow(
              color: Colors.black26,
              blurRadius: 8,
              offset: Offset(0, 2),
            ),
          ],
        ),
        child: inner,
      ),
    );
  }
}

class _FrontCard extends StatelessWidget {
  final Article article;
  const _FrontCard({required this.article, super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        _TitleBar(article: article),
        Padding(
          padding: const EdgeInsets.all(15),
          child: Text(
            article.coreThesis,
            style: const TextStyle(fontSize: 16, color: Colors.black87),
          ),
        ),
      ],
    );
  }
}

class _BackCard extends StatelessWidget {
  final Article article;
  final bool showQuotes;
  const _BackCard({required this.article, required this.showQuotes, super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        _TitleBar(article: article),
        Padding(
          padding: const EdgeInsets.all(15),
          child: Text(
            article.detailedAbstract,
            style: const TextStyle(fontSize: 16, color: Colors.black87),
          ),
        ),
        if (showQuotes)
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 15, vertical: 10),
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFFF8F9FA),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: article.quotes
                  .map(
                    (q) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Text(
                        '• $q',
                        style: const TextStyle(fontStyle: FontStyle.italic),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ),
        Align(
          alignment: Alignment.centerRight,
          child: Padding(
            padding: const EdgeInsets.only(right: 15, bottom: 15),
            child: TextButton(
              onPressed: () {
                // In a real app you would use url_launcher
              },
              child: Text(
                'read on ${article.source == 'Foreign Policy' ? 'foreignpolicy.com' : 'foreignaffairs.com'}',
                style: const TextStyle(color: Colors.grey),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _StackedCard extends StatelessWidget {
  final Article article;
  const _StackedCard({required this.article});

  @override
  Widget build(BuildContext context) {
    return _TitleBar(article: article);
  }
}

class _TitleBar extends StatelessWidget {
  final Article article;
  const _TitleBar({required this.article});

  @override
  Widget build(BuildContext context) {
    final isFP = article.source == 'Foreign Policy';
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: isFP ? const Color(0xFFFFCCCC) : const Color(0xFFCCEEFF),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
        border: const Border(bottom: BorderSide(color: Color(0xFFDDDDDD))),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            article.title,
            style: const TextStyle(fontSize: 18, color: Colors.black87),
          ),
          const SizedBox(height: 4),
          Text(
            '${article.source} — ${article.author}',
            style: const TextStyle(fontSize: 14, color: Colors.black54),
          ),
          Align(
            alignment: Alignment.centerRight,
            child: Text(
              article.shortDate,
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ),
        ],
      ),
    );
  }
}
