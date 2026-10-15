# Official runtime redistribution

Codex app-server package 0.162.1, upstream source commit `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`:
https://github.com/openai/codex/tree/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d
The immutable archive digests and target mapping are in cmake/assistant_runtime.cmake. The complete dedicated package is retained, including the code-mode host, rg and platform helpers. Upstream executable bytes, relative paths and signatures are preserved. No recursive force-resigning or stripping is performed.

Codex Apache-2.0 LICENSE and NOTICE are copied from that source revision's release tag. Ripgrep 15.2.0 is identified by the pinned scripts/codex_package/rg manifest; its MIT licence and dual-license COPYING accompany this distribution. The patched zsh helper is identified by scripts/codex_package/codex-zsh and its published upstream artifact; the pinned build workflow declares zsh source commit 77045ef899e53b9598bebc5a41db93a548a40ca6 with the patch codex-rs/shell-escalation/patches/zsh-exec-wrapper.patch. Its LICENCE is included. Linux bwrap is built from the vendored bubblewrap source at the Codex source revision; its LGPL COPYING is included.

Corresponding source and build/patch instructions:
- Codex/server/code host: https://github.com/openai/codex/tree/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs
- ripgrep 15.2.0: https://github.com/BurntSushi/ripgrep/tree/15.2.0
- zsh source: https://github.com/zsh-users/zsh/tree/77045ef899e53b9598bebc5a41db93a548a40ca6
- zsh patch/build: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/.github/scripts/build-zsh-release-artifact.sh
- bubblewrap source: https://github.com/openai/codex/tree/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/vendor/bubblewrap

The optional shell_zsh_fork feature is disabled for this prototype launch: packaged macOS zsh has a higher deployment minimum than the normal runtime. This preserves Edi's declared minimum and does not modify the provider profile. Actual macOS distribution signing/notarization and live sign-in are separate qualification duties; presence of upstream signatures is not a completed Edi distribution audit.
