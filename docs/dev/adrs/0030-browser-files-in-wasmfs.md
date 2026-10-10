# ADR-0030 — The browser's files live in WasmFS

- **Status:** Accepted
- **Date:** 2026-10-11
- **Implementation:** ✅ Implemented — both browser kits link WasmFS
- **Priority:** High
- **Forward constraint (binding on new features):** code that reads or writes the page's files does it through the C
  library (or Qt over it) from whatever thread it runs on; JavaScript that touches the page's files uses the `FS` calls
  WasmFS keeps under `FORCE_FILESYSTEM` (`mkdir`, `mkdirTree`, `writeFile`, `readFile`, …).

## Context

In the browser the app's files live in the page's memory ([ADR-0023](0023-web-build.md)): a bundled example is copied
there, a folder the user opens is copied there, and a scan writes `analysis/results.csv` and its ledger there.
Emscripten's default file system keeps those files in JavaScript on the page's main thread. In the multithread kit
every file call a worker makes (open, read, write, stat, close) is therefore sent to the page's thread, and the worker
waits for the answer.

A scan does that for every file it fits: it reads the data file, appends a row to the results and to the provenance
ledger, and edi reads the ledger's last row back. The page's thread is busy drawing the scan's progress
([ADR-0029](0029-following-a-scan-latest-finished-file.md)), so each of those calls waits for a drawn frame to finish.
A single fit touches no files and does not wait.

WasmFS is Emscripten's file system written in C++: its files live in WebAssembly memory, and a call runs on the thread
that makes it.

## Decision

1. Both browser kits link WasmFS (`-sWASMFS`) with its full JavaScript API (`-sFORCE_FILESYSTEM`), in
   `app/CMakeLists.txt`. The folder upload (`app/src/web_files.cpp`) keeps calling `FS.mkdirTree` and `FS.writeFile`,
   and Qt's loader keeps calling `FS.mkdir` and `FS.createPreloadedFile`.
2. A WasmFS link has no JavaScript socket library, but Qt Core references its six callback setters. The app opens no
   sockets, so `app/src/wasmfs_socket_stubs.cpp` defines them to do nothing.
3. The single-thread kit uses WasmFS too, so the two kits have one file system. Its calls never left the page's
   thread, so nothing waits less there.

## Measurements

Headless Chrome 146 on the 64-core development VM, the multithread kit at its default team on 8 picked cores, edi
f5f19d3 with crysta 2af34e12 (the cheap frame of ADR-0029 and crysta ADR-0085's fixes), with and without WasmFS and
nothing else changed; 5 interleaved repetitions, whole-machine idle 0.62–0.90:

| | Without WasmFS | With WasmFS |
|---|---|---|
| 162f scan | 28.1, 29.6, 32.6, 31.0, 28.0 s (median 29.6 s) | 20.5, 20.0, 21.5, 19.4, 21.2 s (median 20.5 s, −31 %) |
| One-file step | 781, 749, 773, 887, 799 ms (median 781 ms) | 758, 751, 805, 742, 825 ms (median 758 ms) |

Every repetition of the scan was faster with WasmFS; the single fit, which touches no files, did not change.

The file paths were checked in both kits with a script that drives the page: open the bundled
`pd-neut-cwl_cosio-d20_start-1` example, save it as (Qt hands the archive to the browser's save picker, answered by the
script), reset, open the saved project again through the folder upload, fit it (13 iterations), and save it again. Both
kits passed every step with no file-system error in the console, the second archive holding the same files as the
first. The 162-file scan ran to its end in both kits.

## Consequences

- The scan's worker reads and writes its files without waiting for the page's thread.
- Sockets cannot be used in the browser build; nothing in the app uses them.
- What the page keeps across reloads is unchanged: settings stay in local storage, files stay in memory for the session.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Keep the JavaScript file system and make fewer calls per scan file (larger read buffers, one append per file) | Every remaining call still waits for a drawn frame; it narrows the cost without removing it. |
| Draw less while a scan runs | Already done (ADR-0029); the calls still wait for the frames that remain. |
| WasmFS in the multithread kit only | Two file systems for one app, for no gain in the single-thread kit either way. |
| The origin-private file system (OPFS) backend | Keeps files across reloads, which the app does not need, and its calls are slower than memory. |
