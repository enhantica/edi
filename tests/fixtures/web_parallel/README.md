# Web parallel acceptance vehicles

`contract.json` records the owner's unchanged native baseline and the task's
route and speed requirements. The native scientific captures come from edi's
unchanged native CLI, linked to the declared crysta SDK. Regenerate with:

```
OMP_NUM_THREADS=4 python -m tests.fixtures.web_parallel.generate \
  .pixi/envs/default/bin/python --edi --producer '<edi and linked SDK source shas>'
```

The browser corpus is LBCO HRPT start 4 and NCAF WISH five-bank start 5. Captures
include fitted parameters, fit scalars and every measured/calculated pattern
operand. The existing ADR-0057 cross-platform relative tolerance 1e-9 and
absolute tolerance 1e-11 apply; the owner's rounded numbers use half a hundredth.
The original input baseline is chi-square 649.33; the native capture converges
in five iterations to chi-square 9.497535494 and Rwp 0.07694458606.

Run the browser matrix against the delivered site on the pinned headless browser:

```
node --experimental-websocket tests/system/manual/web_parallel.mjs \
  <unpacked-site> <persistent-output> <pinned-chrome>
```

This executes both corpus cases on the singlethread, direct-isolation and
service-worker routes through the existing browser driver. Every route checks
its kit, isolation, SharedArrayBuffer, Develop diagnostics and native numerical
reference. It records the NCAF fit durations and requires the multithread kit to
be at least 1.4 times faster on the same browser executable and runner exposing
at least four cores. Only this speed gate uses a duration threshold.

The diagnostics text contract adds `Engine backend`, `Engine workers`, and
`WebAssembly SIMD`, retaining the existing ideal-thread, OpenMP-team and browser
core labels. The isolated kits report a std::thread pool with multiple workers
and SIMD enabled; the singlethread kit reports serial, one worker and SIMD off.

The separate executed-body witness lives in crysta's visible
`tests/fixtures/web_parallel` builders and hidden browser driver. Build it from
the same core source as the app, with the same Emscripten thread and SIMD options,
and run that browser driver as well. Configuration counts cannot replace this
execution witness. The witness driver accepts the optional last argument
`serial-dispatch` or `backend-off` for the corresponding observer build. These
control runs must complete and record executed serial bodies with the failed
rendezvous; a startup failure does not count as refusal. The serial-dispatch
control also retains configured capacity four and advertised chunks sixteen. The native performance gate remains the existing crysta A/B
harness (`tools/bench/ab_perf.py`); no new pinned duration is introduced.
