import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// MineOS Remote's palette: near-black with a faint green cast, like a
/// terminal, high-contrast text, and one accent (cyan). Amber, green and red
/// are used only for session status, never for decoration.
abstract final class Palette {
  static const background = Color(0xFF090C0B);
  static const surface = Color(0xFF101513);
  static const surfaceHigh = Color(0xFF161D1A);
  static const border = Color(0xFF223029);
  static const text = Color(0xFFE7EEEA);
  static const muted = Color(0xFF8C9C94);
  static const faint = Color(0xFF5B6A63);

  static const accent = Color(0xFF5CE1F0);

  static const running = accent;
  static const awaiting = Color(0xFFFFB547);
  static const done = Color(0xFF4ADE80);
  static const failed = Color(0xFFFF6B6B);
}

TextStyle mono({
  double size = 13,
  Color color = Palette.text,
  FontWeight weight = FontWeight.w400,
  double height = 1.45,
}) => GoogleFonts.jetBrainsMono(
  fontSize: size,
  color: color,
  fontWeight: weight,
  height: height,
);

ThemeData buildTheme() {
  final base = ThemeData(
    brightness: Brightness.dark,
    useMaterial3: true,
    colorScheme: const ColorScheme.dark(
      primary: Palette.accent,
      onPrimary: Palette.background,
      secondary: Palette.accent,
      surface: Palette.surface,
      onSurface: Palette.text,
      error: Palette.failed,
      outline: Palette.border,
    ),
    scaffoldBackgroundColor: Palette.background,
  );
  final text = GoogleFonts.interTextTheme(base.textTheme).apply(
    bodyColor: Palette.text,
    displayColor: Palette.text,
  );
  return base.copyWith(
    textTheme: text,
    appBarTheme: AppBarTheme(
      backgroundColor: Palette.background,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      titleTextStyle: mono(size: 16, weight: FontWeight.w700),
      iconTheme: const IconThemeData(color: Palette.text),
    ),
    dividerTheme: const DividerThemeData(color: Palette.border, space: 1),
    tooltipTheme: TooltipThemeData(
      decoration: BoxDecoration(
        color: Palette.surfaceHigh,
        border: Border.all(color: Palette.border),
        borderRadius: BorderRadius.circular(6),
      ),
      textStyle: mono(size: 12),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      waitDuration: const Duration(milliseconds: 200),
      showDuration: const Duration(seconds: 4),
      triggerMode: TooltipTriggerMode.tap,
    ),
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: Palette.accent,
    ),
  );
}
