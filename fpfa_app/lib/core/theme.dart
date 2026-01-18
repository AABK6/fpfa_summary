import 'package:flutter/material.dart';

class AppTheme {
  static const Color primaryBlue = Colors.blue;
  static const Color fpTitleBackground = Color(0xFFFFCCCC);
  static const Color faTitleBackground = Color(0xFFCCEEFF);
  static const Color cardBackground = Colors.white;
  static const Color scaffoldBackground = Color(0xFFF0F2F5);
  static const Color quoteBackground = Color(0xFFF8F9FA);
  static const Color dividerColor = Color(0xFFDDDDDD);

  static ThemeData get lightTheme {
    return ThemeData(
      primarySwatch: Colors.blue,
      scaffoldBackgroundColor: scaffoldBackground,
      cardTheme: CardTheme(
        color: cardBackground,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        elevation: 8,
      ),
      textTheme: const TextTheme(
        headlineSmall: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.bold,
          color: Colors.black87,
        ),
        bodyLarge: TextStyle(
          fontSize: 16,
          color: Colors.black87,
        ),
        bodyMedium: TextStyle(
          fontSize: 14,
          color: Colors.black54,
        ),
        labelSmall: TextStyle(
          fontSize: 12,
          color: Colors.grey,
        ),
      ),
    );
  }
}
