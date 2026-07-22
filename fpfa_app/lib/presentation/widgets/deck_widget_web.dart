// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use

import 'dart:async';
import 'dart:html' as html;
import 'dart:ui_web' as ui_web;

import 'package:flutter/material.dart';

import '../../domain/entities/article.dart';

enum ArticleSection { thesis, summary, evidence }

class Deck extends StatefulWidget {
  const Deck({super.key, required this.articles});

  final List<Article> articles;

  @override
  State<Deck> createState() => DeckState();
}

class DeckState extends State<Deck> {
  static int _nextViewId = 0;
  static bool _stylesInjected = false;

  late final String _viewType;
  late final html.DivElement _host;
  final List<StreamSubscription<html.Event>> _subscriptions = [];

  int _activeIndex = 0;
  ArticleSection _section = ArticleSection.thesis;

  @override
  void initState() {
    super.initState();
    _injectStyles();
    _viewType = 'fpfa-reader-${_nextViewId++}';
    _host = html.DivElement()
      ..className = 'fpfa-reader-host'
      ..tabIndex = 0
      ..setAttribute('role', 'region')
      ..setAttribute(
        'aria-label',
        'Article reader. Newest article first. Use left and right arrows to navigate.',
      )
      ..setAttribute('data-testid', 'article-reader');
    _host.style
      ..width = '100%'
      ..height = '100%';

    ui_web.platformViewRegistry.registerViewFactory(_viewType, (_) => _host);
    _render();
  }

  @override
  void didUpdateWidget(covariant Deck oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.articles != widget.articles) {
      _activeIndex = 0;
      _section = ArticleSection.thesis;
      _render();
    }
  }

  @override
  void dispose() {
    _cancelSubscriptions();
    _host.remove();
    super.dispose();
  }

  void reset() {
    _activeIndex = 0;
    _section = ArticleSection.thesis;
    _render();
  }

  void _cancelSubscriptions() {
    for (final subscription in _subscriptions) {
      subscription.cancel();
    }
    _subscriptions.clear();
  }

  void _listen(html.Element element, void Function() callback) {
    _subscriptions.add(
      element.onClick.listen((event) {
        event.stopPropagation();
        callback();
      }),
    );
  }

  void _selectArticle(int index, {String? focusTestId}) {
    if (index < 0 || index >= widget.articles.length) return;
    _activeIndex = index;
    _section = ArticleSection.thesis;
    _render();
    _focusTestId(focusTestId);
  }

  void _selectSection(ArticleSection section) {
    _section = section;
    _render();
    _focusTestId('section-${section.name}');
  }

  void _focusTestId(String? testId) {
    if (testId == null) return;
    final target = _host.querySelector('[data-testid="$testId"]');
    if (target is html.HtmlElement) target.focus();
  }

  void _render() {
    _cancelSubscriptions();
    _host.children.clear();
    if (widget.articles.isEmpty) return;

    final active = widget.articles[_activeIndex];
    final shell = html.DivElement()..className = 'fpfa-reader-shell';
    shell
      ..append(_buildRail())
      ..append(_buildArticle(active));
    _host.append(shell);

    final liveStatus = html.DivElement()
      ..className = 'fpfa-sr-only'
      ..setAttribute('aria-live', 'polite')
      ..text =
          'Article ${_activeIndex + 1} of ${widget.articles.length}: ${active.title}';
    _host.append(liveStatus);

    _subscriptions.add(
      _host.onKeyDown.listen((event) {
        final target = event.target;
        if (target is html.Element && target.getAttribute('role') == 'tab') {
          return;
        }
        if (event.key == 'ArrowLeft' && _activeIndex > 0) {
          event.preventDefault();
          _selectArticle(_activeIndex - 1);
        } else if (event.key == 'ArrowRight' &&
            _activeIndex < widget.articles.length - 1) {
          event.preventDefault();
          _selectArticle(_activeIndex + 1);
        }
      }),
    );
  }

  html.Element _buildRail() {
    final rail = html.Element.tag('nav')
      ..className = 'fpfa-article-rail'
      ..setAttribute('aria-label', 'Article chronology');
    final heading = html.HeadingElement.h2()
      ..className = 'fpfa-rail-heading'
      ..text = 'Newest first';
    final list = html.DivElement()..className = 'fpfa-rail-list';

    for (int index = 0; index < widget.articles.length; index += 1) {
      final article = widget.articles[index];
      final selected = index == _activeIndex;
      final button = html.ButtonElement()
        ..type = 'button'
        ..className = 'fpfa-preview ${selected ? 'is-active' : ''}'
        ..setAttribute('aria-current', selected ? 'true' : 'false')
        ..setAttribute(
          'aria-label',
          '${index == 0 ? 'Latest article' : 'Article ${index + 1}'}. ${article.title}',
        )
        ..setAttribute('data-testid', 'article-preview-$index');
      button.style.setProperty('--stack-offset', '${(index % 4) * 3}px');

      final mark = html.SpanElement()
        ..className = 'fpfa-source-mark ${_sourceClass(article.source)}'
        ..setAttribute('aria-hidden', 'true')
        ..text = article.source == 'Foreign Policy' ? 'FP' : 'FA';
      final copy = html.SpanElement()..className = 'fpfa-preview-copy';
      copy
        ..append(
          html.SpanElement()
            ..className = 'fpfa-preview-order'
            ..text = index == 0
                ? 'LATEST'
                : '${index + 1} OF ${widget.articles.length}',
        )
        ..append(
          html.SpanElement()
            ..className = 'fpfa-preview-title'
            ..text = article.title,
        );
      button
        ..append(mark)
        ..append(copy);
      _listen(
        button,
        () => _selectArticle(index, focusTestId: 'article-preview-$index'),
      );
      list.append(button);
    }

    rail
      ..append(heading)
      ..append(list);
    return rail;
  }

  html.Element _buildArticle(Article article) {
    final card = html.Element.tag('article')
      ..className = 'fpfa-active-card'
      ..setAttribute('aria-labelledby', '$_viewType-title');

    final header = html.Element.tag('header')
      ..className = 'fpfa-card-header ${_sourceClass(article.source)}';
    final eyebrow = html.DivElement()..className = 'fpfa-eyebrow';
    final source = html.SpanElement()
      ..className = 'fpfa-source-name'
      ..text = article.source;
    final date = html.Element.tag('time')
      ..className = 'fpfa-date'
      ..text = article.shortDate;
    eyebrow
      ..append(source)
      ..append(date);

    final title = html.HeadingElement.h1()
      ..id = '$_viewType-title'
      ..className = 'fpfa-active-title'
      ..setAttribute('data-testid', 'active-title')
      ..text = article.title;
    final author = html.ParagraphElement()
      ..className = 'fpfa-author'
      ..text = article.author;
    header
      ..append(eyebrow)
      ..append(title)
      ..append(author);

    final tabs = html.DivElement()
      ..className = 'fpfa-section-tabs'
      ..setAttribute('role', 'tablist')
      ..setAttribute('aria-label', 'Summary sections');
    for (final section in ArticleSection.values) {
      final selected = section == _section;
      final tab = html.ButtonElement()
        ..id = '$_viewType-tab-${section.name}'
        ..type = 'button'
        ..className = 'fpfa-section-tab ${selected ? 'is-active' : ''}'
        ..setAttribute('role', 'tab')
        ..setAttribute('aria-selected', '$selected')
        ..setAttribute('aria-controls', '$_viewType-panel')
        ..setAttribute('tabindex', selected ? '0' : '-1')
        ..setAttribute('data-testid', 'section-${section.name}')
        ..text = _sectionLabel(section);
      _listen(tab, () => _selectSection(section));
      _subscriptions.add(
        tab.onKeyDown.listen((event) {
          const sections = ArticleSection.values;
          final current = sections.indexOf(section);
          final next = switch (event.key) {
            'ArrowLeft' => (current - 1 + sections.length) % sections.length,
            'ArrowRight' => (current + 1) % sections.length,
            'Home' => 0,
            'End' => sections.length - 1,
            _ => null,
          };
          if (next == null) return;
          event
            ..preventDefault()
            ..stopPropagation();
          _selectSection(sections[next]);
        }),
      );
      tabs.append(tab);
    }

    final scroll = html.DivElement()..className = 'fpfa-card-scroll';
    final panel = html.Element.tag('section')
      ..id = '$_viewType-panel'
      ..className = 'fpfa-section-panel'
      ..setAttribute('role', 'tabpanel')
      ..setAttribute('tabindex', '0')
      ..setAttribute('aria-labelledby', '$_viewType-tab-${_section.name}')
      ..setAttribute('data-testid', 'section-content');
    _appendSectionContent(panel, article);
    scroll.append(panel);

    final footer = html.Element.tag('footer')..className = 'fpfa-card-footer';
    final navigation = html.DivElement()
      ..className = 'fpfa-article-navigation'
      ..setAttribute('aria-label', 'Article navigation');
    final newer = html.ButtonElement()
      ..type = 'button'
      ..className = 'fpfa-nav-button'
      ..disabled = _activeIndex == 0
      ..setAttribute('data-testid', 'newer-button')
      ..text = '← Newer';
    final counter = html.SpanElement()
      ..className = 'fpfa-counter'
      ..setAttribute('data-testid', 'article-counter')
      ..text =
          '${_activeIndex + 1} of ${widget.articles.length} · newest first';
    final older = html.ButtonElement()
      ..type = 'button'
      ..className = 'fpfa-nav-button'
      ..disabled = _activeIndex == widget.articles.length - 1
      ..setAttribute('data-testid', 'older-button')
      ..text = 'Older →';
    _listen(
      newer,
      () => _selectArticle(_activeIndex - 1, focusTestId: 'newer-button'),
    );
    _listen(
      older,
      () => _selectArticle(_activeIndex + 1, focusTestId: 'older-button'),
    );
    navigation
      ..append(newer)
      ..append(counter)
      ..append(older);

    final sourceLink = html.AnchorElement(href: article.url)
      ..className = 'fpfa-source-link'
      ..target = '_blank'
      ..rel = 'noopener noreferrer'
      ..setAttribute('data-testid', 'source-link')
      ..setAttribute(
        'aria-label',
        'Read the original article on ${_sourceHost(article.url)}',
      )
      ..text = 'Read on ${_sourceHost(article.url)} ↗';
    footer
      ..append(navigation)
      ..append(sourceLink);

    card
      ..append(header)
      ..append(tabs)
      ..append(scroll)
      ..append(footer);
    return card;
  }

  void _appendSectionContent(html.Element panel, Article article) {
    if (_section == ArticleSection.evidence) {
      if (article.quotes.isEmpty) {
        panel.append(
          html.ParagraphElement()
            ..text = 'No supporting evidence was included in this summary.',
        );
        return;
      }
      final list = html.DivElement()..className = 'fpfa-evidence-list';
      for (final quote in article.quotes.take(8)) {
        list.append(
          html.Element.tag('blockquote')
            ..className = 'fpfa-evidence-item'
            ..text = quote,
        );
      }
      panel.append(list);
      return;
    }

    panel.append(
      html.ParagraphElement()
        ..className = 'fpfa-summary-copy'
        ..text = _section == ArticleSection.thesis
            ? article.coreThesis
            : article.detailedAbstract,
    );
  }

  static String _sectionLabel(ArticleSection section) => switch (section) {
    ArticleSection.thesis => 'Thesis',
    ArticleSection.summary => 'Summary',
    ArticleSection.evidence => 'Evidence',
  };

  static String _sourceClass(String source) =>
      source == 'Foreign Policy' ? 'is-fp' : 'is-fa';

  static String _sourceHost(String value) {
    final host = Uri.tryParse(value)?.host.replaceFirst('www.', '');
    return host == null || host.isEmpty ? 'source site' : host;
  }

  static void _injectStyles() {
    if (_stylesInjected) return;
    _stylesInjected = true;
    html.document.head?.append(
      html.StyleElement()
        ..text = '''
.fpfa-reader-host {
  --ink: #17212b;
  --muted: #52606d;
  --primary: #174a6e;
  --focus: #0b6eaa;
  --canvas: #f4f1ea;
  --surface: #ffffff;
  --line: #d7dce0;
  --fp: #ffe3de;
  --fa: #ddeff8;
  box-sizing: border-box;
  display: block;
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.5;
  outline: none;
}

.fpfa-reader-host *, .fpfa-reader-host *::before, .fpfa-reader-host *::after {
  box-sizing: border-box;
}

.fpfa-reader-shell {
  width: min(100%, 1120px);
  height: 100%;
  min-height: 0;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
  gap: 20px;
}

.fpfa-article-rail,
.fpfa-active-card {
  min-width: 0;
  min-height: 0;
}

.fpfa-article-rail {
  display: flex;
  flex-direction: column;
}

.fpfa-rail-heading {
  margin: 4px 8px 8px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.3;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.fpfa-rail-list {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 4px 8px 12px 4px;
  scrollbar-gutter: stable;
}

.fpfa-preview {
  width: calc(100% - var(--stack-offset));
  min-height: 72px;
  margin: 0 0 8px var(--stack-offset);
  padding: 10px 12px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  text-align: left;
  color: var(--ink);
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: 0 3px 10px rgba(23, 33, 43, .06);
  cursor: pointer;
  transition: transform 160ms ease, border-color 160ms ease, background-color 160ms ease;
}

.fpfa-preview:hover { transform: translateY(-1px); border-color: #8ca4b5; }
.fpfa-preview.is-active { background: #e7f0f6; border: 2px solid var(--primary); }

.fpfa-source-mark {
  flex: 0 0 32px;
  width: 32px;
  height: 32px;
  display: inline-grid;
  place-items: center;
  border-radius: 8px;
  color: white;
  font-size: 11px;
  font-weight: 800;
}
.fpfa-source-mark.is-fp { background: #8f2d22; }
.fpfa-source-mark.is-fa { background: #175a7a; }

.fpfa-preview-copy { min-width: 0; display: grid; gap: 3px; }
.fpfa-preview-order { color: var(--muted); font-size: 10px; font-weight: 700; letter-spacing: .05em; }
.fpfa-preview-title {
  display: -webkit-box;
  overflow: hidden;
  font-size: 13px;
  font-weight: 650;
  line-height: 1.25;
  overflow-wrap: anywhere;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.fpfa-active-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(23, 33, 43, .10);
}

.fpfa-card-header { padding: 18px 22px 16px; border-bottom: 1px solid var(--line); }
.fpfa-card-header.is-fp { background: var(--fp); }
.fpfa-card-header.is-fa { background: var(--fa); }
.fpfa-eyebrow { display: flex; justify-content: space-between; gap: 16px; color: #32404d; font-size: 12px; font-weight: 700; }
.fpfa-source-name { text-transform: uppercase; letter-spacing: .05em; }
.fpfa-date { white-space: nowrap; }
.fpfa-active-title {
  margin: 10px 0 5px;
  max-width: 780px;
  color: var(--ink);
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(22px, 3vw, 32px);
  font-weight: 700;
  letter-spacing: -.02em;
  line-height: 1.16;
  overflow-wrap: anywhere;
}
.fpfa-author { margin: 0; color: var(--muted); font-size: 14px; }

.fpfa-section-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 12px 16px 8px;
}
.fpfa-section-tab,
.fpfa-nav-button {
  min-height: 44px;
  padding: 9px 12px;
  color: var(--ink);
  background: transparent;
  border: 1px solid var(--line);
  border-radius: 10px;
  font: inherit;
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
}
.fpfa-section-tab.is-active { color: var(--primary); background: #e7f0f6; border-color: var(--primary); }
.fpfa-nav-button:disabled { opacity: .42; cursor: not-allowed; }

.fpfa-card-scroll { flex: 1; min-height: 0; overflow: auto; }
.fpfa-section-panel { max-width: 800px; padding: 14px 22px 24px; outline: none; }
.fpfa-summary-copy { margin: 0; font-family: Georgia, "Times New Roman", serif; font-size: 17px; line-height: 1.62; white-space: pre-line; }
.fpfa-evidence-list { display: grid; gap: 12px; }
.fpfa-evidence-item {
  margin: 0;
  padding: 14px 16px;
  color: #34414d;
  background: #f5f7f8;
  border: 1px solid var(--line);
  border-left: 4px solid #8ca4b5;
  border-radius: 10px;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 16px;
  font-style: italic;
  line-height: 1.55;
}

.fpfa-card-footer { padding: 8px 12px 12px; border-top: 1px solid var(--line); }
.fpfa-article-navigation { display: grid; grid-template-columns: auto minmax(110px, 1fr) auto; align-items: center; gap: 8px; }
.fpfa-counter { color: var(--muted); font-size: 12px; font-weight: 650; text-align: center; }
.fpfa-source-link {
  min-height: 44px;
  margin-top: 8px;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  background: var(--primary);
  border-radius: 10px;
  font-size: 14px;
  font-weight: 700;
  text-align: center;
  text-decoration: none;
}
.fpfa-source-link:hover { background: #0f3b59; }

.fpfa-reader-host button:focus-visible,
.fpfa-reader-host a:focus-visible,
.fpfa-reader-host [tabindex]:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}

.fpfa-sr-only {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  padding: 0 !important;
  margin: -1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  white-space: nowrap !important;
  border: 0 !important;
}

@media (max-width: 759px) {
  .fpfa-reader-shell { grid-template-columns: minmax(0, 1fr); grid-template-rows: 104px minmax(0, 1fr); gap: 8px; }
  .fpfa-rail-heading { margin: 0 4px 5px; }
  .fpfa-rail-list { display: flex; gap: 8px; padding: 2px 4px 8px; overflow-x: auto; overflow-y: hidden; }
  .fpfa-preview { flex: 0 0 208px; width: 208px; min-height: 72px; margin: 0; }
  .fpfa-active-card { border-radius: 16px; }
  .fpfa-card-header { padding: 14px 16px 12px; }
  .fpfa-active-title { font-size: clamp(20px, 6.2vw, 27px); }
  .fpfa-section-tabs { padding: 8px 8px 4px; gap: 4px; }
  .fpfa-section-tab { padding-inline: 6px; font-size: 13px; }
  .fpfa-section-panel { padding: 12px 16px 20px; }
  .fpfa-summary-copy { font-size: 16px; line-height: 1.56; }
  .fpfa-card-footer { padding: 6px 8px 8px; }
  .fpfa-article-navigation { grid-template-columns: auto 1fr auto; gap: 4px; }
  .fpfa-nav-button { padding-inline: 9px; font-size: 13px; }
  .fpfa-counter { font-size: 11px; }
  .fpfa-source-link { margin-top: 6px; }
}

@media (max-width: 359px) {
  .fpfa-card-header { padding-inline: 12px; }
  .fpfa-section-tab { font-size: 12px; }
  .fpfa-counter { max-width: 82px; }
}

@media (prefers-reduced-motion: reduce) {
  .fpfa-preview { transition: none; }
}

@media (forced-colors: active) {
  .fpfa-preview.is-active,
  .fpfa-section-tab.is-active { border-width: 3px; }
}
''',
    );
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Article reader',
      child: SizedBox.expand(child: HtmlElementView(viewType: _viewType)),
    );
  }
}
