import 'package:flutter/material.dart';

class AppTheme {
  static const Color ink = Color(0xFF17212B);
  static const Color mutedInk = Color(0xFF52606D);
  static const Color primaryBlue = Color(0xFF174A6E);
  static const Color focusBlue = Color(0xFF0B6EAA);
  static const Color fpTitleBackground = Color(0xFFFFE3DE);
  static const Color faTitleBackground = Color(0xFFDDEFF8);
  static const Color cardBackground = Color(0xFFFFFFFF);
  static const Color scaffoldBackground = Color(0xFFF4F1EA);
  static const Color quoteBackground = Color(0xFFF5F7F8);
  static const Color dividerColor = Color(0xFFD7DCE0);
  static const Color staleBackground = Color(0xFFFFF3CD);
  static const Color staleInk = Color(0xFF5C4300);

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: const ColorScheme.light(
        primary: primaryBlue,
        onPrimary: Colors.white,
        secondary: focusBlue,
        onSecondary: Colors.white,
        surface: cardBackground,
        onSurface: ink,
        error: Color(0xFFB42318),
        onError: Colors.white,
      ),
      scaffoldBackgroundColor: scaffoldBackground,
      focusColor: focusBlue.withValues(alpha: 0.16),
      appBarTheme: const AppBarTheme(
        backgroundColor: scaffoldBackground,
        foregroundColor: ink,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
      ),
      cardTheme: CardThemeData(
        color: cardBackground,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: dividerColor),
        ),
        elevation: 2,
      ),
      textTheme: const TextTheme(
        headlineMedium: TextStyle(
          fontSize: 28,
          height: 1.16,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.4,
          color: ink,
        ),
        headlineSmall: TextStyle(
          fontSize: 20,
          height: 1.2,
          fontWeight: FontWeight.w700,
          color: ink,
        ),
        bodyLarge: TextStyle(fontSize: 16, height: 1.58, color: ink),
        bodyMedium: TextStyle(fontSize: 14, height: 1.45, color: mutedInk),
        labelSmall: TextStyle(
          fontSize: 12,
          height: 1.3,
          fontWeight: FontWeight.w600,
          color: mutedInk,
        ),
      ),
      dividerColor: dividerColor,
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(44, 44),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(44, 44),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(minimumSize: const Size(44, 44)),
      ),
    );
  }
}
