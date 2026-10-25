# Scan renderer acceptance interface

The renderer choice described in [ADR-0041](../adrs/0041-scan-pattern-views.md)
has two separate inputs: what the user requested and what Qt can draw.
`Preferences.scanRenderer` is the requested machine setting: `auto`, `gpu` or
`software`, stored as `ScanViews/renderer`. Develop exposes it through
`preferences.scanRenderer`. The choice survives a complete host restart.

`GraphicsInfo.detected`, `api`, `renderer` and `software` describe detection.
The reference for detection is Qt's graphics API and, for OpenGL,
`GL_RENDERER`. Startup reporting and the Develop display can be checked with
no project open. A software OpenGL renderer such as llvmpipe is classified as
having no physical GPU.

## Requested choice and effective path

The Stacked line layer is `scanView.stacked.layer`. Its `gpu` property reports
the effective path. The named child `scanView.stacked.layer.gpuLines` is visible
and draws the scan when that path is enabled. Otherwise the child is hidden
and the software path draws the scan. The Map remains an image; it is not
required to draw its bands through this Stacked line child.

| Qt rendering setup | Automatic | GPU requested | Software requested |
| --- | --- | --- | --- |
| Hardware rendering through a supported graphics API | GPU lines | GPU lines | Software lines |
| OpenGL through llvmpipe or another software OpenGL renderer | Software lines | GPU lines through software OpenGL | Software lines |
| Qt Quick's **Software** graphics backend | Software lines | Software fallback; GPU drawing refused | Software lines |

llvmpipe OpenGL still supports the scene-graph shader path. A forced GPU
choice on this VM must therefore select that path, although the rasterisation
runs on the CPU. Qt Quick's separate Software backend cannot run that shader
path. A saved GPU request may remain saved there, but effective `gpu` must be
false and the GPU line child must stay hidden.

## Observing the active renderer

A scan must be open and loaded before checking the effective drawing path.
The native gate uses a private copy of the saved scan fixture, waits for every
file to load, and observes the plot after layout and rendering complete. It
checks the effective `gpu` state, the line child's visibility and its actual
rendered contribution. With GPU lines selected, the wrapper's painter must
produce no scan pixels. With software selected, the loaded scan must still
draw. These are drawing observations, not just the text of the preference.

The wrapper may inherit `QQuickPaintedItem` in either mode. Its superclass does
not identify the active renderer. The earlier gate used that inheritance test;
the adapted gate checks the effective path and rendered output instead. No
change of wrapper superclass is required, and no additional product-facing
interface is required beyond the setting, detection fields, effective flag and
named line child above.

The restart gate selects the preference through the real UI, closes that host,
then starts another host with the same private settings file. Each host opens
a scan before checking the active path. The current VM replay exercises
software **OpenGL**, not Qt Quick's Software backend; those are different
capability cases.


## Stacked placement and selectors

The placement contract is the relative rule in ADR-0041 §4, independent of
which renderer draws the lines. The Stacked toolbar controls are
`scanView.stacked.toolbar.offset` and `scanView.stacked.toolbar.height`.
Offset offers 0 through 100 percent in steps of ten, relative to one pattern's
own height. Height offers Fit, then 10 through 100 percent of the plot height.
The defaults are 10 percent offset and Fit. `Preferences.scanStackedOffset`
and `Preferences.scanStackedSize` keep these percentages; size zero means Fit.
The layer receives fractions through `offset` and `heightShare`.

Placement belongs to `scanView.stacked.layer`: `rowOf(dataset)` returns its
Stacked baseline, `peakOf(dataset)` its highest displayed line value, and
`patternHeight` the chosen height. These values use the Stacked vertical axis
coordinate system, with the unzoomed plot running from zero to one. They are
plot shares, not pixels or scan metadata values. Zoom and pan change the
visible axis interval without redefining the placement. The model's
`chart.scan.rowOf(dataset)` remains the scan-value coordinate used by Map;
for example a temperature row is not a Stacked baseline.

For N patterns in ascending row order, let i be the zero-based row rank and
let o be the offset percentage divided by 100. Fit chooses height
H = 1 / (1 + (N - 1) × o); a fixed h percent chooses H = h / 100.
The baseline is i × H × o. A pattern whose displayed maximum reaches its
normalisation maximum peaks at baseline + H. The independently generated
triangles used by the gate have that property. At zero offset every baseline
coincides; at full offset adjacent triangles touch without overlapping.
Fit puts the final peak at one. A fixed-height stack may extend beyond one;
existing zoom and pan reach those values without changing H.

The earlier gate compared the model's scan-value rows against Stacked
baselines. The adapted gate reads both baseline and peak from the layer and
compares them with the independent formulas in these axis coordinates. It
checks the unzoomed zero-to-one interval rather than deriving the placement
scale from whichever interval happens to be visible. The same layer baseline
is used when locating the Stacked highlight and pointer witnesses; Map keeps
its scan-value rows.

For each requested choice the gate searches the combobox model by exact text
equality after removing whitespace and ignoring case, then activates the
matching index and waits for layout and rendering. It does not assume a
particular index or use a suffix match: `0 %` and `100 %` remain distinct.
The closed display may include `offset:` or `height:`; those prefixes do not
change the model entries used for selection. This selector activation is a
placement check; it does not claim a pointer-driven dropdown interaction.
