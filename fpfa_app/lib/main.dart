import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'core/theme.dart';
import 'core/api_config.dart';
import 'data/datasources/local_article_data_source.dart';
import 'data/datasources/remote_article_data_source.dart';
import 'data/repositories/article_repository_impl.dart';
import 'domain/usecases/get_articles.dart';
import 'presentation/providers/article_provider.dart';
import 'presentation/pages/home_page.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final sharedPreferences = await SharedPreferences.getInstance();

  runApp(
    MultiProvider(
      providers: [
        Provider<http.Client>(
          create: (_) => http.Client(),
          dispose: (_, client) => client.close(),
        ),
        Provider<SharedPreferences>.value(value: sharedPreferences),
        Provider<ArticleRepositoryImpl>(
          create: (context) {
            final client = context.read<http.Client>();
            final prefs = context.read<SharedPreferences>();
            return ArticleRepositoryImpl(
              remoteDataSource: RemoteArticleDataSourceImpl(
                client: client,
                baseUrl: resolveApiBaseUrl(),
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
            return ArticleProvider(getArticlesUseCase: GetArticles(repository));
          },
        ),
      ],
      child: const MyApp(),
    ),
  );
  if (kIsWeb) {
    SemanticsBinding.instance.ensureSemantics();
  }
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Latest Summaries',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      home: const HomePage(),
    );
  }
}
