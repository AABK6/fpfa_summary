import 'package:flutter/material.dart';
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

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final sharedPreferences = await SharedPreferences.getInstance();
  
  runApp(
    MultiProvider(
      providers: [
        Provider<http.Client>(create: (_) => http.Client()),
        Provider<SharedPreferences>(create: (_) => sharedPreferences),
        ProxyProvider2<http.Client, SharedPreferences, ArticleProvider>(
          update: (context, client, prefs, _) {
            final remoteDataSource = RemoteArticleDataSourceImpl(
              client: client,
              baseUrl: 'http://localhost:8000', // Default for local dev with FastAPI
            );
            final localDataSource = LocalArticleDataSourceImpl(
              sharedPreferences: prefs,
            );
            final repository = ArticleRepositoryImpl(
              remoteDataSource: remoteDataSource,
              localDataSource: localDataSource,
            );
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