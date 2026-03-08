import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'core/theme.dart';
import 'data/datasources/local_article_data_source.dart';
import 'data/datasources/remote_article_data_source.dart';
import 'data/repositories/article_repository_impl.dart';
import 'domain/usecases/get_articles.dart';
import 'presentation/providers/article_provider.dart';
import 'presentation/pages/home_page.dart';

String _resolveApiBaseUrl() {
  const configuredBaseUrl = String.fromEnvironment('API_BASE_URL');
  if (configuredBaseUrl.isNotEmpty) {
    return configuredBaseUrl;
  }

  if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
    return 'http://10.0.2.2:8000';
  }

  return 'http://localhost:8000';
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final sharedPreferences = await SharedPreferences.getInstance();
  
  runApp(
    MultiProvider(
      providers: [
        Provider<http.Client>(create: (_) => http.Client()),
        Provider<SharedPreferences>.value(value: sharedPreferences),
        Provider<ArticleRepositoryImpl>(
          create: (context) {
            final client = context.read<http.Client>();
            final prefs = context.read<SharedPreferences>();
            return ArticleRepositoryImpl(
              remoteDataSource: RemoteArticleDataSourceImpl(
                client: client,
                baseUrl: _resolveApiBaseUrl(),
              ),
              localDataSource: LocalArticleDataSourceImpl(
                sharedPreferences: prefs,
              ),
            );
          },
        ),
        ChangeNotifierProvider<ArticleProvider>(
          create: (context) {
            final repository = context.read<ArticleRepositoryImpl>();
            return ArticleProvider(
              getArticlesUseCase: GetArticles(repository),
            );
          },
        ),
      ],
      child: const MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Latest Summaries',
      theme: AppTheme.lightTheme,
      home: const HomePage(),
    );
  }
}
