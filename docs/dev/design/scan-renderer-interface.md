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
