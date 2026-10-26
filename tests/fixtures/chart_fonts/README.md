# Chart-font consistency

`ChartFonts.qml` instantiates the production chart components with private copies
of saved powder, single-crystal, scan and polynomial-correlation projects. It
compares the actual numeric tick text and both Qt Graphs per-axis font fields
(`axisXLabelFont`, `axisYLabelFont`) with the actual axis titles and the shared app
font. A generic theme `labelFont` alone does not prove either axis's font.

The inventory includes Pattern main, residual and Bragg panes; both single-crystal
F and squared-F scatters; Correlations row/column names and colour-bar values;
Evolution; Stacked; Map; and the Structure view's painted labels and axis letters.
Normally hidden/shared pane axes are exposed only to instantiate their real tick
text for this font comparison. Empty inventories fail. No replacement chart or
app-generated correctness golden supplies the expected font.

Each case checks the default, changes the one shared app font to another bundled
family and adds five pixels to its size, then restores it. This nontrivial
stimulus rejects a hardcoded default that only happens to match initially. The
Structure painter's two actual font properties are checked independently.

The native driver uses the normal test runner. `build.py` compiles only this same
Qt Quick Test witness, its passive helper and production module with the pinned
browser kit. The browser runner serves the sealed assets in one isolated pinned
Chromium context, passes the ordinary Qt Test input arguments to Qt's loader and
collects actual test output. The test host links Qt Test with Asyncify for its
blocking test waits, following the pinned kit's batch-test recipe.
Production, SDK/source, GUI recipes, probe/fixture
bytes and all served assets must match the build receipt. Set
`EDI_CHART_FONT_BROWSER_RECEIPT` to reuse a qualified `receipt.json`; stale or
changed bytes fail closed.

Run `python -m pytest tests/system/py/test_chart_fonts.py
tests/system/py/test_chart_fonts_browser.py`. Separate backend modules keep each
host's actual module setup cost independently measurable. The witness is formatting
acceptance, not a rendering-speed or physical-GPU measurement.
