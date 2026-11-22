import 'package:flutter/material.dart';

import 'theme.dart';
import 'widgets.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final body = Theme.of(
      context,
    ).textTheme.bodyMedium?.copyWith(height: 1.55, color: Palette.text);
    return Scaffold(
      appBar: AppBar(
        title: const Text('About'),
        actions: const [DemoReplayChip(), SizedBox(width: 12)],
      ),
      body: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            children: [
              Text(
                'MineOS Remote',
                style: mono(size: 18, weight: FontWeight.w700),
              ),
              const SizedBox(height: 12),
              Text(
                'MineOS is a Debian-based Linux distribution with its AI '
                'built in and running offline. Its terminal agent routes each '
                'request locally, then plans and acts with Qwen2.5 1.5B on '
                'llama.cpp, runs every action in a Bubblewrap sandbox, and '
                'stops for your OK before it writes a file or runs a command. '
                'Nothing is sent to a cloud AI, so organisations that cannot '
                'risk leaking data can still use an agent. MineOS Remote lets '
                'you watch those agent sessions from your phone. In this '
                'round it replays recorded sessions. In live mode, the app '
                'connects to a MineOS machine on the same office network, and '
                'you will answer the approval prompt from your phone.',
                style: body,
              ),
              const SizedBox(height: 20),
              const _Fact(
                icon: Icons.lock,
                color: Palette.done,
                text:
                    'Local badge: the session used the on-device model. '
                    'No data left the machine.',
              ),
              const _Fact(
                icon: Icons.replay,
                color: Palette.accent,
                text:
                    'Demo replay: recorded sessions, replayed with '
                    'compressed timing. Not a live machine.',
              ),
              const _Fact(
                icon: Icons.front_hand_outlined,
                color: Palette.awaiting,
                text:
                    'Awaiting approval: the agent is paused at its y/N '
                    'prompt and nothing has been written yet.',
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Fact extends StatelessWidget {
  const _Fact({required this.icon, required this.color, required this.text});

  final IconData icon;
  final Color color;
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 16, color: color),
        const SizedBox(width: 10),
        Expanded(
          child: Text(text, style: mono(size: 12, color: Palette.muted)),
        ),
      ],
    ),
  );
}
