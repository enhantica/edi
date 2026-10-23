# Hosted Windows clipping job

Windows clipping is deferred because the rendering fault has not been reproduced.
The actor, job fragment and producer-refusal module require explicit invocation. The preserved
checks are in `tests/deferred/py/windows_clipping_job.py`, outside automatic
collection. Restore them with a reproducible Windows case and a working producer.


`job.yml` is the job to add beside `app-wasm` in the application workflow. The
existing Linux `app-wasm` job builds both Qt kits with
`pixi run -e app --skip-deps wasm-build` and uploads the directory
`build/wasm/site` as `edi-webapp`. Download that artifact directly into the site's
folder. Do not expand a zip: the uploaded directory contains `build.json`, the
start page and the two content-addressed kit folders.

The consumer is `windows-web-clipping` on `windows-2025`. It needs no Windows
compiler or Pixi environment. It needs Node 22.23.2, Python 3.13, the locked
Playwright driver from `tests/fixtures/web_parallel`, and the image's installed
Microsoft Edge. It serves localhost with COOP/COEP headers so the multithread kit
can use shared memory. The actor verifies isolation, the requested kit, the
browser version and the actual WebGL renderer. It runs headed Edge through
Windows ANGLE/D3D11; it does not force SwiftShader or Qt's software renderer. A
hosted runner may report a software Windows adapter: record that fact rather
than calling it a hardware-GPU result. If WebGL2 cannot start, the job fails.

## Producer work required before the job can pass

The ordinary site currently has `ediControlGeometry` and `ediOpenExample` but no
clipping fixture. The producer must compile a test-only host into **both** kits,
using the same app module, pinned gui-components, compiler options and rendering
backend as the normal app. Resolve the shared-cell pin from `cmake/EdiGuiBase.cmake`. Record that full pin, edi commit, source hashes of the host
and preset QML, Qt kit and Emscripten version in `clipping-host.json` at the site
root. Preserve the production entry points and pages. Do not provide a separate
HTML/CSS imitation of QML, or a renderer with clipping implemented by the host.

Build integration: add the fixture's QML to `edi_app_module`'s `QML_FILES`, its
native observation bridge to `SOURCES`, and install that bridge immediately
after `install_web_page_hooks(engine)` in a temporary source snapshot. Use the
existing `tools/ci/wasm-build.sh` kit configuration and `wasm-pack.sh` packing
recipe against that snapshot. The host must be disabled on a normal start and
activate only for `?acceptance=clipping`. Publish the instrumented site's two
kits together as this run's `edi-webapp` artifact. That producer integration is
implementation work still required; this test job refuses a normal artifact
without its host manifest. Wiring the consumer alone cannot produce a green.

The host exposes asynchronous
`ediClippingAcceptance(scenario, theme, phase)`. Preparation may open the actual
example and switch the actual page, theme and sidebar groups. Observation must
read native QQuickItem scene geometry and actual visibility/contentY; it must
not return desired geometry or perform the action being tested. Its contract:

- `background`: return a settled, empty-content reference of the same scene,
  before the sentinel content has ever been drawn; unrelated layout is fixed.
- `prepare`: draw the case, await actual Qt frame swaps, and return `clip`
  (`x,y,width,height`), `region` (the full possible overflowing child bounds,
  including antialiasing), and `action` (trusted click or wheel coordinates).
- `read`: observe the completed real input action, await actual Qt frame swaps,
  and return `completed: true` only after contentY, expanded state or popup
  visibility proves that action occurred. It cannot hide or move items itself.
  The actor checks the actual `contentHeight` and before/after `contentY`,
  `expanded`, and `popupVisible` fields as appropriate. Presets also expose
  native `innerClip`, `outerClip`, `coverVisible`, `layerEnabled` and
  `antialiasing` properties; their names alone never prove the preset ran.

The region includes all possible escaped child pixels, rather than an arbitrary
strip that could miss a distant overflow. For collapse and close, take the
background at the resulting layout with the content never created, then restore
the identical layout for the visible witness. Do not take the background after
the close: that could bless a stale frame as its own reference. The input target
and unrelated animated content must not add pixels outside the reference mask.

## Cases and independent controls

The first argument to `ediClippingAcceptance(scenario, theme, phase)` is exactly
one of the following ids. Each id receives all three phases above, with `theme`
`light` or `dark`, once per kit. Reject unknown ids; do not silently use a default.

| Scenario id | Production scene or preset | Trusted action and required observation |
| --- | --- | --- |
| `rows` | Saturated rows crossing nested bounds | Wheel; changing `contentY`, `contentHeight` larger than the viewport |
| `antialiased-border` | Clipped antialiased border | Preset action; `antialiasing: true` |
| `outer-off` | Inner clip with outer clipping disabled | Preset action; `outerClip: false`, pixels escape the outer bounds |
| `both-clips` | Both nested clips enabled | Preset action; `innerClip: true`, `outerClip: true` |
| `layer` | Clipped content in a layer | Preset action; `layerEnabled: true` |
| `cover` | Opaque cover over unclipped sentinel | Preset action; `outerClip: false`, `coverVisible: true`, no escaped ink |
| `structure-table` | Actual populated Structure table | Wheel; `contentY` changes, enough rows to overflow |
| `experiment-table` | Actual populated Experiment table | Wheel; `contentY` changes, enough rows to overflow |
| `analysis-table` | Actual populated Analysis table | Wheel; `contentY` changes, enough rows to overflow |
| `sidebar-collapse` | Actual expanded sidebar group | Click; `expanded` changes from true to false |
| `popup-close` | Actual open QML popup | Click; `popupVisible` changes from true to false |

`prepare.action` has `kind` (`wheel` or `click`), finite `x` and `y`, and, for
wheel input, nonzero `dy`. Preset actions must still be real input with a completed
native observation; the host does not mutate state during `read`.


Exercise every combination of the two kits and light/dark themes. The six
minimal presets named in the task brief are clipped rows, an antialiased clipped
border, outer clipping off, both clips on, `layer.enabled`, and an opaque cover
with clipping off. Give each a saturated sentinel crossing both the inner and
outer native bounds. Copy the upstream shapes-app preset source when available,
record its revision, and retain the preset source hashes in the artifact. The
upstream source was unavailable during initial authoring; the case names alone
are not a claim that these presets have already been reproduced.

Also use the production Structure, Experiment and Analysis tables, an actual
collapsible sidebar group, and a real popup. Use a populated project, scroll a
row completely out of view, collapse expanded content, and close the popup with
trusted browser input. A table containing no rows cannot supply a witness.
The producer must retain enough rows to overflow each table in both themes.

For every case save background, visible and post-action screenshots; native
geometry; actual post-action state; browser/GPU and build identities; pixel
counts; console errors. A positive inside witness proves real content was
visible before the action. Every pixel outside the allowed clip, within all
possible overflowing bounds, must match the independent empty reference. For a
closed popup or collapsed group the vacated area must also match that reference.
Turning outer clipping off must produce outside sentinel pixels; the opaque
cover must remove them without enabling clipping. Those controls must fail if
the pixel comparison is disabled or the sentinel is never drawn.

The job must become required at the exact app head. `app-wasm` currently skips
pull requests, so the dependent Windows job also skips those events: either run
both jobs on the accepted head by dispatch/main, or change the producer's event
policy before requiring this on pull requests. A skipped job, a Linux actor, a
job fragment, or a missing fixture host supplies no Windows acceptance evidence.

The consumer must run `check_receipt.py` after the browser actor. It requires the complete case matrix, exact app head, actual Windows renderer, native and QML source identities and the retained screenshot hashes. The controls in `tests/deferred/py/windows_clipping_job.py` do not supply a Windows rendering result. A missing producer or installed workflow remains red.
