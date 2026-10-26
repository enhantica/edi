# Chart-font consistency

`ChartFonts.qml` instantiates the production chart components with private copies
of saved powder, single-crystal, scan and polynomial-correlation projects. It
compares the actual numeric tick text and both Qt Graphs per-axis font fields
(`axisXLabelFont`, `axisYLabelFont`) with the actual axis titles and the shared app
font. A generic theme `labelFont` alone does not prove either axis's font.

The inventory includes Pattern main, residual and Bragg panes; both single-crystal
F and squared-F scatters; Correlations row/column names and colour-bar values;
Evolution; Stacked; Map; and the Structure view's painted labels and axis letters.
Normally hidden/shared Pattern pane axes are exposed only to instantiate their
real tick text for this font comparison. Scan charts retain their normal axis
visibility; their actual shown dataset row names are checked alongside numeric
ticks, titles and both per-axis theme fonts. Empty inventories fail. No replacement chart or
app-generated correctness golden supplies the expected font.

Each case checks the default, changes the one shared app font to another bundled
family and adds five pixels to its size, then restores it. This nontrivial
stimulus rejects a hardcoded default that only happens to match initially. The
Structure painter's two actual font properties are checked independently.

The native driver uses the normal Qt Quick Test runner. Its compiled helper
and QML witness must be from matching inputs; an explicit shared-inventory API
check reports an outdated helper before any chart case attempts its method. The web producer uses
an ordinary nonblocking Qt application loop with the production module; a small
Timer samples ready chart objects rather than suspending the browser's main
thread. Both read the same declared inventory. The browser records actual font
fields for all three phases; hidden Python assertions compare those observations
with its actual axis titles and shared app font. The passive helper only copies
saved inputs, traverses actual objects and publishes the observation.

The browser runner serves sealed assets in pinned Chromium, with a fresh page
and preferences store for each chart. Each actor selects one declared input
through the URL; a missing or extra case fails.
Production, SDK/source, GUI recipes, probe/data bytes and all served assets must
match the receipt. Set `EDI_CHART_FONT_BROWSER_RECEIPT` to reuse a qualified
`receipt.json`; stale or changed bytes fail closed. Explicit root-relative
resource aliases keep saved inputs independent of aliases set by earlier app
example bundles.

Run `python -m pytest tests/system/py/test_chart_fonts.py
tests/system/py/test_chart_fonts_browser.py`. Separate backend modules keep each
host's actual module setup cost independently measurable. The witness is formatting
acceptance, not a rendering-speed or physical-GPU measurement.
