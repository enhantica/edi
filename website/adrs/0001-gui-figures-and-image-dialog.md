# ADR-0001: GUI figures, compound highlights and image enlargement

Date: 2026-10-30
Status: implemented

## Context and prior art

The native screenshot importer and `gui-capture` renderer already pair PNGs with Qt layout metadata. The first renderer rounded and clipped the entire SVG, shrinking some figures through Zensical's `width: fit-content` default. It also omitted gallery annotations and only drew rectangles. The NOBUGS presentation's `markbox` paths instead join a selected tab to its panel in one stepped outline.

## Decision

All generated GUI figures fill the text column. The rounded clip applies only to the screenshot image; its frame and square highlight paths are separate siblings. The SVG allows visible overflow. Each highlight expands by 1.5 displayed CSS pixels on each side, recalculated from the viewBox scale by one ResizeObserver. Its outline remains two display pixels through a non-scaling stroke.

Every GUI switch uses native Zensical content tabs above the image. Tab labels contain names and GUI icons, without numbering or explanatory text. Each selected pane puts a short explanation immediately above its image. The same renderer handles highlight selection, the layout overview, main-view tabs and sidebar tabs; the older buttons below figures are removed. SVG titles retain view-specific descriptions for assistive technology and the enlarged dialog.

A ResizeObserver measures the natural height of each viewer's explanations at its current width and reserves their maximum height. Switching tabs therefore keeps the image in place, including on narrow screens and after resizing. Explanations can wrap without clipping. Hidden measurement clones are removed synchronously and excluded from accessibility.

Sidebar paths join the selected native tab and the body below the tab strip, using the capture's geometry. Missing or inconsistent tab geometry refuses generation. All sidebar views show this compound shape. The same rendering path serves the walkthrough, layout guide and enlarged view; it does not alter native images or metadata.

The introductory Main regions and Following the workflow diagrams use the Experiment capture. Their four area highlights are plain rectangles inset by two display pixels, rather than tab-and-panel paths. Following the workflow is a separate section immediately after Main regions. Its two arrows use the documentation page background colour and share one shaft/head width; the downward arrow is centered in the native sidebar bounds. Regular task and sidebar views retain expanded, compound highlights.

Clicking a screenshot opens a native HTML dialog filling the viewport, with the current highlights retained. It has an accessible title, visible Close button, Escape handling, modal focus containment and focus return. The image link remains a fallback without JavaScript and supports ordinary modified clicks. The dialog uses the site's theme colors. Keyboard behavior follows the [WAI modal dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/).

The close check waits for the native dialog's queued close event to restore focus and scroll, rather than assuming that removing the `open` attribute already completed that event. A faster hosted Chromium run exposed this timing difference from local Chromium.

The Application introduction contains one **Application layout** page before one **Example refinement** page. The former merges the workspace overview and every enabled sidebar view; the latter contains the complete Y2O3/SPODI workflow. The old routes redirect to these pages.

## Verification

Build validation checks the native capture bundle and generated links, including SVG image links. Browser checks verify uniform column widths, screenshot-only clipping, square unclipped outlines, display-pixel padding after resizing, compound selected-tab paths, modal sizing/focus/close behavior, theme inheritance and the consolidated navigation and redirects. Check desktop and narrow mobile viewports.

## Native tab viewers and GUI icon parity

The layout guide uses Zensical's native content tabs: one viewer per workflow page, with an overview, enabled main views and enabled sidebar views. A Lucide monitor and a Material dock-right icon distinguish workspace tabs from sidebar tabs; hidden text gives each selector an explicit accessible prefix. Home precedes Project and has one overview because it has no tabbed panels. Switching tabs changes the image and its geometry as one pane. This replaces the repeated vertical gallery and its two overlay-choice buttons.

Main views use captured native tab labels and bounds. Their stepped outline joins the selected main-view tab to its workspace, just as the existing sidebar path joins a sidebar tab to its panel. Secondary main views require an actual capture whose action record selects that tab; missing captures refuse generation. Overview titles describe the whole page and do not inherit the source screenshot's sidebar name.

Highlight selectors use the actual captured Font Awesome icon name, mapped to the same Font Awesome 5 solid face bundled by the GUI. The font and its license are retained, and the glyph map is derived from that exact face. Controls with no GUI icon remain text-only. Figures always use their captured display labels, with explicit human-written explanations where useful.

Image URLs include their image hash. The generated GUI CSS/JavaScript URLs include a hash of those assets, so frequent preview deployments do not mix current HTML with cached older styles or code. A full browser exercise passed the native tabs, mode switching, fixed column sizing and modal behavior at desktop and mobile widths. Local browser scratch used an isolated RAM-backed directory after the nearly full VM disk caused a Chromium page crash; this was a test-environment capacity issue.

2026-10-31 clarification: each app area owns a restrained highlight colour: blue navigation, teal main view, amber sidebar, violet status bar. Classify every generated highlight from its captured native region/bounds; use the same semantic colours in the walkthrough, all guide/tab views, layout overview and enlarged dialog. The layout selectors include matching coloured area icons, with text/position retained so colour is never the only cue. Fills remain light enough to read the screenshot controls. The workflow-direction arrows use the current documentation background colour, partially transparent so the original controls remain visible, instead of blue. The prior single amber overlay is superseded.

2026-10-31 selector refinement: main-view and sidebar selector icons inherit the same teal/amber area colours as their highlights while tab text stays neutral. The Main regions selector uses dock-top, monitor, dock-right and dock-bottom area icons instead of generic square swatches. Keep those area symbols distinct from workflow/category icons in page navigation.
