import 'package:flutter/material.dart';
import '../../domain/entities/article.dart';
import 'article_card_widget.dart';

enum CardState { stacked, front, back, quotes }

class Deck extends StatefulWidget {
  final List<Article> articles;
  const Deck({super.key, required this.articles});

  @override
  State<Deck> createState() => DeckState();
}

class DeckState extends State<Deck> {
  late List<CardState> _states;

  @override
  void initState() {
    super.initState();
    _states = List.generate(
      widget.articles.length,
      (i) =>
          i == widget.articles.length - 1 ? CardState.front : CardState.stacked,
    );
  }

  void reset() {
    setState(() {
      _states = List.generate(
        widget.articles.length,
        (i) => i == widget.articles.length - 1
            ? CardState.front
            : CardState.stacked,
      );
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
      } else if (current == CardState.front) {
        _states[index] = CardState.back;
      } else if (current == CardState.back) {
        _states[index] = CardState.quotes;
      } else if (current == CardState.quotes) {
        _states[index] = CardState.front;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final total = widget.articles.length;
    return SizedBox(
      width: 600,
      child: Stack(
        alignment: Alignment.topCenter,
        children: List.generate(total, (i) {
          final depth = total - 1 - i;
          final state = _states[i];
          final isStacked = state == CardState.stacked;
          final top = isStacked ? depth * -30.0 : depth * 10.0;
          final scale = isStacked ? 1 - depth * 0.03 : 1.0;
          return Positioned(
            top: top,
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
    );
  }
}
