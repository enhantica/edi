# Windows clipping check

`job.yml` is a job fragment for the application workflow. It consumes the actual
`edi-webapp` artifact from the same workflow run, extracts it and runs the browser
actor on hosted Windows with Edge. It does not compile a substitute renderer.
The app build must retain the existing native control-geometry hook. Keep hardware
ANGLE enabled: forcing SwiftShader or the Qt software backend would change the
Windows rendering path under investigation. Record the browser version and GPU
renderer in the receipt. Run both single-thread and multi-thread web kits.

The six small cases described in shapes-app's `wasm/prototype` layout change are:
clipped rows, an antialiased clipped border, outer clip off, both clips on,
`layer.enabled`, and an opaque cover with clipping off. The referenced source
could not be fetched during authoring. These descriptions come from the task
brief; they are not claimed to be a transcription of the unavailable files.
Before the Windows result can count, the build job must include a test host of
these presets using the same pinned gui-components and the production render
configuration. It must also exercise the real Structure, Experiment and Analysis
tables, sidebar groups and a popup. Neither the presets alone nor a screenshot
of an empty viewport satisfies the application requirement.

For each case the browser captures a settled frame, moves a brightly coloured
child partly outside the inner clip and then across the enclosing clip, and
compares every pixel in the outside band with an empty background capture. It
also requires a positive inside-band witness. The cover case is the independent
pixel-reference control, and turning clips off must produce visible sentinel
pixels. Row scrolling, group collapse and popup close use trusted browser input;
the baseline is taken at the same layout and theme. Save before/after screenshots,
geometry, pixel counts, console errors and the GPU receipt. Repeat both themes.

The browser actor intentionally refuses without the preset host. A Linux result,
a disabled browser gate or an unevaluated job fragment is not a Windows green.
The conductor must arrange the producer hook and wire this fragment into the
actual required CI workflow before gate 2 can pass.
