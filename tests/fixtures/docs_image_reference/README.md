# Built documentation image reference

The observer loads the actual built HTML, CSS and scripts through an intercepted
filesystem transport. Chromium's host resolver is disabled and requests outside the local
site are aborted. It drives the site's real palette control and observes computed styles.
It does not manufacture dark sources or expected colours.

The hidden gate uses the WCAG 2.2 [relative luminance formula](https://www.w3.org/TR/WCAG22/#dfn-relative-luminance):
sRGB channels are linearized at 0.04045, then weighted by 0.2126, 0.7152 and 0.0722.
For the requested small lighter step, the border must have higher luminance than the page,
and `(border luminance + 0.05) / (page luminance + 0.05)` must lie from 1.01 through 1.25.
This interval is the gate's policy; WCAG supplies the formula.

The capture command publishes `assets/capture-manifest.json` in the built site, or the
runner supplies `EDI_DOCS_CAPTURE_MANIFEST`. The manifest has one nonempty `command` array
and an `images` array. Each image row gives `theme` (`light` or `dark`) and `path` relative
to the built site. It may include static images as well as app captures. Every resolved
content image must appear for its active theme, so all app images and the landing hero
are covered without a hand-maintained screenshot list.

`EDI_DOCS_SITE` selects an existing built site, defaulting to `website/_build`.
`EDI_DOCS_BROWSER_PYTHON` may select the installed Playwright interpreter. The observer
consumes an existing browser; it never downloads one. Scheme-specific sources must resolve
to distinct existing assets with distinct bytes. SVG GUI figures use their actual frame
stroke as the border; ordinary images use their computed border or frame border.
