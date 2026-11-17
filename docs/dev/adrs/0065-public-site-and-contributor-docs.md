# 0065. The public site and the contributor documentation

- **Status:** Accepted
- **Date:** 2026-11-02
- **Implementation:** ✅ Implemented
- **Priority:** Medium

## Context

The user documentation was redesigned as a separate Zensical site, organised by interface (Application, Python,
Command Line) with a shared User guide and a Physics reference, and illustrated with captures from the real
application (ADR-0060). It was built and reviewed outside this repository. Meanwhile the MkDocs site in `docs/`
served users and contributors together, with the web application at `/webapp/` (ADR-0023).

## Decision

- The public site lives in `website/`: the site in `website/surfaces/` (`mkdocs.yml`, `docs/`, `overrides/`), its
  generators (`render_*.py`, `import_gui_captures.py`, `capture_*.py`), its checks and its design notes and ADRs.
  `pixi run site-build` builds it strictly into `website/_build` and checks its generated links, the Physics catalogue
  headings and the parameter reference. Zensical is pinned at 0.0.73 in the pixi environment and lock.
- GitHub Pages publishes three parts at <https://enhantica.github.io/edi/>: the public site at the root, the MkDocs
  documentation (`mkdocs.yml`, `docs/`, executed notebooks included) at `/dev/`, and the web application at `/webapp/`.
  The public site may not own `/dev/` or `/webapp/`; the Pages workflow refuses it.
  **Amended 2026-11-17 (the owner):** `main` publishes the site and its web app only to edi-sites' `deploy-docs` branch,
  behind <https://easydiffraction.org>, each publish keeping the other half from that branch; it no longer deploys to
  GitHub Pages, which became the developers' test site, deployed from edi's `dev` branch.
- The app's Documentation link, What's new's link to the full page (ADR-0067) and its parameter help links (ADR-0061)
  point at the public site.
- Dictionary descriptions copied into the parameter reference leave out development task labels.

## Consequences

- User-facing pages are written in `website/surfaces/docs/`; contributor pages stay in `docs/`.
- The published layout of the earlier preview site is kept: pages, anchors and redirects keep their paths, now under
  the edi address.


## Recorded assistant prompt trials

The Python and command-line assistant pages say only when their prompt was last checked and that
another assistant may take different steps. The trial records are a contributor page,
[Assistant prompt trials](../assistant-prompt-trials.md), not part of the user docs. A trial fetches the actual published prompt and references, executes its generated artifact,
and records the assistant/date, source and artifact hashes, results and comparisons. Both the
existing prerelease-preview route and the official published-release route require this evidence;
metadata alone does not qualify either route. Historical prerequisite failures remain immutable.

CI checks the recorded provenance, citation and comparisons; it does not run an online assistant.
Staged tutorial/scientific-reference matches and separate single-fit regression mismatches stay
separate, with original numerical references and tolerances unchanged. Diagnostic executables
are identified as such and do not establish release or current-candidate qualification.


Retired walkthrough redirects terminate at the corresponding case tutorial on the
same interface. The former Python and Command line example-fit URLs both lead to
the LBCO HRPT tutorial; redirecting only to a tutorial index loses that destination.
The app's first-fit and scan walkthroughs retain their declared case targets.
