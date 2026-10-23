# edi

**edi** is the diffraction data-analysis product: one C++ product core bound into a Python
library (`import edi`), the `easydiffraction` CLI, a desktop QML app, and its WASM web
target — with the [`crysta`] engine underneath.

- **[Web app](https://enhantica.github.io/edi/webapp/)** — the app in the browser, nothing to install.
- **Platforms** — the desktop app runs on Linux (x86-64) and on macOS 14 or later (Apple silicon).
- **[User documentation](user/index.md)** — what edi does per surface, and the guides for
  people who use it without modifying it.
- **[Developer documentation](dev/index.md)** — the specification corpus: ADRs, the
  feature catalog, design docs, requirements coverage, library notes and the
  verification notebooks.

The diffraction **physics** lives in the org's private physics knowledge book, consumed
through crysta.
