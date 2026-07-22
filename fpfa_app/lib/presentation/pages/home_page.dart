import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/article_provider.dart';
import '../widgets/deck_widget.dart';
import '../widgets/status_widgets.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) context.read<ArticleProvider>().fetchArticles();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, viewport) {
            // Flutter web can briefly report a 1×1 view while its engine starts.
            // Deferring fixed-size controls avoids transient overflow exceptions.
            if (viewport.maxWidth < 200 || viewport.maxHeight < 200) {
              return const SizedBox.shrink();
            }

            return Column(
              children: [
                const _AppHeader(),
                Expanded(
                  child: Consumer<ArticleProvider>(
                    builder: (context, provider, child) {
                      if (provider.state == ArticleState.loading) {
                        return const LoadingWidget();
                      }
                      if (provider.state == ArticleState.error) {
                        return ErrorDisplayWidget(
                          message: provider.errorMessage,
                          onRetry: provider.fetchArticles,
                        );
                      }
                      if (provider.articles.isEmpty) {
                        return EmptyStateWidget(
                          onRetry: provider.fetchArticles,
                        );
                      }

                      return Column(
                        children: [
                          if (provider.isRefreshing)
                            const LinearProgressIndicator(minHeight: 2),
                          if (provider.isStale)
                            _StaleBanner(
                              cachedAt: provider.cachedAt,
                              onRetry: provider.fetchArticles,
                            ),
                          Expanded(
                            child: LayoutBuilder(
                              builder: (context, constraints) {
                                final horizontalPadding =
                                    constraints.maxWidth < 600 ? 8.0 : 20.0;
                                return Padding(
                                  padding: EdgeInsets.fromLTRB(
                                    horizontalPadding,
                                    8,
                                    horizontalPadding,
                                    16,
                                  ),
                                  child: Deck(articles: provider.articles),
                                );
                              },
                            ),
                          ),
                        ],
                      );
                    },
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _AppHeader extends StatelessWidget {
  const _AppHeader();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: Color(0xFFD7DCE0))),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 10, 8, 10),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Semantics(
                    header: true,
                    child: const Text(
                      'FPFA Brief',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  const SizedBox(height: 2),
                  const Text(
                    'Foreign Policy & Foreign Affairs',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
                  ),
                ],
              ),
            ),
            Consumer<ArticleProvider>(
              builder: (context, provider, _) => IconButton(
                tooltip: provider.isRefreshing
                    ? 'Refreshing summaries'
                    : 'Refresh summaries',
                onPressed: provider.isRefreshing
                    ? null
                    : provider.fetchArticles,
                icon: const Icon(Icons.refresh),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StaleBanner extends StatelessWidget {
  const _StaleBanner({required this.cachedAt, required this.onRetry});

  final DateTime? cachedAt;
  final VoidCallback onRetry;

  String _cachedLabel(BuildContext context) {
    final value = cachedAt?.toLocal();
    if (value == null) return 'Saved copy';
    final date = MaterialLocalizations.of(context).formatShortDate(value);
    final time = MaterialLocalizations.of(
      context,
    ).formatTimeOfDay(TimeOfDay.fromDateTime(value));
    return 'Saved $date at $time';
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      label: 'Offline copy. ${_cachedLabel(context)}.',
      child: ColoredBox(
        color: const Color(0xFFFFF3CD),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              const Icon(
                Icons.cloud_off_outlined,
                size: 20,
                color: Color(0xFF5C4300),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Offline copy · ${_cachedLabel(context)}',
                  style: const TextStyle(
                    color: Color(0xFF5C4300),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              TextButton(onPressed: onRetry, child: const Text('Try again')),
            ],
          ),
        ),
      ),
    );
  }
}
