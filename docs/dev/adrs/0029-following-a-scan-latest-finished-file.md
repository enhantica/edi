# ADR-0029 — Following a scan: the latest finished file, when the screen is ready

- **Status:** Accepted
- **Date:** 2026-10-10
- **Implementation:** ✅ Implemented — the app follows a running scan by this rule on the desktop and in the browser
- **Priority:** High

## Context

While a scan runs with Follow on, the pattern view shows the files as they are fitted. Until now the scan's fit job
built a display frame for a file (read the file again, calculate its pattern on a copy of the project, capture it) on
the calculation worker, then waited for the view to show it before building the next ([ADR-0020](0020-calculation-worker-and-publication.md)
§9, the `file_frame` hook). That handshake behaves very differently in the two web kits:

- in the single-thread kit the job holds the page's thread, so the view never shows a frame while the scan runs and
  the job builds about one;
- in the multithread kit the page's thread is free, shows every frame at once, and the job builds one for every file.

A frame costs about 90 to 200 ms of the worker's time in the browser. On the 162-file D20 example that is 15 to 20 s
of a 47 s scan, which is most of why the multithread kit was about twice as slow as the single-thread one on this
example. The deliveries themselves are cheap and asynchronous; the worker never waits for the page.

Two kinds of scan need different things. A fast scan (dozens of files a second) cannot show every file and should not
try. A slow scan (a file every few seconds) can show every file and should.

## Decision

1. The scan's worker calculates no display frame. It reports each finished file (its results row, counts and χ²) as
   before.
2. When the view has asked for a pattern, the job sends, right after the next finished file's completion, that
   file's pattern as the fit left it: the measured and calculated columns of the project crysta fitted the file on
   (shared, not copied) and its reflections grouped by phase. Nothing is read or calculated for it. crysta passes that
   project to an optional per-file callback just before the file's completion event.
3. The view asks for the next pattern once it has shown the one before and at least `kFollowIntervalMs` (500 ms, in
   `app/src/fit_view_model.cpp`) has passed since that pattern arrived. Files finished in between are not drawn.
4. The followed file's data are still read off the GUI thread for the model (its measured points and its row's values
   in the tables); its pattern is the one the fit sent. A file chosen by hand while the scan runs, the newest file
   when Follow is turned on again, and the last file when the interval skipped it are calculated off the GUI thread
   on a copy of the template. A skipped file costs nothing, and choosing it later calculates it then.
5. When the scan ends, its last finished file is shown, whatever the interval skipped.
6. The desktop app and both web kits use this same path. The scan's counts, notes, evolution and results do not
   change.
7. Only the pattern waits. What costs nothing to update follows every finished file at once: the current dataset (the
   evolution's line for the current fit, the highlighted row in the dataset list, the dataset selectors), the file
   name and the counts. A pattern that arrives after newer files have finished leaves the current dataset on the
   newest one. A file chosen by hand moves all of them, as before.

A slow scan therefore shows every file as it finishes. A fast scan shows the newest file about twice a second.

## Measurements

Host: a 64-core Linux virtual machine, the multithread kit and the single-thread kit in Chrome 146 (headless shell,
software WebGL), each run pinned to 8 cores that were idle when the run started; whole-machine idle is recorded for
every run and runs below 60 % idle are left out. Driver: a script that serves the packed site with the
cross-origin isolation headers, opens the bundled `pd-neut-cwl_cosio-d20_scan-162f` example through the app's page
hooks, clicks Start fitting and polls the status bar until the fit ends (the time is from the click to the end). The
diagnostic builds are edi 7d04d1c with one change each to `core/src/fit_job.cpp`, built like the shipped kit with
function names kept, and crysta b4d6a484. "1 worker" sets the engine's pool to one worker; "6 workers" is the
default team on 8 cores.

| Variant | Frames built (162 files) | Worker time on frames | 162f scan, 1 worker | 162f scan, 6 workers |
|---|---:|---:|---:|---:|
| A frame for every file (before this decision) | 162 | 14.7–17.6 s | 46.8 s; 45.4, 46.8, 48.5 s in other runs | 48.5 s |
| Frames at most every 100 ms, latest wins | 162 | 17.2–20.1 s | 45.7 s; 52.7, 53.3 s in other runs | 54.8 s |
| Frames at most every 1 s, latest wins | 29–31 | 5.7–5.9 s | 32.0 s | 34.4 s |
| No progress or frames at all (upper bound) | 0 | 0 | 22.7 s; 21.1, 26.8 s in other runs | 30.2 s |
| Single-thread kit (for comparison) | about 1 | — | 21.6 s | — |

The same example measured by hand on an Apple M2 laptop (12 cores) on 2026-10-10, timed from Start fitting to the
end of the scan. "Calculated" is the first version of this decision, which calculated a followed file's pattern
beside the scan; "from the fit" is the decision as it stands. One engine worker was set through a test copy of the
site that reads `?threads=1`.

| Build | Browser (reported cores, engine workers) | 162f scan |
|---|---|---:|
| A frame for every file (before) | Safari | 22.5 s |
| A frame for every file (before) | Brave | 16 s |
| A frame for every file (before) | Firefox | 20 s |
| Frames at most every 1 s | Safari (8, 6) | 14–15 s |
| Latest finished file, calculated | Safari (8, 6) | 16 s |
| Latest finished file, calculated | Brave (5, 3) | 11 s |
| Latest finished file, calculated | Firefox (12, 10) | 15 s |
| Latest finished file, calculated | Safari, 1 worker | 17.1 s |
| Latest finished file, calculated | Brave, 1 worker | 12.9 s |
| Latest finished file, from the fit | Safari (8, 6) | 15.2 s |
| Latest finished file, from the fit | Brave (5, 3) | 10.8 s |
| Latest finished file, from the fit | Safari, 1 worker | 16 s |
| Latest finished file, from the fit | Brave, 1 worker | 12 s |
| The desktop app | — | 4.4–4.7 s |

On the virtual machine (headless Chrome, the multithread kit at its default team, 8 picked cores, 5 interleaved
repetitions, 60–72 % idle) the 162f scan took 37.1 s (35.4–43.9 s) with the pattern calculated and 36.7 s
(34.0–38.4 s) with the pattern from the fit, faster in 4 of the 5 pairs. Before, a shown file cost a background
thread about 31 ms to read it, 4 ms for the relations and 36 ms to calculate it (medians of 68 frames in one scan);
the read is all that remains.

Taking the pattern from the fit gained about 1 s on each browser. The frames are no longer what keeps the browser
about 2.5 times slower than the desktop; that gap is followed function by function in the engine's own work.

On the one-file step of the same example (13 iterations) the variants differ by less than the run-to-run spread
(0.7–0.9 s): a single fit builds at most a few frames.

The 100 ms throttle changes nothing because a file takes about 300 ms to fit here, so every file is past the
interval. The 1 s throttle helps, but it still builds a frame on the worker, holding up the next file by the frame's
cost.

## Consequences

- The scan's worker only fits and hands over what it has calculated; the view shows the newest file about twice a
  second. The scan is still slower than with no progress at all (the bound in the first table): the page thread's
  work for every finished file remains, and the worker's file reads and writes wait for the page thread in the
  multithread kit.
- A followed file costs the fit's thread a few allocations: its pattern is made of columns the fit has just
  calculated. Its data are still read off the GUI thread, and applying them to the model and drawing them stay on the
  GUI thread.
- The single-thread kit is unchanged in practice: its page thread is busy while the scan runs, so it shows the last
  file when the scan ends, as before.
- The `file_frame` hook of `edi::FitJob` carries the fit's own pattern of a file. Only a file chosen by hand during a
  scan, the newest file when Follow is turned on again, and a last file the interval skipped are calculated again.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| A frame for every file (the previous behaviour) | Fast scans build hundreds of frames nobody sees, and in the multithread kit they double the scan time. |
| A fixed interval on the worker (100 ms or 1 s) | Too short does nothing when files take longer than the interval; too long hides the files of a slow scan. Either way the frame is still built on the fit's thread and delays the next file. |
| Every Nth file | Right for one speed only: for a slow scan it hides N − 1 files that could have been shown, for a fast one it still builds too many. |
| No progress at all while a scan runs | Fastest, but the user cannot follow the scan. |
| Calculate a followed file's pattern beside the scan (this decision's first version) | Repeats work the fit has just done: a read of the file, the relations and a calculation per shown file, about 70 ms of a background thread per frame in headless Chrome. |
