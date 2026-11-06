# ADR-0002: Shared workflow navigation and icons

Date: 2026-10-30
Status: implemented; icon choices superseded by ADR-0014

The prior library guide declares Material Design Icons in `diffraction-lib/docs/docs/user-guide/analysis-workflow/`: Project `material/archive`, Structure `material/puzzle`, Experiment `material/microscope`, Analysis `material/calculator`, Report `material/clipboard-text`.

Reuse these exact bundled icons for the five workflow section headers in every interface's left navigation and for workflow page headings. Application, Python and Command Line share the ordered groups Start here, Project, Structure, Experiment, Analysis and Report. Their child instructions describe their own operations; code and command references remain additional interface-specific sections.

The pinned Zensical 0.0.73 `partials/nav-item.html` is retained verbatim except for the small icon-selection branch in `render_content`. It uses Zensical's own icon inclusion and sizing; there is no replacement typography or layout. The original license is retained under `third-party/zensical-LICENSE.md`.

Extend the existing group-icon rendering to Foundations, Analysis workflow, Start here and the main Physics groups. Keep leaf pages mostly text to preserve scanning and avoid decorating every navigation entry.

## Interface menus follow the User guide — 2026-11-06

Application, Python and Command Line now use the User guide's shape, replacing the flat ordered groups above. Start here is a clickable section with no icon whose page is the interface entry (`/application/`, `/python/`, `/cli/`), and its setup pages carry icons through front matter. Analysis workflow is a clickable section with its own overview page and the five stages as children: a stage with one page is a direct link, and a stage with several pages expands. Examples is the last group. Each interface has exactly these three groups; the Python and Command Line reference pages sit last in Start here, as lookup pages sit in Foundations.

A section's index row takes its icon from the section title, not the page title, so the Application page does not put an icon on Start here. Page files keep their paths apart from the section indexes, which keeps every URL unchanged. `_check_navigation` in `build.py` enforces this shape.

Each interface entry page is titled Start here, matching its menu entry the way Foundations does in the User guide; the top navigation and breadcrumb name the interface. Because three pages share that title, front matter `html_title` keeps browser tabs and `llms.txt` specific, for example "Command Line: Start here".
