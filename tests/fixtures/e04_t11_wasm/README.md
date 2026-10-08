# Native reference and browser invocation

`native.json` and `native-report.txt` were captured by `generate.py` on 2026-10-04 using the native
`python -m edi fit ... --dry --report machine --verbosity full`. The input is the committed
`docs/user/cli/pd-neut-cwl_lbco-hrpt_start-4/project`; its ordered path/content SHA-256 binds the input.
The fixture records the native extension's actual embedded build commit and binary SHA-256. The native
artifact was reused from the installed Linux edi environment with the Python package from its embedded
build commit, copied into isolated scratch, and never rebuilt or overwritten. This is a native-versus-wasm oracle, not a claim about CI or the current GUI build.
The new capture updates the input hash after edits to its README and metadata title. Fitted parameters
and reduced chi-square are unchanged; only elapsed times differ in the report.
The reference report's numeric formatting has ten significant digits; the declared relative comparison
bound is 1e-9, with a 1e-11 absolute floor. Every free fitted parameter, terminal status, convergence and
reduced chi-square belongs to the comparison; elapsed times and exact iteration histories do not.

Regenerate only with a native edi extension and a pinned Python environment:

```sh
python tests/fixtures/e04_t11_wasm/generate.py
```

The core numerical vehicles are the compiled wasm `crysta` CLI, separate for each thread kit. Set
`EDI_WASM_CLI_SINGLETHREAD` and `EDI_WASM_CLI_MULTITHREAD` to their generated JavaScript entrypoints, then
run the system Python gates. They copy the committed project before executing a fit.
`EDI_WASM_ZIP` selects the single delivered archive; its default location is `build/wasm/*.zip`.
These environment variables select real artifacts and never replace a result or a browser capability.

The browser checks are a dedicated task check, separate from the disabled desktop app tests:

```sh
node --experimental-websocket tests/system/manual/e04_t11_browser.mjs <extracted-webapp> singlethread <persistent-output> <chrome>
node --experimental-websocket tests/system/manual/e04_t11_browser.mjs <extracted-webapp> multithread <persistent-output> <chrome>
node --experimental-websocket tests/system/manual/e04_t11_browser.mjs <extracted-webapp> shim <persistent-output> <chrome>
```

The progress check follows the current status bar: the former `Fit iterationsN` label is now
`fitting · it N`. A Stop/Cancel control (including the Stop icon prefix) and a live iteration
label are both required in multithread and shim modes. Completed `it N` summaries, Success,
maximum-iteration settings, a control alone and an iteration label alone remain negative controls.
The observer records changed labels and newly inserted accessibility nodes before their first update.

File requests use real pointer input on the app's button instead of a synthetic click on its
accessibility element. The chooser event's backend node must be the file input captured from the
app's own request. Structure remains single-file, Experiment remains batch, and Load data is
single-file. The `--file-request-case=load-data` case creates an experiment and opens its actual
Load data control; the full `all` case includes it. The driver never opens the input directly.

Use Node with the WebSocket API (the shown flag enables it on Node 20) and pinned Chrome headless shell 146 with SwiftShader (the feasibility-check browser). The driver
records screenshots, the browser's own isolation flag, requested wasm URLs, runtime exceptions and
the fitting accessibility tree and progress-mutation history. It uses an isolated browser profile, serves under a subfolder,
blocks the isolation shim for the non-isolated single-thread case, supplies real headers for the
multi-thread case, and supplies no headers for the separate service-worker case. Browser controls
are located by their user-facing accessibility names, and clicks use real pointer input after the native page settles and its mirrored rectangle is mapped to the visible page.
No fixed delay substitutes for a ready page, completed fit, accepted file picker or completed download.
The driver expects a browser-visible Qt accessibility tree; if the kit does not expose the controls,
the driver activates Qt's documented screen-reader control first. A tree
that still lacks a table delegate is a harness limitation to adapt, not independent evidence of a rendering failure.

A passing browser run must open the bundled LBCO/HRPT example, show Structure and Experiment, run
Start fitting to the results popup, download the saved project, extract its project folder, and reopen that folder through
the browser directory picker. Captures still require a human view of the chart and structure drawing; the
accessibility labels alone do not prove rendered geometry. The initial frozen baselines had no wasm artifact. No live GUI
workflow success is claimed until the complete driver passes. Native numerical parity and the browser GUI flow
are different checks, and both are required before accepting the complete task.

Append `--startup-only` to run only initialization, real canvas, browser isolation and automatic kit
selection. This is gate 3 evidence only and never a substitute for the full gate 4 GUI workflow.
Qt accessibility activation: https://doc.qt.io/qt-6.10/wasm.html#accessibility-and-screen-readers.

Qt's accessibility mirror uses page-deck coordinates and can scroll the document when it focuses a hidden element. The harness maps the deck translation, waits for rendered page stability, and uses `focus({preventScroll:true})` to keep those hidden mirrors from moving the canvas. The real pointer input and Qt actions remain intact.

Qt omits the results popup table from the browser AX tree. Its modal visibility check uses the independent gui-components v0.9.1 `Colors.qml` tokens (`dialogBackground = contentBackground = #f4f4f4`, `chartPlotAreaBackground = #fff`), requires the broad overlay across chart and sidebar, and proves its disappearance on Escape. Done status and the captured popup remain separate witnesses. The component reference is commit `a573a9695e53a0807de197785e12f9facd06da05`.

The browser case disables Chromium's optional `FileSystemAccessLocal` feature and verifies that `showOpenFilePicker` is absent. This exercises Qt's actual Blob/anchor zip-download fallback, as used by browsers without the native picker API. A native save-picker path is not claimed: CDP's file-chooser interception aborts `showSaveFilePicker`. Folder reopening still uses the real intercepted directory picker.

Reopening closes the live project with the public reset action first and proves Structure, Experiment and
Analysis are disabled. The upload must enable Analysis from that empty state. A second real download must
retain every archive path and file byte, including project identity, README and the complete saved fit record;
the first saved chi square also matches the independent native CLI oracle. Only the value of the project's
`_metadata.last_modified` field is normalized, using the existing project round-trip convention.
Fresh chooser/download events are required for every action.

Append `--reopen-control=noop` or `--reopen-control=refuse` for deliberate negative controls: the former
prevents the real folder input's change handler, the latter supplies a folder whose project schema is invalid.
Each must fail specifically waiting for the formerly disabled Analysis tab to become enabled. A setup error
or unrelated fit failure is not a successful negative control. These controls never count as passing workflows.

The default full invocation also exercises all four request cases. For serial diagnostics, append
`--file-requests-only --file-request-case=overlap`, `replacement`, `cancel-structure` or `cancel-experiment`.
These scoped cases do not claim a complete gate 4 workflow. Append `--file-request-case=none` to run the
fit/save/reopen proof separately. Inputs come from `routing.py`; its copied scientific data are inputs,
not numerical reference results. Folder overlap holds actual browser Blob reads until both requests are
observably pending. Project replacement checks a real bundled example and the entire saved project tree
after the late upload completes. Cancel cases begin with a newly created empty project and require new
Structure or Experiment counts after the next picker. Every retry uses a fresh request.

The Structure case requires an actual one-file import and a single-file picker. A separate CDP escape
attempt supplied two files: Qt's single-file path read only the first, so requiring both reads would
misstate its contract. Chooser cardinality is independently guarded by the fast source seam gates,
including a mutant that switches Structure to a multiple-file request. Those gates also sweep every
QML receiver for request identity, terminal cancellation and initiating-project ownership. These checks
complement the real browser cases; neither source patterns nor unchanged empty-project labels alone
prove an asynchronous upload transition. Navigation requires the requested native tab to become selected.
