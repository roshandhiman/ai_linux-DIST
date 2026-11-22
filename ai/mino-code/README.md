# Mino Code

Mino Code is MineOS's customised Freebuff terminal client. It uses Freebuff's account login, hosted models, agents, tools, session management, and sponsored access. The interface uses a mint and lavender palette, a compact project header, and Mino Code branding.

## Install

From the MineOS checkout inside Linux, run

    bash scripts/install-mino-code.sh
    cd ~/your-project
    mino code

You can also run mino-code directly. Run mino-code login to use the upstream browser sign-in flow, mino-code doctor for diagnostics, and mino-code --help for available options. Complete account sign-in in your browser. Your project is handled by Freebuff's service under its terms and privacy policy.

The build script fetches upstream source at 35ed93aeb6bfcb739effda228ba34f1d03986d98 and Bun 1.3.14, applies interface.patch, installs the locked dependencies, and compiles a standalone Linux binary. Build for arm64 or amd64 with scripts/build-mino-code.sh. The binary and its required tree-sitter.wasm live together in /opt/mino-code/current. The installer preserves older releases for rollback.

The patch changes presentation and CLI naming. Upstream login URLs, credential storage, model selection, tools, ads, and API protocols are preserved. The Apache 2.0 license and upstream NOTICE are included. Rebuild through the MineOS installer to upgrade the fork.

The build uses the public production configuration documented in the upstream smoke-test guide. Web-only Stripe and PostHog fields use that guide's inactive placeholders. Hosted coding sessions and browser sign-in use the production Freebuff and Codebuff endpoints. Successful account sign-in is required before a live coding session can be verified.

[Upstream source](https://github.com/CodebuffAI/freebuff/tree/35ed93aeb6bfcb739effda228ba34f1d03986d98)
