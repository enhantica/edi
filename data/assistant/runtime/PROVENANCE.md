# Official runtime redistribution

Codex app-server package 0.162.1, upstream source commit `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`:
https://github.com/openai/codex/tree/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d
The immutable archive digests and target mapping are owned by tools/deps/assistant-runtime/recipe.yaml; cmake/assistant_runtime.cmake consumes the installed package. The complete dedicated package is retained, including the code-mode host, rg and platform helpers. Upstream executable bytes, relative paths and signatures are preserved. No recursive force-resigning or stripping is performed.

Codex Apache-2.0 LICENSE and NOTICE are copied from that source revision's release tag. Ripgrep 15.2.0 is identified by the pinned scripts/codex_package/rg manifest; its MIT licence and dual-license COPYING accompany this distribution. The patched zsh helper is identified by scripts/codex_package/codex-zsh and its published upstream artifact; the pinned build workflow declares zsh source commit 77045ef899e53b9598bebc5a41db93a548a40ca6 with the patch codex-rs/shell-escalation/patches/zsh-exec-wrapper.patch. Its LICENCE is included. Linux bwrap is built from the vendored bubblewrap source at the Codex source revision; its LGPL COPYING is included.

Corresponding source and build/patch instructions:
- Codex/server/code host: https://github.com/openai/codex/tree/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs
- ripgrep 15.2.0: https://github.com/BurntSushi/ripgrep/tree/15.2.0
- zsh source: https://github.com/zsh-users/zsh/tree/77045ef899e53b9598bebc5a41db93a548a40ca6
- zsh patch/build: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/.github/scripts/build-zsh-release-artifact.sh
- bubblewrap source: https://github.com/openai/codex/tree/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/vendor/bubblewrap

The optional shell_zsh_fork feature is disabled for this prototype launch: packaged macOS zsh has a higher deployment minimum than the normal runtime. This preserves Edi's declared minimum and does not modify the provider profile. Actual macOS distribution signing/notarization and live sign-in are separate qualification duties; presence of upstream signatures is not a completed Edi distribution audit.


The bundled code-mode host's pinned Cargo.lock resolves rusty-V8 150.4.0 and deno_core_icudata 0.77.0.
`rusty-v8-LICENSE-MIT` is the exact Deno authors' MIT text from denoland/rusty_v8 tag v150.4.0
(Git blob 5a671244de937cfc449c42d48da7867e4f0a7852). That tag's V8 submodule is
ac1e23989121713ca642f6650b34deff7b686896; `v8-LICENSE` is its exact root licence and
external-library qualifications (Git blob 9898b2d4833bfe87c05ba9106f082ed600bb2aab).
These materials supplement the separate Qt-associated V8 notices.

The published deno_core_icudata 0.77.0 crate has SHA256
a9efff8990a82c1ae664292507e1a5c6749ddd2312898cdf9cd7cb1fd4bc64c6 and source commit
83537ba16a4bf1645fc8322e81f7aaf0149a8922. Its metadata declares MIT but includes no licence text.
Its src/icudtl.dat has Git blob d1a12cb93065157498a11ff5f4b9a6501ee22506, identical to
source/common/icudtl.dat at the V8 ICU submodule ee5f27adc28bd3f15b2c293f726d14d2e336cbd5.
`icu-LICENSE` is that exact Chromium ICU root licence, including all additional notices
(Git blob 0b9efcd9092f977797c2572de717ca2edac50bc2); the data's Unicode terms are retained,
rather than inferred from the Rust crate's metadata.
Source: https://chromium.googlesource.com/chromium/deps/icu/+/ee5f27adc28bd3f15b2c293f726d14d2e336cbd5/

These exact materials resolve the named wrapper/engine/data notice omissions. Complete binary-transitive
attribution and actual installer qualification remain open. For an elected Linux binary release, delivery
must also include the matching vendored bubblewrap source, the selected zsh source plus the exact wrapper
patch/build script, and the corresponding Codex source/build inputs identified above, or a verified applicable
source-download arrangement alongside that release. URLs in this development provenance are not evidence
that the final release delivered corresponding source. No release/installer clearance is claimed.

Windows dependency packaging additionally pins the official x86_64-pc-windows-msvc standalone
app-server tarball from the same 0.162.1 release (SHA256 e67c01033b79e7ee3ec763b85cf5c7b774ba4846d46c0b0920193bd19f835728).
The upstream Codex092 scripts/codex_package/layout.py and targets.py define the .exe entrypoint,
code-mode host, rg and command-runner/sandbox-setup resource closure. Their Windows rule does not
require POSIX executable bits. The separate tools/deps/assistant-packages workspace locks these
same recipes for Windows without enabling the Edi Windows app, bash tasks or installer. Metadata
coverage is distinct from native Windows package execution and distribution qualification.
