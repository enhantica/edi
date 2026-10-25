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

**Machine: the no-GPU case.** A Linux VM, 64 vCPUs (Intel Xeon, Cascade Lake), 31 GB, no GPU. The app runs on X
(Xwayland on headless Weston) with Mesa llvmpipe drawing OpenGL on the CPU, as the UI test captures do, pinned to 8
vCPUs. A user without a GPU sees this case, so the redraw target holds here as well as on a GPU. Other work
shared the machine: the load average was 4 to 18 during the runs it was recorded for (not the view runs). GPU
numbers are taken where a GPU exists (the macOS CI runner).

## Baseline, no GPU

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

## The renderers compared, no GPU

`scan_bench` on the same 324 patterns, plot 1 000 columns wide, each change timed to its frame as above, 30 changes
of each kind per run. Candidates: **a**, Qt Graphs, a `LineSeries` per pattern fed its reduced trace in one
`replace()`; **b**, `ScanLines`, a scene-graph node of quads per 64 patterns, its shader placing each pattern's line,
so an offset, height or colour change gives the shader new values and no new vertices; **p**, the way the view draws
today, every pattern stroked with `QPainter` into the item's image on each change. Medians of three runs, in
milliseconds ([rows](scan-view-timings/renderers.tsv)):

| Candidate | Width | First | x range | Restyle | Offset |
| --- | ---: | ---: | ---: | ---: | ---: |
| a, Qt Graphs | 2 px | 2 853 | 2 151 | no frame | 2 156 |
| a, Qt Graphs (one run) | 1 px | 2 496 | 2 486 | no frame | 2 382 |
| b, ScanLines | 2 px | 489 | 358 | 258 | 341 |
| b, ScanLines | 1 px | 576 | 479 | 262 | 240 |
| p, QPainter | 2 px | 3 174 | 3 090 | 3 159 | 2 983 |
| p, QPainter | 1 px | 134 | 124 | 128 | 126 |

"x range" is a new x range, every trace reduced again (a zoom or pan step); reducing the 324 traces takes 6 to 8 ms
of it. "No frame": after a colour change alone, Qt Graphs drew no frame within 10 s.

- Qt Graphs misses the 100 ms target by twenty times on every change.
- ScanLines costs about the same at either width: llvmpipe's cost is its vertices (four per segment, about 1.9
  million), not its pixels. A first build with one node per pattern took about 500 ms for a restyle; one node per 64
  patterns took it to about 260 ms.
- QPainter strokes a 1 px antialiased line on a fast path and a 2 px one through its general stroker, 25 times
  slower. At 324 rows in about 600 pixels the view draws 1 px lines (ADR-0041 §4), so without a GPU the painter is
  today's fastest path, at about 125 ms.
- None meets 100 ms without a GPU yet.

## The renderers compared, with a GPU

The same benchmark on an Apple M2 (macOS, Metal through Qt Quick, a Retina screen: the plot 2 000 device pixels wide,
so no pattern is reduced), run by the owner on 2026-10-25, one run each
([rows](scan-view-timings/renderers-gpu.tsv)), in milliseconds:

| Candidate | Width | First | x range | Restyle | Offset |
| --- | ---: | ---: | ---: | ---: | ---: |
| a, Qt Graphs | 2 px | 1 008 | 492 | no frame | 495 |
| b, ScanLines | 1 px | 147 | 16.7 | 8.2 | 8.2 |
| p, QPainter | 1 px | 72 | 66.5 | 66.5 | 66.4 |

ScanLines meets the target with a GPU, at about one frame of a 120 Hz screen for a restyle or an offset, four to eight
times faster than the painter. A second run reported by the owner gave b 26.5 ms for the first population (the first
run's 147 ms held one-time start-up) and the same changes.

## Why Qt Graphs is slow here

Timed in one run of candidate a without a GPU, each change split by Qt's render loop timing: our side of a change, the
324 traces reduced and handed over with one `replace()` per series, takes a median 7.5 ms (at most 29 ms); Qt Graphs then
takes a median 1 355 ms preparing the frame on the GUI thread (its polish), 193 ms rendering it and 501 ms in llvmpipe
before the swap. So the time is Qt Graphs' handling of 324 series, not the feeding.

A colour change alone does not make Qt Graphs draw (6.11): `setColor` schedules no frame, so the restyles drew nothing
in the runs above. The benchmark now emits the series' `update()` signal after the colour, and a restyle then draws in
about 2 s without a GPU, as the other changes do.
