// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use

import 'dart:async';
import 'dart:html' as html;
import 'dart:ui_web' as ui_web;

import 'package:flutter/material.dart';

import '../../domain/entities/article.dart';

enum CardState { stacked, front, back, quotes }

class Deck extends StatefulWidget {
  final List<Article> articles;
  const Deck({super.key, required this.articles});

  @override
  State<Deck> createState() => DeckState();
}

class DeckState extends State<Deck> {
  static int _nextViewId = 0;
  static bool _stylesInjected = false;

  late final String _viewType;
  late final html.DivElement _host;
  late final html.DivElement _scene;
  late List<CardState> _states;
  final List<_DeckDomCard> _cards = [];

  StreamSubscription<html.Event>? _resizeSub;

  int _activeIndex = 0;
  num? _dragStartY;

  @override
  void initState() {
    super.initState();
    _activeIndex = widget.articles.isEmpty ? 0 : widget.articles.length - 1;
    _states = _buildStates(activeIndex: _activeIndex);
    _injectStyles();

    _viewType = 'fpfa-rolodex-web-${_nextViewId++}';
    _host = html.DivElement()..className = 'fpfa-rolodex-host';
    _scene = html.DivElement()..className = 'fpfa-rolodex-scene';
    _host.append(_scene);

    ui_web.platformViewRegistry.registerViewFactory(_viewType, (viewId) {
      return _host;
    });

    _buildCards();
    _resizeSub = html.window.onResize.listen((_) => _applyLayout());
  }

  @override
  void didUpdateWidget(covariant Deck oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.articles != widget.articles) {
      _activeIndex = widget.articles.isEmpty ? 0 : widget.articles.length - 1;
      _states = _buildStates(activeIndex: _activeIndex);
      _buildCards();
    }
  }

  @override
  void dispose() {
    _resizeSub?.cancel();
    super.dispose();
  }

  List<CardState> _buildStates({
    required int activeIndex,
    CardState activeState = CardState.front,
  }) {
    return List.generate(
      widget.articles.length,
      (i) => i == activeIndex ? activeState : CardState.stacked,
    );
  }

  void reset() {
    if (widget.articles.isEmpty) {
      return;
    }
    _activeIndex = widget.articles.length - 1;
    _states = _buildStates(activeIndex: _activeIndex);
    _applyLayout();
  }

  void _shiftActiveIndex(int delta) {
    if (widget.articles.isEmpty) {
      return;
    }
    final nextIndex =
        (_activeIndex + delta).clamp(0, widget.articles.length - 1);
    if (nextIndex == _activeIndex) {
      return;
    }

    _activeIndex = nextIndex;
    _states = _buildStates(activeIndex: _activeIndex);
    _applyLayout();
  }

  void _onCardTap(int index) {
    if (widget.articles.isEmpty) {
      return;
    }

    final current = _states[index];
    if (current == CardState.stacked) {
      _activeIndex = index;
      _states = _buildStates(activeIndex: index);
    } else if (current == CardState.front) {
      _states[index] = CardState.back;
    } else if (current == CardState.back) {
      _states[index] = CardState.quotes;
    } else {
      _states[index] = CardState.front;
    }

    _applyLayout();
  }

  List<int> _buildBehindIndices(int limit) {
    final behind = <int>[];
    for (int offset = 1; offset < widget.articles.length; offset += 1) {
      behind.add((_activeIndex + offset) % widget.articles.length);
    }
    if (behind.length <= limit) {
      return behind;
    }
    return behind.sublist(0, limit);
  }

  void _buildCards() {
    _cards.clear();
    _scene.children.clear();
    _scene.onWheel.listen((event) {
      event.preventDefault();
      if (event.deltaY > 8) {
        _shiftActiveIndex(1);
      } else if (event.deltaY < -8) {
        _shiftActiveIndex(-1);
      }
    });
    _scene.onMouseDown.listen((event) {
      _dragStartY = event.client.y;
    });
    _scene.onMouseUp.listen((event) {
      if (_dragStartY == null) {
        return;
      }
      final endY = event.client.y;
      final delta = endY - _dragStartY!;
      _dragStartY = null;
      if (delta > 40) {
        _shiftActiveIndex(1);
      } else if (delta < -40) {
        _shiftActiveIndex(-1);
      }
    });

    for (int i = 0; i < widget.articles.length; i += 1) {
      final card = _DeckDomCard.fromArticle(
        index: i,
        article: widget.articles[i],
        onTap: () => _onCardTap(i),
      );
      _cards.add(card);
      _scene.append(card.root);
    }

    _applyLayout();
  }

  void _applyLayout() {
    if (widget.articles.isEmpty) {
      return;
    }

    final viewportWidth = html.window.innerWidth ?? 1280;
    final isMobile = viewportWidth < 720;
    final visibleBehind = _buildBehindIndices(isMobile ? 7 : 9);
    final ordered = <int>[
      ...visibleBehind.reversed,
      _activeIndex,
    ];
    final positionByIndex = <int, int>{
      for (int i = 0; i < ordered.length; i += 1) ordered[i]: i,
    };

    final activeState = _states[_activeIndex];
    final activeHeight = activeState == CardState.back
        ? (isMobile ? 500 : 580)
        : activeState == CardState.quotes
            ? (isMobile ? 430 : 500)
            : (isMobile ? 330 : 390);
    final activeTop = isMobile ? 230 : 280;
    final sceneHeight = activeTop + activeHeight + (isMobile ? 90 : 120);

    _scene.style.height = '${sceneHeight}px';
    _scene.classes.toggle('is-mobile', isMobile);

    for (final card in _cards) {
      final position = positionByIndex[card.index];
      if (position == null) {
        card.root.style.opacity = '0';
        card.root.style.pointerEvents = 'none';
        card.root.style.transform =
            'translate3d(0, ${sceneHeight + 120}px, -400px) scale(0.75)';
        continue;
      }

      final isActive = card.index == _activeIndex;
      final depth = (ordered.length - 1 - position).toDouble();
      final inset = isActive ? 0.0 : depth * (isMobile ? 12 : 16);
      final top = isActive
          ? activeTop.toDouble()
          : activeTop -
              (depth * (isMobile ? 34 : 40)) -
              (depth * depth * (isMobile ? 4.5 : 7.5));
      final z = isActive ? 200.0 : -depth * (isMobile ? 60 : 88);
      final tilt = isActive ? 0.0 : -14.0 - depth * 2.6;
      final scale = isActive ? 1.0 : 1 - depth * (isMobile ? 0.045 : 0.04);
      final cardHeight = isActive ? activeHeight : (isMobile ? 58 : 66);

      card.root.classes
        ..toggle('is-active', isActive)
        ..toggle('is-stacked', !isActive)
        ..toggle('is-expanded', isActive && activeState == CardState.back)
        ..toggle('is-quotes', isActive && activeState == CardState.quotes);

      card.abstractBlock.classes
          .toggle('is-visible', isActive && activeState == CardState.back);

      card.root.style
        ..opacity = '1'
        ..pointerEvents = 'auto'
        ..zIndex = '${1000 - depth.round()}'
        ..left = '${inset}px'
        ..width = 'calc(100% - ${inset * 2}px)'
        ..height = '${cardHeight}px'
        ..transform =
            'translate3d(0, ${top}px, ${z}px) rotateX(${tilt}deg) scale($scale)';
    }
  }

  static void _injectStyles() {
    if (_stylesInjected) {
      return;
    }
    _stylesInjected = true;

    final style = html.StyleElement()
      ..text = '''
.fpfa-rolodex-host {
  width: 100%;
  height: 100%;
  display: block;
}

.fpfa-rolodex-scene {
  position: relative;
  width: min(88vw, 920px);
  height: 860px;
  margin: 0 auto;
  perspective: 2200px;
  transform-style: preserve-3d;
  transform: rotateX(8deg);
  user-select: none;
  touch-action: pan-y;
}

.fpfa-rolodex-card {
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: top center;
  transform-style: preserve-3d;
  transition:
    transform 560ms cubic-bezier(0.22, 1, 0.36, 1),
    width 560ms cubic-bezier(0.22, 1, 0.36, 1),
    height 460ms cubic-bezier(0.22, 1, 0.36, 1),
    opacity 220ms ease,
    filter 320ms ease;
  filter: drop-shadow(0 16px 30px rgba(20, 26, 38, 0.16));
  cursor: pointer;
}

.fpfa-rolodex-card.is-active {
  filter: drop-shadow(0 28px 42px rgba(20, 26, 38, 0.2));
}

.fpfa-rolodex-card-inner {
  position: relative;
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
  transition: transform 720ms cubic-bezier(0.22, 1, 0.36, 1);
}

.fpfa-rolodex-card.is-quotes .fpfa-rolodex-card-inner {
  transform: rotateY(180deg);
}

.fpfa-rolodex-face {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 22px;
  border: 1px solid #dddddd;
  backface-visibility: hidden;
  overflow: hidden;
}

.fpfa-rolodex-back {
  transform: rotateY(180deg);
}

.fpfa-rolodex-card.is-stacked .fpfa-rolodex-body {
  opacity: 0;
  transform: translateY(-20px);
}

.fpfa-rolodex-card.is-stacked .fpfa-rolodex-header {
  padding-bottom: 10px;
}

.fpfa-rolodex-card.is-stacked .fpfa-rolodex-title {
  font-size: 18px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fpfa-rolodex-card.is-stacked .fpfa-rolodex-meta {
  opacity: 0.68;
}

.fpfa-rolodex-header {
  padding: 14px 16px 12px;
  border-bottom: 1px solid #dddddd;
}

.fpfa-rolodex-header.fp {
  background: linear-gradient(180deg, #ffd8d8 0%, #ffcaca 100%);
}

.fpfa-rolodex-header.fa {
  background: linear-gradient(180deg, #daf2ff 0%, #ccecff 100%);
}

.fpfa-rolodex-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.fpfa-rolodex-title {
  margin: 0;
  color: #171717;
  font: 700 20px/1.08 Georgia, "Times New Roman", serif;
}

.fpfa-rolodex-date {
  flex: 0 0 auto;
  color: #7b7b7b;
  font: 12px/1.2 Arial, sans-serif;
}

.fpfa-rolodex-meta {
  margin-top: 6px;
  color: #595959;
  font: 13px/1.3 Arial, sans-serif;
}

.fpfa-rolodex-body {
  flex: 1;
  padding: 16px 18px 18px;
  overflow: auto;
  color: #1c1c1c;
  transition:
    opacity 260ms ease,
    transform 460ms cubic-bezier(0.22, 1, 0.36, 1);
}

.fpfa-rolodex-thesis {
  font: 400 17px/1.52 Georgia, "Times New Roman", serif;
}

.fpfa-rolodex-abstract {
  max-height: 0;
  opacity: 0;
  overflow: hidden;
  transform: translateY(-12px);
  transition:
    max-height 520ms cubic-bezier(0.22, 1, 0.36, 1),
    opacity 280ms ease,
    transform 520ms cubic-bezier(0.22, 1, 0.36, 1),
    margin-top 520ms cubic-bezier(0.22, 1, 0.36, 1),
    padding-top 520ms cubic-bezier(0.22, 1, 0.36, 1);
}

.fpfa-rolodex-abstract.is-visible {
  max-height: 420px;
  opacity: 1;
  transform: translateY(0);
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #dddddd;
}

.fpfa-rolodex-abstract p {
  margin: 0;
  color: #525252;
  font: 15px/1.56 Arial, sans-serif;
}

.fpfa-rolodex-quotes {
  display: grid;
  gap: 10px;
}

.fpfa-rolodex-quote {
  padding: 12px 14px;
  border: 1px solid #dddddd;
  border-radius: 12px;
  background: #f8f9fa;
  color: #535353;
  font: italic 15px/1.5 Georgia, "Times New Roman", serif;
}

@media (max-width: 720px) {
  .fpfa-rolodex-scene {
    width: min(94vw, 430px);
    height: 720px;
    transform: rotateX(6deg);
  }

  .fpfa-rolodex-face {
    border-radius: 18px;
  }

  .fpfa-rolodex-card.is-stacked .fpfa-rolodex-title {
    font-size: 15px;
  }

  .fpfa-rolodex-title {
    font-size: 16px;
  }

  .fpfa-rolodex-meta {
    font-size: 12px;
  }

  .fpfa-rolodex-thesis {
    font-size: 16px;
    line-height: 1.48;
  }
}

@media (prefers-reduced-motion: reduce) {
  .fpfa-rolodex-card,
  .fpfa-rolodex-card-inner,
  .fpfa-rolodex-body,
  .fpfa-rolodex-abstract {
    transition-duration: 0.01ms !important;
  }
}
''';

    html.document.head?.append(style);
  }

  @override
  Widget build(BuildContext context) {
    final isMobile = MediaQuery.of(context).size.width < 720;
    return SizedBox(
      width: isMobile ? MediaQuery.of(context).size.width - 20 : 920,
      height: isMobile ? 720 : 860,
      child: HtmlElementView(viewType: _viewType),
    );
  }
}

class _DeckDomCard {
  final int index;
  final html.DivElement root;
  final html.DivElement abstractBlock;

  _DeckDomCard({
    required this.index,
    required this.root,
    required this.abstractBlock,
  });

  factory _DeckDomCard.fromArticle({
    required int index,
    required Article article,
    required VoidCallback onTap,
  }) {
    final root = html.DivElement()..className = 'fpfa-rolodex-card';
    final inner = html.DivElement()..className = 'fpfa-rolodex-card-inner';

    final front = html.DivElement()..className = 'fpfa-rolodex-face';
    final back = html.DivElement()
      ..className = 'fpfa-rolodex-face fpfa-rolodex-back';

    final frontHeader = _buildHeader(article);
    final backHeader = _buildHeader(article);

    final frontBody = html.DivElement()..className = 'fpfa-rolodex-body';
    final thesis = html.DivElement()
      ..className = 'fpfa-rolodex-thesis'
      ..text = article.coreThesis;
    final abstractBlock = html.DivElement()
      ..className = 'fpfa-rolodex-abstract';
    abstractBlock.append(
      html.ParagraphElement()..text = article.detailedAbstract,
    );
    frontBody
      ..append(thesis)
      ..append(abstractBlock);

    final backBody = html.DivElement()
      ..className = 'fpfa-rolodex-body fpfa-rolodex-quotes';
    final quotes = article.quotes.isEmpty
        ? ['No supporting quotations were available for this article.']
        : article.quotes.take(5);
    for (final quote in quotes) {
      backBody.append(
        html.DivElement()
          ..className = 'fpfa-rolodex-quote'
          ..text = quote,
      );
    }

    front
      ..append(frontHeader)
      ..append(frontBody);
    back
      ..append(backHeader)
      ..append(backBody);

    inner
      ..append(front)
      ..append(back);
    root.append(inner);
    root.onClick.listen((_) => onTap());

    return _DeckDomCard(
      index: index,
      root: root,
      abstractBlock: abstractBlock,
    );
  }

  static html.DivElement _buildHeader(Article article) {
    final header = html.DivElement()
      ..className =
          'fpfa-rolodex-header ${article.source == 'Foreign Policy' ? 'fp' : 'fa'}';
    final row = html.DivElement()..className = 'fpfa-rolodex-header-row';
    final title = html.HeadingElement.h3()
      ..className = 'fpfa-rolodex-title'
      ..text = article.title;
    final date = html.DivElement()
      ..className = 'fpfa-rolodex-date'
      ..text = article.shortDate;
    row
      ..append(title)
      ..append(date);

    final meta = html.DivElement()
      ..className = 'fpfa-rolodex-meta'
      ..text = '${article.source} — ${article.author}';

    header
      ..append(row)
      ..append(meta);
    return header;
  }
}
