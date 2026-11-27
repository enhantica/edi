# 0110. Load data off the GUI thread

- **Status:** Accepted
- **Date:** 2026-11-27
- **Implementation:** ✅ Implemented
- **Priority:** High
- **Forward constraint (binding on new features):** a new way to load measured data reads and copies its files in the
  background job of this ADR and settles once with `dataLoadSettled`; nothing parses a data file on the GUI thread, and
  the web app checks a file's size before reading it.

## Context

Load data read and parsed the whole file on the GUI thread. A large file froze the window, and in the browser a
large enough one ended the tab (edi#119). Every route did it: the file dialog, the online dialog, a tutorial, and the
several-files routes, one of which also copied every file into the project before its first read. ADR-0089 point 7
already reads a series' files off the GUI thread with `run_in_background`, and ADR-0102 rule 3 asks the same of every
view's data.

## Decision

1. **Two phases per route.** On the user's action a route makes its usual checks, then starts one background job
   (`run_in_background`) that reads every file it needs, a powder pattern's rows or a single crystal's reflections
   (`edi::read_data_file`, given only what the parse needs: the sample form and a single crystal's beam mode), after
   copying a copied scan's files into the folder the route made. When the job ends, the route's own code runs again on
   the GUI thread with those reads (`edi::experiment_with_read`) and checks everything against the project as it is
   then. A reflection read whose experiment changed sample form or beam mode meanwhile is refused; a powder pattern is
   assembled on the current beam mode, which its parse does not use.
2. **Not the calculation worker.** Its destructor waits for the running job, and crysta's readers cannot be stopped,
   so closing a project during a long read would freeze. A job of this ADR that is no longer wanted finishes in the
   background; its result is dropped and the folder it copied into removed.
3. **One load at a time, and its end, by number.** While a load runs the Experiments group shows "Reading <file>, <size>
   MB, <n> s" in the fit's striped bar, with Cancel. Each load a route starts gets a number, which
   `ProjectViewModel::startedDataLoad()` gives right after the route's call (0 when the call started none), and
   `dataLoadSettled(number, loaded)` comes exactly once for it: when it is applied or refused, or as not loaded when
   Cancel, a newer load, or removing its experiment drops it. A caller that needs the data waits for its own number, so
   another load's end never answers it: the online dialog marks its entry loaded then, and the documentation capture and
   the demo wait through `wait_for_load` (`app/src/load_wait.hpp`), which also stops waiting when the project closes. A
   route returns true when its job started. The assistant's own input is loaded in the call that consumes it, as before.
4. **The web app's bound, 50 MB.** The browser holds a file twice while reading it (in the page and in the app's
   memory) and the app's memory is limited to 4 GiB, so the web app refuses a data file over the largest size it loaded
   reliably in Chrome: 50 MB loaded three times out of three with 43 % of that memory to spare, and 100 MB neither
   finished in 50 minutes nor kept a quarter spare (files from `tools/probes/large_plain_data.py`). It refuses before
   reading any byte of the file: in the file chooser's accept step, from the size the browser reports, and in the
   folder chooser, over every file's size. It also drops its own copy of a file once the file is in the page's file
   system. The desktop has no such bound.

## Consequences

- The window answers while a large file is read; the read itself is not faster, and there is no percentage, which
  would need a callback inside crysta's readers.
- Code that calls a load route and reads the data straight after must wait for `dataLoadSettled`.
- A load that finds the project changed in a way its reads no longer fit is refused, and the user loads again.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| A second calculation worker | Rejected: closing a project would wait for an unstoppable read (decision 2). |
| Read small files on the GUI thread and only large ones in the background | Rejected: two paths, and the background one would be tested only by large files. |
| A progress percentage | Deferred: it needs a progress callback in crysta's plain-data and reflection readers. |
