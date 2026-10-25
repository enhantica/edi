# Scan view timings

How long the Stacked and Map views ([ADR-0041](../adrs/0041-scan-pattern-views.md)) take to redraw on the
324-file scan, what a 162-file sequential fit costs with "Every pattern" updates against "Adaptive"
([ADR-0029](../adrs/0029-following-a-scan-latest-finished-file.md)), and what one step of the Analysis slider costs
before and after a fit. The first table set is the baseline: the views as they drew before the GPU renderer, with
`QPainter` in `ScanLayer`.

## How the numbers are taken

The app's demo mode times them (`app/src/demo_driver.cpp`, the `perf-` steps):

```
edi_app --demo <dir> --demo-only perf-views    # the views on pd-neut-cwl_cosio-d20_scan-324f
edi_app --demo <dir> --demo-only perf-fit-     # the 162-file fit, four ways
edi_app --demo <dir> --demo-only perf-slider   # 30 slider steps on LBCO, before and after a fit
```

A view change is timed from the change to the swap of the first frame whose scene synchronisation followed it, so
the time holds the QML bindings, the drawing and the frame. Each view change runs from an idle window. The changes:

| Change | What it does |
| --- | --- |
| zoom | x range to its middle half and back |
| pan | a window half the x range wide, moved a fiftieth of the range per step |
| restyle | the colours reversed (Stacked) or the colour map reversed (Map) |
| select | another dataset shown |
| data | the rows placed again, by file and by scan value: every dataset's row moves |

A slider step moves the selected parameter (the LBCO cell length a) by 1 to 5 % of the slider's range and is timed to
the frame after its calculation ended ("shown"), and to the calculation's end ("calculated"). A fit is timed from its
start to its end being published with nothing calculating, after the demo checks every file was fitted.

`app/tools/scan_bench.cpp` (`pixi run -e app app-scan-bench`) compares the renderers outside the app, on the same
324 files, as one table.

Every number below is the median of three runs, each run's value the median of its samples. The raw rows are in
`scan-view-timings/`: each run's medians ([baseline](scan-view-timings/baseline/medians.tsv)), every timed change
([baseline](scan-view-timings/baseline/samples.tsv)) and when each run ran
([baseline](scan-view-timings/baseline/runs.tsv)).

**Machine.** A Linux VM, 64 vCPUs (Intel Xeon, Cascade Lake), 31 GB, no GPU. The app runs on X (Xwayland on headless
Weston) with Mesa llvmpipe drawing OpenGL on the CPU, as the UI test captures do, pinned to 8 vCPUs. Other work
shared the machine: the load average was 4 to 18 during the runs it was recorded for (not the view runs). A GPU draws much faster than llvmpipe, so these
times say how the views scale, not what a user with a GPU sees.

## Baseline

The views, 324 patterns of about 1 500 points each, a plot 1 000 pixels wide, in milliseconds:

| Change | Stacked median | Stacked p95 | Map median | Map p95 |
| --- | ---: | ---: | ---: | ---: |
| zoom | 114.6 | 131.0 | 57.0 | 70.1 |
| pan | 110.5 | 130.0 | 42.3 | 66.0 |
| restyle | 526.9 | 593.3 | 39.2 | 50.1 |
| select | 88.7 | 93.9 | 39.0 | 42.4 |
| data | 1 829.5 | 3 252.9 | 1 983.9 | 3 680.4 |

The 162-file fit, in seconds (three interleaved rounds):

| Tab shown | Every pattern | Adaptive | Every pattern / Adaptive |
| --- | ---: | ---: | ---: |
| Pattern | 53.85 (53.84–66.28) | 22.37 (18.71–23.88) | 2.41 |
| Stacked | 16.68 (16.55–18.36) | 17.13 (16.76–17.78) | 0.97 |

A slider step on LBCO, in milliseconds:

| | Before the fit | After the fit |
| --- | ---: | ---: |
| shown | 210.4 | 229.5 |
| calculated | 75.9 | 79.8 |

## Where the time goes

Read from Qt's render loop timing (`QT_LOGGING_RULES=qt.scenegraph.time.renderloop=true`) and the QML involved:

- **Drawing the Stacked view** happens in the scene synchronisation, which blocks the GUI thread: `ScanLayer::paint`
  reduces and strokes all 324 patterns every time, whatever changed. That is most of a zoom or pan frame.
- **A data change** costs over a second, mostly outside the drawing: the row labels' model is the rows' texts, so the
  Repeater deletes and makes again all 324 labels, each label's colour calls `colourOf`, and every row tick does too.
- **A restyle** reads `colourOf` for 324 labels and 324 ticks, and each call builds the colour table again.
- **A change of the shown dataset redraws every pattern**, although the drawing does not use it (the selection box
  is a separate item): a followed scan redraws all 324 patterns for every file.
- **"Every pattern" with the Pattern tab shown** waits about 0.2 s per file for the pattern chart to draw
  ([ADR-0029](../adrs/0029-following-a-scan-latest-finished-file.md) §8). With the Stacked tab shown nothing waits.
