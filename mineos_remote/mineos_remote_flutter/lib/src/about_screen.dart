import 'package:flutter/material.dart';
import 'app_scaffold.dart';
import 'theme.dart';
import 'widgets.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});
  @override
  Widget build(BuildContext context) => AppScaffold(
    title: 'About MineOS',
    selectedIndex: 2,
    showBack: true,
    body: Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 800),
        child: ListView(
          padding: const EdgeInsets.all(Space.xl),
          children: [
            const SizedBox(height: Space.xl),
            const Align(
              alignment: Alignment.centerLeft,
              child: BrandMark(size: 56),
            ),
            const SizedBox(height: Space.xl),
            Text(
              'Intelligence, on your terms.',
              style: Theme.of(context).textTheme.headlineLarge,
            ),
            const SizedBox(height: Space.lg),
            Text(
              'A quieter way to stay connected to your agent.',
              style: uiText(size: 17, color: Palette.muted),
            ),
            const SizedBox(height: Space.xxl),
            Container(
              padding: const EdgeInsets.all(Space.xl),
              decoration: BoxDecoration(
                color: Palette.surface,
                border: Border.all(color: Palette.border),
                borderRadius: AppStyle.rounded,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Meet MineOS Remote',
                    style: uiText(size: 20, weight: FontWeight.w600),
                  ),
                  const SizedBox(height: Space.md),
                  Text(
                    'MineOS is a Debian-based Linux desktop with an AI agent that runs locally. Remote gives you a clear view of its sessions, decisions, and sandboxed actions from your phone or browser.',
                    style: uiText(size: 15, color: Palette.muted),
                  ),
                  const SizedBox(height: Space.xl),
                  const DemoReplayChip(),
                  const SizedBox(height: Space.md),
                  Text(
                    'This release replays recorded sessions. Live machine connections and phone approvals are planned for a later version.',
                    style: uiText(size: 14, color: Palette.muted),
                  ),
                ],
              ),
            ),
            const SizedBox(height: Space.lg),
            const _Fact(
              icon: Icons.memory_rounded,
              color: Palette.accent,
              title: 'Local by design',
              text:
                  'The Local badge identifies recordings that used the on-device model, rather than a hosted AI provider.',
            ),
            const _Fact(
              icon: Icons.replay_rounded,
              color: Palette.accent,
              title: 'Every step, in focus',
              text:
                  'Explore recorded sessions with compressed replay timing, expandable steps, and clear outcomes.',
            ),
            const _Fact(
              icon: Icons.shield_outlined,
              color: Palette.awaiting,
              title: 'You stay in control',
              text:
                  'The agent pauses before actions that require approval. Approval controls are previews in this demo.',
            ),
            const SizedBox(height: Space.xl),
            Center(
              child: Text(
                'MineOS Remote  ·  Version 1.0',
                style: uiText(size: 12, color: Palette.faint),
              ),
            ),
            const SizedBox(height: Space.xxl),
          ],
        ),
      ),
    ),
  );
}

class _Fact extends StatelessWidget {
  const _Fact({
    required this.icon,
    required this.color,
    required this.title,
    required this.text,
  });
  final IconData icon;
  final Color color;
  final String title, text;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: Space.md),
    child: Container(
      padding: const EdgeInsets.all(Space.xl),
      decoration: BoxDecoration(
        color: Palette.surface,
        border: Border.all(color: Palette.border),
        borderRadius: AppStyle.rounded,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(Space.md),
            decoration: BoxDecoration(
              color: color.withValues(alpha: .08),
              borderRadius: AppStyle.smallRounded,
            ),
            child: Icon(icon, color: color, size: 22),
          ),
          const SizedBox(width: Space.lg),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: uiText(size: 15, weight: FontWeight.w600)),
                const SizedBox(height: Space.xs),
                Text(text, style: uiText(size: 14, color: Palette.muted)),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}
