# Scan renderer acceptance interface

The renderer choice described in [ADR-0041](../adrs/0041-scan-pattern-views.md)
has two separate inputs: what the user requested and what Qt can draw.
`Preferences.scanRenderer` is the requested machine setting: `auto`, `gpu` or
`software`, stored as `ScanViews/renderer`. Develop exposes it through
`preferences.scanRenderer`. The choice survives a complete host restart.

`RenderingInfo.detected`, `api`, `renderer` and `software` describe detection.
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

The placement contract extends the Stacked view in ADR-0041 with the relative
offset and height choices, independent of which renderer draws the lines. The Stacked toolbar controls are
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


## Highlight ink and the selected row label

Both views use `Preferences.chartHighlightSelected` and
`Preferences.chartFadedOpacity` (0.3), exposed by the active layer as
`highlight` and `faded`. The real button is
`scanView.<mode>.toolbar.highlight`. Turning it off restores every dataset's
full colour; turning it on keeps the selected dataset on top and fades the
others. `SelectedPatternBox` and its runtime instance are retired.

The ink observation captures the complete actor surface after rendering,
before and after clicking that button. Sample points in
`scanView.<mode>.layer` coordinates are mapped into that surface, then scaled
to image pixels. Qt Test's item-sized window capture was previously treated
as a layer-local image, so a toolbar and plot margin displaced the witnesses.
The adapted observation maps the actual layer position explicitly. For the independent triangle with knots (10, 0),
(40, 255), (80, 0), Stacked samples x = 30 at baseline plus two thirds of its
height. Map samples x = 40 at each dataset's scan-value row. The gate searches
a small vertical neighbourhood for actual colour different from
`chart.colors.chartBackground`, then compares that same pixel with highlight
on and off. The selected dataset keeps its full colour and the other two
approach the shared fade fraction. A separate fully overlapping Stacked
witness checks the selected middle dataset's approved palette colour on top.
Preferences and layer flags alone do not prove visible ink.

Previously the Stacked ink witness sampled each triangle's maximum at
x = 40. Fit places the last maximum at the plot boundary, where clipping can
remove its ink. The adapted witness uses the known interior line segment and mapped capture;
its expected position still follows the independent triangle and the placement
contract above. Pointer hover and clicking also target that interior segment,
rather than a baseline at an unrelated x coordinate. The named tooltip
`scanView.<mode>.hover` must name the targeted dataset, and clicking must select
it.

With highlight off, the selected label is the **visible**
`scanView.<mode>.rowLabel.<dataset>` IconLine. The gate reads its nonempty
`segments` text entry with `bold: true` and checks `textColor` against the theme
accent. It also observes the corresponding visible text child: its family is
the loaded PT Sans bold family, its style is `Bold`, and its actual colour
reaches the theme accent. An inactive label with the same name is not the
selection marker. On a Map using a numeric scan-value axis, the selected
IconLine sits inside the plot's left edge even though ordinary row labels
are absent.

The label and its text must also have positive opacity. The earlier label witness required the text child's `font.bold` flag.
IconLine selects its bold font through the loaded family and `styleName`, so
that flag does not describe the chosen font face. The adapted witness checks
the segment, visible font face and rendered text colour together; a bold
segment alone is insufficient.

## Structure view capability

Structure availability follows Qt Quick 3D's supported graphics API, not the
scan renderer preference or the presence of a physical GPU. On the real
Structure page, `structure.view.view3d` must be a live, visible View3D when Qt
reports OpenGL, Direct3D, Vulkan or Metal, and
`structure.view.unavailable` must be hidden. Software OpenGL such as llvmpipe
also supports this path. With Qt Quick's separate Software backend, the
View3D must be absent and the unavailable message visible. The gate opens a
private crystal project, waits for nonempty geometry and a rendered frame,
and compares these observations with the native Qt API reference in separate
processes for the two capability cases.

The existing drawn Structure suite reaches real View3D picking and should
fail if the 3D item disappears, but its `app-test-3d` route is manual. The
ordinary rendering-setup gates previously visited startup, Preferences and
scan plots, without visiting the Structure page. The system capability pair
now exercises both the active 3D item and the fallback message directly.
A software-OpenGL replay is correctness evidence for the supported API path;
it is not a physical-GPU performance measurement or a browser replay.

The [scan-update acceptance interface](scan-update-interface.md) covers both
Every-pattern choices, the catch-up timing bound, stable parameter y ranges
and first-group sidebar defaults. The rendering-detection singleton is now
named `RenderingInfo`; its earlier name `GraphicsInfo` shadowed Qt Quick's
attached graphics API type used by the Structure view.


## Toolbar centre and plot hover placement

Every toolbar line on Experiment and Analysis Pattern, Stacked and Map shares
the horizontal centre of the visible `mainArea.blocks` dataset selector line.
The reference is the entire selector row, including its navigation buttons,
not the plot area offset by axis or row labels. The gate previously compared
with the plot centre. It now maps both lines into common chart coordinates
and checks each row within one logical pixel. Historical numeric case tags
now select an actual wide, middle or supported-minimum application width;
the gate no longer detaches a narrow chart beneath an unchanged wider selector.
Wrapping and whole-control containment remain checked. If the comboboxes'
combined width exceeds the available row, multiple combobox rows are required
above the button row.

The named `scanView.<mode>.hover` tooltip follows the actual pointer inside
the plot. Its complete background stays inside the plot at interior and edge
positions, its nearest edge lies within two standard font sizes of the pointer,
and it intersects no toolbar control. Geometry is observed on the rendered
popup background, not inferred from a requested x/y value. The text must name
the independently targeted dataset. Its actual background and visible text
use the app's shared tooltip background, foreground and font; the border and
shadow token must also match. These observations cover both Stacked and Map.

The centre witness waits for stable mapped positions and sizes of the selector,
chart and controls across successive event-loop samples. One completed frame
does not prove that the selector’s resize animation has finished. Seq 19 found
that the previous one-frame witness read a moving selector; the settled witness
retains the one-logical-pixel tolerance.


## Stacked line quality against Pattern

The reference is the actual Pattern chart's Qt Graphs measured-line rendering,
not the retired painter or an existing capture. A paired capture loads the same
independent dense polyline into Pattern and Stacked: a sharp triangular peak and
a narrow peak whose feet straddle device-pixel columns. More than 4096 samples
exercise reduction, rather than a sparse path that can bypass it. The matrix is
DPR 1 and 2, each with effective GPU and software Stacked drawing. The approved
measured palette assignment remains the colour reference.

Both actual plots have equal physical grids and equal data ranges. Only their
line subtrees are captured over white. The triangular join witness uses opacity
0.3, exposing overlapping joins; the narrow reduction witness is opaque, so
coverage of its closely spaced arms measures geometry without opacity stacking.
The tolerances are engineering allowances for different antialiasing kernels:

- Integrated stroke coverage and local cross-sections sampled at seven positions
  along the segments (outside the vertex disk) differ by at most
  15 percent from Pattern; the local checks also reject uneven thickness.
- Absolute coverage error, after a half-physical-pixel smoothing kernel, is at
  most 12 percent of Pattern's integrated coverage. No logical-pixel rescaling
  or registration is allowed, including at DPR 2.
- Every reference core pixel has candidate ink within one physical pixel; the
  same rule applies inside a five-logical-pixel disk at the sharp vertex. This
  permits antialiasing edge placement, not a missing segment or vertex notch.
- Maximum opacity at the vertex exceeds Pattern's maximum there by at most
  0.08. Comparing maxima within the vertex area avoids treating different edge
  coverage as doubled alpha.

The receipt retains both PNGs, actual Qt API/renderer, input and reference point
counts, all metric values, and eight elapsed frame-delivery samples for each
path. These elapsed samples include event delivery and the test's frame wait;
they are not isolated GPU timings or quiet-machine performance claims.
Controlled thinning, a gap, excessive alpha and a physical displacement of the
actual Pattern reference must each fail the comparator; identity must pass.

## Legend visibility and range preference

Experiment and Analysis Pattern and single-crystal charts use the actual
`chart.legend` or `singleCrystal.legend`. Every `chart.legend.entry` has a curve
`key`, `hidden` state and drawn name and symbol. Clicking either part toggles the
corresponding rendered curve, not just the legend metadata. Powder series have
no drawable points while hidden; single-crystal reflection layers become
invisible. Both name and symbol paint the chart's disabled foreground colour.
A real hover uses the shared app tooltip and says exactly `Click to hide` or
`Click to show`.

`preferences.hiddenRange` offers `Keep the y range` (default, stored `keep`) and
`Fit the range to visible curves` (stored `fit`), backed by
`Preferences.chartHiddenRange` in machine settings. The former keeps both axis
endpoints on hide and show; a later reset still counts hidden curves. The latter
fits the visible data once on hide or show, and a later reset continues to leave
hidden curves out. Showing everything restores the full-data fitted range.
Visibility remains independent per chart across navigation in the running app
and resets when another project opens.

Before the amended owner record, the legend rule would have required an
unchanged range for every click. The gates now separate the default keep rule
from visible-only fits and test both actual preference choices and persistence.


## Supported minimum and undersize overlay

ADR-0017 section 2 fixes the supported app area at 1024 by 640 logical pixels.
`AppSizes.minimumAppWidth` and `minimumAppHeight` supply both the native window's
`minimumWidth`/`minimumHeight` and the undersize predicate. The inherited GUI
library's minimum-size tokens are not the reference for this app-specific size.

The window owns the named Rectangle `app.tooSmall`, visually parented to
`Overlay.overlay`, above the entire application, including dialogs. It is visible
when the actual window width is below 1024 **or** its height is below 640, and
hidden exactly at both minima. Its `EmptyStateLabel` child is named
`app.tooSmall.text`, says `Increase the window size`, and is centred in the
complete window area. It uses the same font as the ordinary empty-view label;
the cover uses the shared empty-view background colour.

The acceptance observer finds these names from the actual window's QObject
hierarchy, checks their visual ancestry in `Overlay.overlay`, and captures the
window's complete visual root. An application content-item-only text traversal
can miss an overlay sibling. Discovering controls beneath the cover does not
mean they are exposed: the observer checks that the cover fills and paints the
whole window and that a real pointer click cannot activate a covered control.
The same control must work after the area grows again.

The cover leaves the existing application underneath alive. Crossing either
boundary and returning to the minimum retains the project and page instances,
page and chart tabs, selected dataset and existing scroll positions. The native
actor temporarily relaxes the window-manager minimum properties to exercise the
same production predicate at browser-reachable sizes; this is not a claim of a
WebAssembly runtime capture. Native minimum publication is checked separately.

Before this adaptation, the gate searched only `win.contentItem` and required
underlying controls to disappear. It now observes the named overlay, its actual
pixels and pointer interception while requiring the underlying state to survive.
