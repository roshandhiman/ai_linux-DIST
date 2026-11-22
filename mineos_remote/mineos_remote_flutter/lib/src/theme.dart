import 'package:flutter/material.dart';

abstract final class Palette {
  static const sidebar = Color(0xFF111217);
  static const glow = Color(0xFF151823);
  static const bannerStart = Color(0xFF1A1E2C);
  static const bannerEnd = Color(0xFF16181F);
  static const brandStart = Color(0xFFA6B5FF);
  static const brandEnd = Color(0xFF697DCE);
  static const onAccent = Color(0xFF141B36);
  static const background = Color(0xFF0D0E12);
  static const surface = Color(0xFF15161C);
  static const surfaceHigh = Color(0xFF1C1E26);
  static const border = Color(0xFF292C36);
  static const text = Color(0xFFF1F2F6);
  static const muted = Color(0xFF969BAA);
  static const faint = Color(0xFF747B8D);
  static const accent = Color(0xFF91A7FF);
  static const running = accent;
  static const awaiting = Color(0xFFE9B96E);
  static const done = Color(0xFF78C8A3);
  static const failed = Color(0xFFED8A94);
}

abstract final class Space {
  static const double xs = 4,
      sm = 8,
      md = 12,
      lg = 16,
      xl = 24,
      xxl = 32,
      xxxl = 48;
}

abstract final class AppStyle {
  static const double radius = 16, smallRadius = 12;
  static const motion = Duration(milliseconds: 220);
  static const pageWidth = 1160.0;
  static const mobileBreakpoint = 700.0;
  static const desktopBreakpoint = 1100.0;
  static BorderRadius get rounded => BorderRadius.circular(radius);
  static BorderRadius get smallRounded => BorderRadius.circular(smallRadius);
}

TextStyle uiText({
  double size = 14,
  Color color = Palette.text,
  FontWeight weight = FontWeight.w400,
  double height = 1.5,
}) => TextStyle(
  fontFamily: 'Inter',
  fontSize: size,
  color: color,
  fontWeight: weight,
  height: height,
  letterSpacing: -0.15,
);

/// Monospace is reserved for the actual agent code and command output.
TextStyle mono({
  double size = 13,
  Color color = Palette.text,
  FontWeight weight = FontWeight.w400,
  double height = 1.5,
}) => TextStyle(
  fontFamily: 'monospace',
  fontSize: size,
  color: color,
  fontWeight: weight,
  height: height,
);

ThemeData buildTheme() {
  final scheme = const ColorScheme.dark(
    primary: Palette.accent,
    onPrimary: Palette.onAccent,
    secondary: Palette.accent,
    surface: Palette.surface,
    onSurface: Palette.text,
    error: Palette.failed,
    outline: Palette.border,
  );
  final base = ThemeData(
    brightness: Brightness.dark,
    useMaterial3: true,
    fontFamily: 'Inter',
    colorScheme: scheme,
    scaffoldBackgroundColor: Palette.background,
  );
  return base.copyWith(
    textTheme: base.textTheme.copyWith(
      headlineLarge: uiText(size: 34, weight: FontWeight.w600, height: 1.2),
      headlineMedium: uiText(size: 28, weight: FontWeight.w600, height: 1.25),
      titleLarge: uiText(size: 22, weight: FontWeight.w600, height: 1.35),
      titleMedium: uiText(size: 17, weight: FontWeight.w600, height: 1.4),
      titleSmall: uiText(size: 15, weight: FontWeight.w600),
      bodyLarge: uiText(size: 16),
      bodyMedium: uiText(size: 14),
      bodySmall: uiText(size: 13, color: Palette.muted),
      labelLarge: uiText(size: 14, weight: FontWeight.w600),
      labelMedium: uiText(size: 12, weight: FontWeight.w500),
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: Palette.background,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      titleTextStyle: uiText(size: 16, weight: FontWeight.w600),
    ),
    dividerTheme: const DividerThemeData(color: Palette.border, space: 1),
    splashFactory: InkRipple.splashFactory,
    splashColor: Palette.accent.withValues(alpha: .08),
    hoverColor: Colors.white.withValues(alpha: .035),
    highlightColor: Palette.accent.withValues(alpha: .04),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(44, 48),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: AppStyle.smallRounded),
        textStyle: uiText(size: 14, weight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: Palette.text,
        minimumSize: const Size(44, 44),
        side: const BorderSide(color: Palette.border),
        shape: RoundedRectangleBorder(borderRadius: AppStyle.smallRounded),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        textStyle: uiText(size: 13, weight: FontWeight.w600),
        shape: RoundedRectangleBorder(borderRadius: AppStyle.smallRounded),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Palette.background,
      contentPadding: const EdgeInsets.all(16),
      labelStyle: uiText(color: Palette.muted),
      hintStyle: uiText(color: Palette.faint),
      border: OutlineInputBorder(
        borderRadius: AppStyle.smallRounded,
        borderSide: const BorderSide(color: Palette.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: AppStyle.smallRounded,
        borderSide: const BorderSide(color: Palette.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: AppStyle.smallRounded,
        borderSide: const BorderSide(color: Palette.accent, width: 1.5),
      ),
    ),
    floatingActionButtonTheme: FloatingActionButtonThemeData(
      backgroundColor: Palette.accent,
      foregroundColor: scheme.onPrimary,
      elevation: 6,
      hoverElevation: 10,
      shape: RoundedRectangleBorder(borderRadius: AppStyle.rounded),
      extendedTextStyle: uiText(size: 14, weight: FontWeight.w600),
    ),
    tooltipTheme: TooltipThemeData(
      decoration: BoxDecoration(
        color: Palette.surfaceHigh,
        border: Border.all(color: Palette.border),
        borderRadius: BorderRadius.circular(8),
      ),
      textStyle: uiText(size: 12),
      waitDuration: const Duration(milliseconds: 400),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: Palette.surface,
      surfaceTintColor: Colors.transparent,
      indicatorColor: Palette.accent.withValues(alpha: .12),
      height: 68,
      labelTextStyle: WidgetStateProperty.resolveWith(
        (states) => uiText(
          size: 11,
          color: states.contains(WidgetState.selected)
              ? Palette.accent
              : Palette.muted,
          weight: FontWeight.w500,
        ),
      ),
    ),
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: Palette.accent,
      linearTrackColor: Palette.border,
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: Palette.surface,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: AppStyle.rounded),
    ),
  );
}
