# ADR-0002: Shared workflow navigation and icons

Date: 2026-10-30
Status: implemented

The prior library guide declares Material Design Icons in `diffraction-lib/docs/docs/user-guide/analysis-workflow/`: Project `material/archive`, Structure `material/puzzle`, Experiment `material/microscope`, Analysis `material/calculator`, Report `material/clipboard-text`.

Reuse these exact bundled icons for the five workflow section headers in every interface's left navigation and for workflow page headings. Application, Python and Command Line share the ordered groups Start here, Project, Structure, Experiment, Analysis and Report. Their child instructions describe their own operations; code and command references remain additional interface-specific sections.

The pinned Zensical 0.0.73 `partials/nav-item.html` is retained verbatim except for the small icon-selection branch in `render_content`. It uses Zensical's own icon inclusion and sizing; there is no replacement typography or layout. The original license is retained under `third-party/zensical-LICENSE.md`.

Extend the existing group-icon rendering to Foundations, Analysis workflow, Start here and the main Physics groups. Keep leaf pages mostly text to preserve scanning and avoid decorating every navigation entry.
