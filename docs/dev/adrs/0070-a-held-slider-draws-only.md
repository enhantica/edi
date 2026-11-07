# 0070. A held slider calculates and draws, nothing else

- **Status:** Accepted
- **Date:** 2026-11-07
- **Implementation:** ✅ Implemented
- **Priority:** High
- **Forward constraint (binding on new features):** work that follows a parameter value (texts, tables, spelling, the
  assistant's context, anything a page derives from the project) runs on release of a drag, not on each step. A new
  per-step cost needs a measured reason.

## Context

Dragging the parameter slider on the Analysis page edits a value many times a second. Each edit used to run everything
an ordinary edit runs: the save spelling of every field through crysta, the file texts and their categories, the
report, the assistant's context, a full Undo record, and a redraw of every chart series. On the LBCO example a step
took about 0.8 s to show, so the slider no longer followed the hand. ADR-0020 already makes the calculation itself
asynchronous and newest-wins; the cost was everything around it.

## Decision

1. While the slider is held (`ProjectViewModel.adjusting`), each value change runs the calculation, publishes the
   values to the parameter fields, and redraws the pattern charts. Everything else waits for the release.
2. On release the work the steps skipped runs once, as for one ordinary edit: symmetry and fittability, the save
   spelling, texts, categories, report, the assistant and the session's listeners. A calculation still running then
   publishes its part when it arrives.
3. One drag is one Undo step. Its first step records the project as the drag found it, later steps add nothing, and the
   release trims the record to the parameters the drag changed. A drag let go where it started leaves no step.
4. While held, the charts keep their y range and leave the measured series as drawn. Filled areas (the residual band,
   the structures' areas) are emptied for the drag and drawn again on release, because Qt Graphs triangulates an area
   on every change and that was the largest cost of a step. The lines on their edges keep following each step.
5. A save during a drag writes the newest values: the saved files are made when read, and each step marks them stale.

The slider is the app's only drag control; its keyboard steps hold it the same way (Qt marks a held arrow key as
pressed).

## Consequences

A drag step costs the calculation, the values and the line series. On the LBCO example on this project's Linux build
machine, which renders in software, a step went from 192–201 ms to about 140 ms to show; most of what remains there is
the software renderer, which a GPU does not have. Releasing the slider costs one ordinary edit. While a value is held
the residual band and the structures' areas are not shown, and the Text tab and report show the values from before
the drag.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Debounce every edit by a timer | Rejected: delays typed edits too and still runs all of it while dragging slowly |
| Compute texts and spelling on a worker thread | Deferred: they read the live project; with the rule above they run once per drag, which measured cheap enough |
| Keep a stale filled area during the drag | Rejected: it visibly disagrees with its own edges as soon as the value moves |
| Cache the spelling and texts between steps | Rejected by the owner (2026-11-04): restore the old feel without new caches |
