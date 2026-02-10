import 'dart:math';
import 'package:flutter/material.dart';
import '../../core/theme.dart';
import '../../domain/entities/article.dart';
import 'deck_widget.dart';

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
    final isFront = _state == CardState.front || _state == CardState.stacked;
    final showQuotes = _state == CardState.quotes;
    return GestureDetector(
      onTap: widget.onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        margin: const EdgeInsets.only(bottom: 20),
        height: _state == CardState.stacked ? 40 : null,
        decoration: BoxDecoration(
          color: AppTheme.cardBackground,
          borderRadius: BorderRadius.circular(16),
          boxShadow: const [
            BoxShadow(
              color: Colors.black26,
              blurRadius: 8,
              offset: Offset(0, 2),
            ),
          ],
        ),
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
                final value =
                    isUnder ? min(rotate.value, pi / 2) : rotate.value;
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
            style: Theme.of(context).textTheme.bodyLarge,
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
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ),
        if (showQuotes)
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 15, vertical: 10),
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppTheme.quoteBackground,
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
                style: Theme.of(context).textTheme.labelSmall,
              ),
            ),
          ),
        ),
      ],
    );
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
        color: isFP ? AppTheme.fpTitleBackground : AppTheme.faTitleBackground,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
        border: const Border(bottom: BorderSide(color: AppTheme.dividerColor)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            article.title,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 4),
          Text(
            '${article.source} — ${article.author}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          Align(
            alignment: Alignment.centerRight,
            child: Text(
              article.shortDate,
              style: Theme.of(context).textTheme.labelSmall,
            ),
          ),
        ],
      ),
    );
  }
}
