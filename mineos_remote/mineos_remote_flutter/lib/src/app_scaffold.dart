import 'package:flutter/material.dart';

import 'about_screen.dart';
import 'connection_screen.dart';
import 'theme.dart';
import 'widgets.dart';

class AppScaffold extends StatelessWidget {
  const AppScaffold({
    super.key,
    required this.body,
    required this.title,
    this.selectedIndex = 0,
    this.showBack = false,
    this.floatingActionButton,
    this.actions = const [],
  });
  final Widget body;
  final String title;
  final int selectedIndex;
  final bool showBack;
  final Widget? floatingActionButton;
  final List<Widget> actions;

  void _navigate(BuildContext context, int index) {
    if (index == selectedIndex && !showBack) return;
    if (index == 0) {
      Navigator.of(context).popUntil((route) => route.isFirst);
      return;
    }
    final route = MaterialPageRoute<void>(
      builder: (_) =>
          index == 1 ? const ConnectionScreen() : const AboutScreen(),
    );
    if (showBack) {
      Navigator.of(context).pushReplacement(route);
    } else {
      Navigator.of(context).push(route);
    }
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final mobile = width < AppStyle.mobileBreakpoint;
    final expanded = width >= AppStyle.desktopBreakpoint;
    return Scaffold(
      floatingActionButton: floatingActionButton,
      bottomNavigationBar: mobile
          ? DecoratedBox(
              decoration: const BoxDecoration(
                border: Border(top: BorderSide(color: Palette.border)),
              ),
              child: NavigationBar(
                selectedIndex: selectedIndex,
                onDestinationSelected: (index) => _navigate(context, index),
                destinations: const [
                  NavigationDestination(
                    icon: Icon(Icons.grid_view_rounded),
                    label: 'Sessions',
                  ),
                  NavigationDestination(
                    icon: Icon(Icons.tune_rounded),
                    label: 'Connection',
                  ),
                  NavigationDestination(
                    icon: Icon(Icons.info_outline_rounded),
                    label: 'About',
                  ),
                ],
              ),
            )
          : null,
      body: SafeArea(
        bottom: false,
        child: Row(
          children: [
            if (!mobile)
              _Sidebar(
                expanded: expanded,
                selectedIndex: selectedIndex,
                onSelect: (index) => _navigate(context, index),
              ),
            Expanded(
              child: Column(
                children: [
                  Container(
                    height: 72,
                    padding: EdgeInsets.symmetric(
                      horizontal: mobile ? Space.lg : Space.xxl,
                    ),
                    decoration: const BoxDecoration(
                      border: Border(bottom: BorderSide(color: Palette.border)),
                    ),
                    child: Row(
                      children: [
                        if (showBack) ...[
                          IconButton(
                            tooltip: 'Back',
                            onPressed: () => Navigator.of(context).pop(),
                            icon: const Icon(
                              Icons.arrow_back_rounded,
                              size: 20,
                            ),
                          ),
                          const SizedBox(width: Space.sm),
                        ] else if (mobile) ...[
                          const BrandMark(size: 30),
                          const SizedBox(width: Space.md),
                        ] else ...[
                          Text(
                            'Workspace',
                            style: uiText(color: Palette.faint),
                          ),
                          const Padding(
                            padding: EdgeInsets.symmetric(horizontal: Space.md),
                            child: Text(
                              '/',
                              style: TextStyle(color: Palette.border),
                            ),
                          ),
                        ],
                        Expanded(
                          child: Text(
                            title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: uiText(weight: FontWeight.w500),
                          ),
                        ),
                        if (!mobile) ...[
                          const DemoReplayChip(),
                          const SizedBox(width: Space.lg),
                        ],
                        ...actions,
                      ],
                    ),
                  ),
                  Expanded(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: RadialGradient(
                          center: const Alignment(.6, -1.6),
                          radius: 1.5,
                          colors: [
                            Palette.glow,
                            Palette.background,
                          ],
                          stops: const [0, .7],
                        ),
                      ),
                      child: SizedBox.expand(child: body),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class BrandMark extends StatelessWidget {
  const BrandMark({super.key, this.size = 36});
  final double size;
  @override
  Widget build(BuildContext context) => Container(
    width: size,
    height: size,
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(size * .28),
      gradient: const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Palette.brandStart, Palette.brandEnd],
      ),
      boxShadow: [
        BoxShadow(color: Palette.accent.withValues(alpha: .12), blurRadius: 14),
      ],
    ),
    child: Icon(
      Icons.layers_rounded,
      size: size * .6,
      color: Palette.onAccent,
    ),
  );
}

class _Sidebar extends StatelessWidget {
  const _Sidebar({
    required this.expanded,
    required this.selectedIndex,
    required this.onSelect,
  });
  final bool expanded;
  final int selectedIndex;
  final ValueChanged<int> onSelect;
  @override
  Widget build(BuildContext context) => Container(
    width: expanded ? 232 : 84,
    decoration: const BoxDecoration(
      color: Palette.sidebar,
      border: Border(right: BorderSide(color: Palette.border)),
    ),
    padding: EdgeInsets.symmetric(
      horizontal: expanded ? Space.lg : Space.md,
      vertical: Space.xl,
    ),
    child: Column(
      crossAxisAlignment: expanded
          ? CrossAxisAlignment.start
          : CrossAxisAlignment.center,
      children: [
        Padding(
          padding: EdgeInsets.only(left: expanded ? Space.sm : 0),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const BrandMark(),
              if (expanded) ...[
                const SizedBox(width: Space.md),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'MineOS',
                      style: uiText(size: 18, weight: FontWeight.w700),
                    ),
                    Text(
                      'Remote',
                      style: uiText(size: 12, color: Palette.muted),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: Space.xxxl),
        if (expanded)
          Padding(
            padding: const EdgeInsets.fromLTRB(Space.md, 0, 0, Space.md),
            child: Text(
              'WORKSPACE',
              style: uiText(
                size: 10,
                color: Palette.faint,
                weight: FontWeight.w600,
              ),
            ),
          ),
        for (final (index, icon, label) in [
          (0, Icons.grid_view_rounded, 'Sessions'),
          (1, Icons.tune_rounded, 'Connection'),
          (2, Icons.info_outline_rounded, 'About'),
        ])
          Padding(
            padding: const EdgeInsets.only(bottom: Space.xs),
            child: Tooltip(
              message: expanded ? '' : label,
              child: Material(
                color: index == selectedIndex
                    ? Palette.accent.withValues(alpha: .1)
                    : Colors.transparent,
                borderRadius: AppStyle.smallRounded,
                child: InkWell(
                  borderRadius: AppStyle.smallRounded,
                  onTap: () => onSelect(index),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: Space.md,
                      vertical: 14,
                    ),
                    child: Row(
                      mainAxisSize: expanded
                          ? MainAxisSize.max
                          : MainAxisSize.min,
                      children: [
                        Icon(
                          icon,
                          size: 20,
                          color: index == selectedIndex
                              ? Palette.accent
                              : Palette.muted,
                        ),
                        if (expanded) ...[
                          const SizedBox(width: Space.md),
                          Text(
                            label,
                            style: uiText(
                              color: index == selectedIndex
                                  ? Palette.text
                                  : Palette.muted,
                              weight: index == selectedIndex
                                  ? FontWeight.w600
                                  : FontWeight.w400,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        const Spacer(),
        if (expanded)
          Container(
            padding: const EdgeInsets.all(Space.lg),
            decoration: BoxDecoration(
              color: Palette.surface,
              border: Border.all(color: Palette.border),
              borderRadius: AppStyle.smallRounded,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.shield_outlined,
                  size: 20,
                  color: Palette.accent,
                ),
                const SizedBox(height: Space.md),
                Text(
                  'Your machine.\nYour intelligence.',
                  style: uiText(size: 13, weight: FontWeight.w500),
                ),
                const SizedBox(height: Space.sm),
                Text(
                  'Recorded sessions.\nA window into your agent.',
                  style: uiText(size: 12, color: Palette.muted),
                ),
              ],
            ),
          ),
        const SizedBox(height: Space.xl),
        if (expanded)
          Padding(
            padding: const EdgeInsets.only(left: Space.md),
            child: Text(
              'MineOS Remote  /  v1.0',
              style: uiText(size: 11, color: Palette.faint),
            ),
          )
        else
          const Icon(
            Icons.desktop_windows_outlined,
            size: 19,
            color: Palette.faint,
          ),
      ],
    ),
  );
}

void showNewTaskInfo(BuildContext context) => showDialog<void>(
  context: context,
  builder: (context) => AlertDialog(
    icon: const Icon(Icons.terminal_rounded, color: Palette.accent),
    title: const Text('Start on your MineOS machine'),
    content: const Text(
      'Run a task in the MineOS terminal using ai. This version of Remote replays recorded sessions; creating live tasks from your phone is coming later.',
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.of(context).pop(),
        child: const Text('Got it'),
      ),
    ],
  ),
);
