import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme.dart';
import '../../domain/entities/article.dart';

enum ArticleSection { thesis, summary, evidence }

class Deck extends StatefulWidget {
  const Deck({super.key, required this.articles});

  final List<Article> articles;

  @override
  State<Deck> createState() => DeckState();
}

class DeckState extends State<Deck> {
  int _activeIndex = 0;
  ArticleSection _section = ArticleSection.thesis;

  @override
  void didUpdateWidget(covariant Deck oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.articles != widget.articles) {
      reset();
    }
  }

  void reset() {
    if (!mounted) return;
    setState(() {
      _activeIndex = 0;
      _section = ArticleSection.thesis;
    });
  }

  void _selectArticle(int index) {
    if (index < 0 || index >= widget.articles.length || index == _activeIndex) {
      return;
    }
    setState(() {
      _activeIndex = index;
      _section = ArticleSection.thesis;
    });
  }

  void _selectSection(ArticleSection section) {
    if (section == _section) return;
    setState(() => _section = section);
  }

  Future<void> _openSource() async {
    final uri = Uri.tryParse(widget.articles[_activeIndex].url);
    var opened = false;
    try {
      opened =
          uri != null &&
          (uri.scheme == 'https' || uri.scheme == 'http') &&
          await launchUrl(uri, mode: LaunchMode.externalApplication);
    } on Object {
      opened = false;
    }
    if (!opened && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('The original article could not be opened.'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.articles.isEmpty) return const SizedBox.shrink();

    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 760;
        final rail = _ArticleRail(
          articles: widget.articles,
          activeIndex: _activeIndex,
          horizontal: compact,
          onSelected: _selectArticle,
        );
        final reader = _ArticleReader(
          article: widget.articles[_activeIndex],
          activeIndex: _activeIndex,
          total: widget.articles.length,
          section: _section,
          onSectionSelected: _selectSection,
          onNewer: _activeIndex > 0
              ? () => _selectArticle(_activeIndex - 1)
              : null,
          onOlder: _activeIndex < widget.articles.length - 1
              ? () => _selectArticle(_activeIndex + 1)
              : null,
          onOpenSource: _openSource,
        );

        return CallbackShortcuts(
          bindings: {
            const SingleActivator(LogicalKeyboardKey.arrowLeft): () {
              if (_activeIndex > 0) _selectArticle(_activeIndex - 1);
            },
            const SingleActivator(LogicalKeyboardKey.arrowRight): () {
              if (_activeIndex < widget.articles.length - 1) {
                _selectArticle(_activeIndex + 1);
              }
            },
          },
          child: Focus(
            autofocus: true,
            child: Semantics(
              container: true,
              label:
                  'Article reader. Newest article first. Use left and right arrows to navigate.',
              child: compact
                  ? Column(
                      children: [
                        SizedBox(height: 104, child: rail),
                        const SizedBox(height: 8),
                        Expanded(child: reader),
                      ],
                    )
                  : Row(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        SizedBox(width: 248, child: rail),
                        const SizedBox(width: 20),
                        Expanded(child: reader),
                      ],
                    ),
            ),
          ),
        );
      },
    );
  }
}

class _ArticleRail extends StatelessWidget {
  const _ArticleRail({
    required this.articles,
    required this.activeIndex,
    required this.horizontal,
    required this.onSelected,
  });

  final List<Article> articles;
  final int activeIndex;
  final bool horizontal;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    final list = ListView.separated(
      scrollDirection: horizontal ? Axis.horizontal : Axis.vertical,
      itemCount: articles.length,
      padding: const EdgeInsets.all(4),
      separatorBuilder: (_, _) =>
          SizedBox(width: horizontal ? 8 : 0, height: horizontal ? 0 : 8),
      itemBuilder: (context, index) {
        final article = articles[index];
        final selected = index == activeIndex;
        return SizedBox(
          width: horizontal ? 208 : null,
          child: Semantics(
            button: true,
            selected: selected,
            label:
                '${index == 0 ? 'Latest article' : 'Article ${index + 1}'}. ${article.title}',
            child: Material(
              color: selected
                  ? const Color(0xFFE7F0F6)
                  : AppTheme.cardBackground,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: BorderSide(
                  color: selected
                      ? AppTheme.primaryBlue
                      : AppTheme.dividerColor,
                  width: selected ? 2 : 1,
                ),
              ),
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: () => onSelected(index),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _SourceMark(source: article.source),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              index == 0
                                  ? 'LATEST'
                                  : '${index + 1} OF ${articles.length}',
                              style: Theme.of(context).textTheme.labelSmall
                                  ?.copyWith(
                                    color: selected
                                        ? AppTheme.primaryBlue
                                        : AppTheme.mutedInk,
                                  ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              article.title,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontSize: 13,
                                height: 1.25,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.ink,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );

    if (horizontal) return list;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(8, 4, 8, 8),
          child: Text(
            'NEWEST FIRST',
            style: Theme.of(context).textTheme.labelSmall,
          ),
        ),
        Expanded(child: list),
      ],
    );
  }
}

class _ArticleReader extends StatelessWidget {
  const _ArticleReader({
    required this.article,
    required this.activeIndex,
    required this.total,
    required this.section,
    required this.onSectionSelected,
    required this.onNewer,
    required this.onOlder,
    required this.onOpenSource,
  });

  final Article article;
  final int activeIndex;
  final int total;
  final ArticleSection section;
  final ValueChanged<ArticleSection> onSectionSelected;
  final VoidCallback? onNewer;
  final VoidCallback? onOlder;
  final VoidCallback onOpenSource;

  @override
  Widget build(BuildContext context) {
    final sourceColor = article.source == 'Foreign Policy'
        ? AppTheme.fpTitleBackground
        : AppTheme.faTitleBackground;
    return Card(
      margin: EdgeInsets.zero,
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          ColoredBox(
            color: sourceColor,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      _SourceMark(source: article.source),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          '${article.source} · ${article.shortDate}',
                          style: Theme.of(
                            context,
                          ).textTheme.labelSmall?.copyWith(color: AppTheme.ink),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    article.title,
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    article.author,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Row(
              children: ArticleSection.values
                  .map(
                    (value) => Expanded(
                      child: Padding(
                        padding: EdgeInsets.only(
                          right: value == ArticleSection.evidence ? 0 : 8,
                        ),
                        child: Semantics(
                          selected: section == value,
                          button: true,
                          child: OutlinedButton(
                            onPressed: () => onSectionSelected(value),
                            style: OutlinedButton.styleFrom(
                              backgroundColor: section == value
                                  ? const Color(0xFFE7F0F6)
                                  : Colors.transparent,
                              foregroundColor: AppTheme.ink,
                              side: BorderSide(
                                color: section == value
                                    ? AppTheme.primaryBlue
                                    : AppTheme.dividerColor,
                              ),
                            ),
                            child: Text(_sectionLabel(value)),
                          ),
                        ),
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
          ),
          Expanded(
            child: Semantics(
              liveRegion: true,
              label: '${_sectionLabel(section)} section',
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(22, 12, 22, 24),
                child: _SectionContent(article: article, section: section),
              ),
            ),
          ),
          const Divider(height: 1),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 10),
            child: Row(
              children: [
                OutlinedButton.icon(
                  onPressed: onNewer,
                  icon: const Icon(Icons.arrow_back, size: 18),
                  label: const Text('Newer'),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '${activeIndex + 1} of $total · newest first',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                ),
                const SizedBox(width: 8),
                OutlinedButton.icon(
                  onPressed: onOlder,
                  iconAlignment: IconAlignment.end,
                  icon: const Icon(Icons.arrow_forward, size: 18),
                  label: const Text('Older'),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
            child: SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: onOpenSource,
                icon: const Icon(Icons.open_in_new, size: 18),
                label: Text('Read on ${_sourceHost(article.url)}'),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionContent extends StatelessWidget {
  const _SectionContent({required this.article, required this.section});

  final Article article;
  final ArticleSection section;

  @override
  Widget build(BuildContext context) {
    if (section == ArticleSection.evidence) {
      if (article.quotes.isEmpty) {
        return Text(
          'No supporting evidence was included in this summary.',
          style: Theme.of(context).textTheme.bodyLarge,
        );
      }
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: article.quotes
            .take(8)
            .map(
              (quote) => Container(
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.quoteBackground,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.dividerColor),
                ),
                child: Text(
                  quote,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyLarge?.copyWith(fontStyle: FontStyle.italic),
                ),
              ),
            )
            .toList(growable: false),
      );
    }

    final text = section == ArticleSection.thesis
        ? article.coreThesis
        : article.detailedAbstract;
    return SelectableText(text, style: Theme.of(context).textTheme.bodyLarge);
  }
}

class _SourceMark extends StatelessWidget {
  const _SourceMark({required this.source});

  final String source;

  @override
  Widget build(BuildContext context) {
    final label = source == 'Foreign Policy' ? 'FP' : 'FA';
    final color = source == 'Foreign Policy'
        ? const Color(0xFF8F2D22)
        : const Color(0xFF175A7A);
    return ExcludeSemantics(
      child: Container(
        width: 32,
        height: 32,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          label,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 11,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }
}

String _sectionLabel(ArticleSection section) => switch (section) {
  ArticleSection.thesis => 'Thesis',
  ArticleSection.summary => 'Summary',
  ArticleSection.evidence => 'Evidence',
};

String _sourceHost(String value) {
  final host = Uri.tryParse(value)?.host.replaceFirst('www.', '');
  return host == null || host.isEmpty ? 'source site' : host;
}
