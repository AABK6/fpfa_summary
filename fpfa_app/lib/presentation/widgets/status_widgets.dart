import 'package:flutter/material.dart';

class LoadingWidget extends StatelessWidget {
  const LoadingWidget({super.key});

  @override
  Widget build(BuildContext context) {
    return const _StatusPanel(
      semanticLabel: 'Loading the latest summaries',
      icon: CircularProgressIndicator(),
      title: 'Loading the latest summaries',
      message: 'This should only take a moment.',
    );
  }
}

class ErrorDisplayWidget extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const ErrorDisplayWidget({
    super.key,
    required this.message,
    required this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    return _StatusPanel(
      semanticLabel: 'Summaries could not be loaded',
      icon: Icon(
        Icons.cloud_off_outlined,
        color: Theme.of(context).colorScheme.error,
        size: 40,
      ),
      title: 'The summaries are unavailable',
      message: message,
      action: FilledButton.icon(
        onPressed: onRetry,
        icon: const Icon(Icons.refresh),
        label: const Text('Try again'),
      ),
    );
  }
}

class EmptyStateWidget extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;

  const EmptyStateWidget({
    super.key,
    this.message = 'No summaries have been published yet.',
    this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    return _StatusPanel(
      semanticLabel: 'No summaries available',
      icon: const Icon(Icons.article_outlined, size: 40),
      title: 'Nothing to read yet',
      message: message,
      action: onRetry == null
          ? null
          : OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Check again'),
            ),
    );
  }
}

class _StatusPanel extends StatelessWidget {
  const _StatusPanel({
    required this.semanticLabel,
    required this.icon,
    required this.title,
    required this.message,
    this.action,
  });

  final String semanticLabel;
  final Widget icon;
  final String title;
  final String message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      liveRegion: true,
      label: semanticLabel,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(28),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    icon,
                    const SizedBox(height: 20),
                    Text(
                      title,
                      style: Theme.of(context).textTheme.headlineSmall,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      message,
                      style: Theme.of(context).textTheme.bodyMedium,
                      textAlign: TextAlign.center,
                    ),
                    if (action != null) ...[
                      const SizedBox(height: 20),
                      action!,
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
