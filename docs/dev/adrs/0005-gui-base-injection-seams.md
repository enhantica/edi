# 0005. GUI-base injection seams (the base stays generic)

- **Status:** Accepted
- **Date:** 2026-07-04
- **Implementation:** 🟡 Partially implemented — the app host consumes gui-components v0.9.1 unmodified at a
  pinned sha and injects `ApplicationInfo`, its pages and its session through the base's existing seams
  ([ADR-0015](0015-edi-app-stack.md))
- **Priority:** High
- **Forward constraint (binding on new features):** The GUI base stays **generic**. edi injects its
  pages, `ApplicationInfo`, and session layer through the base's seams; **never** push an
  edi-specific into the `gui-components` layer. CI grep gate: no `easydiffraction`/`EasyApp`
  identity in the base layer (`grep -Rin -e easydiffraction -e EasyApp <base-path>` → nothing).

**Amended 2026-09-27 ([ADR-0015](0015-edi-app-stack.md) §4):** the base is the maintained gui-components
(the renamed EasyApp), which is not decoupled upstream and has no Phase I in any org checkout. Point 4
("adopt after Phase I") is replaced: edi adopts gui-components v0.9.1 now, byte-identical at a pinned sha,
builds only its own file list, and injects through the base's existing seams, so every identity the user
sees is edi's. The grep gate as spelled (`-e EasyApp`) matches every `EasyApplication` import and can never
pass on the renamed base; it is replaced by the configure-time sha and byte-identity check plus the runtime
identity assertion (no rendered text from the base's fallback identity).

## Context

`gui-components` is the Qt/QML GUI base (`Style` tokens, `Elements`, `Components`, a charting
façade). Its 2026-07 audit (`knowledge/libraries/gui-components/audit/`) found it **entangled with
EasyDiffraction** (app specifics baked into the library, stale `EasyApp` branding, an embedded
updater/tutorial harness) and defines a Phase-I decoupling: **G03 — decouple** introduces the
injection seams (a host-supplied **page model**, an injected **`ApplicationInfo`**, updater/QtTest
lifted out). edi must consume the base **after** it is decoupled, or edi inherits EasyDiffraction's
identity and an un-reusable base.

## Decision

edi adopts `gui-components` **only through its injection seams**, and keeps the base generic:

1. **edi supplies, the base receives.** edi provides its own **pages** (via the base's host-supplied
   page model), its own **`ApplicationInfo`**, and its **shared session layer** (`edi/shared`:
   theme/settings/page-model, and undo once crysta's EditCommand exists — ADR-0003). The base
   contains none of these.
2. **Style through tokens only.** edi styles via the base's `Style` design tokens and
   `Components.ApplicationWindow`; it never hardcodes colours/sizes and never imports the base's
   internals or private `.impl` controls (modern-Qt guidelines [MUST]).
3. **No back-flow of edi specifics.** No edi page, string, `ApplicationInfo`, or product asset is
   ever committed into the `gui-components` layer. Enforced by a CI grep gate for the EasyDiffraction
   identity in the base.
4. **Adopt after Phase I.** `edi/app` does not start until the base clears its **G01** (CMake/WASM
   revival), **G02** (native charts + WASM-safe settings), **G03** (decouple), and **G04** (qmllint/
   qmlformat/Qt Quick Test gated) — see the base's roadmap and ADR-0006.
5. **Absorb an improved base, keep the seam.** When an improved `gui-components` is brought in-repo
   (a product goal, with minimized deps — ADR-0008), the same generic-base / injected-specifics
   seam is preserved so the base stays independently reusable.

## Consequences

- edi's app is a thin composition over a reusable base; the base can serve other apps.
- edi's app surface is **gated** on the base's Phase I — a scheduling dependency tracked in the
  roadmap, not something edi can shortcut.
- A standing CI grep gate guards against the exact regression the audit was caused by (app
  specifics leaking into the library).

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Fork gui-components and edit it directly for edi | Re-creates the entanglement the audit is dissolving; the base stops being reusable. Rejected — inject through seams. |
| Start edi/app now on the un-decoupled base | Inherits EasyDiffraction identity + a base that can't build for WASM; the audit exists to prevent this. Rejected — wait for Phase I. |
| Bake edi pages into the base for convenience | Violates the generic-base seam and the CI identity gate. Rejected. |
