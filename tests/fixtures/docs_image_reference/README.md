# Built documentation image reference

The observer loads the actual built HTML, CSS and scripts through an intercepted
filesystem transport. Chromium's host resolver is disabled and requests outside the local
site are aborted. It drives the site's real palette control and observes computed styles.
It does not manufacture dark sources or expected colours.

The hidden gate uses the WCAG 2.2 [relative luminance formula](https://www.w3.org/TR/WCAG22/#dfn-relative-luminance):
sRGB channels are linearized at 0.04045, then weighted by 0.2126, 0.7152 and 0.0722.
The border has lower luminance than the white page in light mode and higher luminance than
the page in dark mode. The ratio `(brighter luminance + 0.05) / (darker luminance + 0.05)`
must lie from 1.01 through 1.25 in both schemes.
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

Logical slots are collected before visibility filtering, including slots hidden in every
scheme and tab state. The landing preview is identified by its semantic container, never
an asset filename. Every active ordinary or SVG image target must decode in the browser.
The independent tiny page accepts an ordinary-named hero and rejects an entirely hidden
slot or an existing but undecodable SVG target through that same browser witness.

The execution gate requires one `OUTPUT` token in the declared command. It copies committed
source into a disposable workspace, deletes old app capture images there, runs the command
and checks the newly produced app images against the required built-site inventory. Static
illustrations are excluded from this producer comparison. The existing prebuilt app can be
provided through `EDI_DOCS_APP`; the gate never builds it. The capture route's environment,
display and recorded/local input sources must already be provisioned. Captures may be costly;
select this execution node explicitly for its qualification run. No automatic skip replaces it.
Executable controls prove missing commands, failing commands and missing new output fail even
with a fully populated old publication tree.

Fresh output qualification additionally uses libpng's complete simplified-read API,
with the public `png_image` declarations from the installed `png.h`. Browser image
decoding can recover missing pixels, so it is insufficient for these new artifacts.
The checksum-correct incomplete-pixel control passes the old container checker and
must fail the full decoder, alongside the header-truncated control. Decoding is
sequential; the fixture caps one RGBA allocation at 256 MiB, above the declared app
capture viewport. `EDI_DOCS_PNG_LIBRARY` can select an already provisioned decoder.
