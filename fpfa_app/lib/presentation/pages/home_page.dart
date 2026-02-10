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
  final GlobalKey<DeckState> _deckKey = GlobalKey<DeckState>();

  @override
  void initState() {
    super.initState();
    context.read<ArticleProvider>().fetchArticles();
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
      body: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTapDown: _handleTapDown,
        child: Consumer<ArticleProvider>(
          builder: (context, provider, child) {
            if (provider.state == ArticleState.loading) {
              return const LoadingWidget();
            } else if (provider.state == ArticleState.error) {
              return ErrorDisplayWidget(
                message: provider.errorMessage,
                onRetry: () => provider.fetchArticles(),
              );
            } else if (provider.articles.isEmpty) {
              return const EmptyStateWidget();
            } else {
              return Center(
                child: Deck(key: _deckKey, articles: provider.articles),
              );
            }
          },
        ),
      ),
    );
  }
}
